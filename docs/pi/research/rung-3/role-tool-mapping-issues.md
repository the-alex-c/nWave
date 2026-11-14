# Rung 3 research: mapping Claude role tools to pi (issue definition)

Feeds [adr-pi-role-tool-mapping.md](adr-pi-role-tool-mapping.md). Part of [TODO-RUNG-3.md](../../TODO-RUNG-3.md), "Role mapping". Evidence date: pi-code in `~/.pi/agent/npm/node_modules/pi-code`, pi docs in the Cellar.

## Problem

nWave roles (`nWave/agents/nw-*.md`, 37 files) declare Claude Code tools. The pi role file must name tools pi can resolve. `PI_BUILTINS` in `scripts/shared/pi_role_validation.py` is `read bash edit write grep find ls`, so validation rejects four Claude tools that roles declare today:

| Claude tool | Roles declaring it (`tools:`) | Body directive |
|---|---|---|
| `Task` | 14 | n/a |
| `Skill` | 4 | `Invoke Skill(X)` in 4 role bodies |
| `WebFetch` | 4 | n/a |
| `WebSearch` | 3 | n/a |

`SendMessage` (nearly all roles) is already decided: dropped. No role's `tools:` line carries `StructuredOutput` or a scoped grant such as `Bash(...)`.

## How other harnesses map it

Each harness has its own agents plugin with its own tool table. Shared: `rewrite_host_paths`, `parse_frontmatter`, manifest ownership. Not shared: tool mapping.

| Harness | Mechanism | `Task` | `Skill` | `WebFetch` / `WebSearch` |
|---|---|---|---|---|
| OMP (`omp_common.py`) | `_TOOL_NAME_MAP` to lowercase builtins | `task` | `read` (resolves `skill://`) | `read` / `web_search` |
| OpenCode | `tools` become a `permission` map | allow | allow | allow |
| Codex | tools become a prose capability preamble; no tools field | n/a | n/a | n/a |

OMP laws worth copying:
1. **Never widen.** A declared entry with no equivalent is dropped and reported. A scoped grant (`Bash(x:*)`) is dropped, because OMP tool lists are bare names and a bare `bash` would hand over the whole shell.
2. **Report every drop.** `map_declared_tools` returns `(mapped, dropped_scoped, dropped_unmapped, structured_output)`; callers surface the drops. Nothing is lost silently.
3. **Deliver each skill once.** `skills:` becomes `autoloadSkills`; bodies are not inlined. `Invoke Skill(X)` becomes `` Read `skill://X/SKILL.md` ``.

`map_declared_tools` cannot be reused for pi as is: `_TOOL_NAME_MAP` is a module constant.

## Findings about pi

### F1. Skills need no tool
pi core advertises each skill (name, description, path) in the system prompt; the model loads it by calling `read` on `SKILL.md` (`docs/skills.md`). A `Skill` tool is therefore redundant. pi-code maps Claude's `Skill` to `slash_command`, but that tool belongs to `commands.ts` (custom commands), which our filter does not load.

### F2. Web tools exist in pi-code, behind a filtered-out extension
`extensions/web.ts` registers:
- `web_search`: DuckDuckGo, `allowed_domains` / `blocked_domains`.
- `web_fetch`: http(s) only, upgraded to https, cross-host redirect reported not followed, HTML converted to markdown, 15-minute per-URL cache, optional `prompt` (the model answers from the page).

Our level 3 filter (`pi_code_package.DELEGATION_FILTER`) keeps only `hooks/index.ts` and `subagent/index.ts`, so neither tool exists in an nWave install. The `pi-fetch` package seen in the author's global npm dir is a separate user install, not part of nWave.

### F3. pi-code already translates Claude tool names
`extensions/internal/claude-tool-names.ts` pairs Claude and pi names and applies them to an agent's `tools:`: `Glob→find`, `WebFetch→web_fetch`, `WebSearch→web_search`, `Task`/`Agent→subagent`, `Skill→slash_command`. A role could pass Claude names through unchanged. Not relied on: our validator is stricter on purpose and the explicit pi names keep generated files readable and checkable.

### F4. A child can only use a fixed tool set
`subagent/child.ts` `CHILD_TOOL_NAMES`: `read bash edit write grep find ls web_fetch web_search list_mcp_resources read_mcp_resource todo question memory slash_command plan_mode_complete`. `subagent` is not in it. A child launch fails only when no `tools:` entry resolves (`unresolvedToolsError`); one stray unresolved name is harmless at runtime. Consequence: mapping `Task` to the delegation tool makes it available to the parent (`subagent` now, the `Agent` wrapper later). Whether a child can call it is **unverified**.

### F5. Scoped grants widen under pi-code
`agents.ts` `parseToolsField`: as in Claude Code, a scope on a grant (`Bash(git log:*)`) does not limit the agent; it gets the base tool. This is the opposite of the OMP "never widen" law.

## Open unknowns (need a live run)
- U1. Does a child load `web.ts` when it is in the filter?
- U2. Is the delegation tool (`subagent`, later `Agent`) callable inside a child?
- U3. Do `nwdes_cli_role_tools` roles produce scoped grants for pi? (Absent from current `tools:` lines.)
- U4. `nwdes_cli_role_tools` roles: Bash plus the nwdes CLI (OMP), or `submit_<role>` as well? Not yet decided; outside this write-up.

## Constraints
- Test-first; `to_pi_role(name, text)` is pure, and the generator and validator both consume it.
- All-or-nothing install (ADR 4): a role that fails validation fails the whole install, so each mapping decision decides how many roles can ever fail.
- YAGNI: no new abstraction beyond what the four tools need.
