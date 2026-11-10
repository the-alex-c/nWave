# Pi vs OMP: gaps for nWave / nwdes

Scope: `pi/main` (upstream earendil-works/pi) vs the OMP (oh-my-pi) integration in
`scripts/install/plugins/omp_*.py`, `nWave/templates/omp-nwave-hooks-extension.ts.template`.
Source-read only; nothing was executed.

## OMP-side contract nWave relies on, and the pi equivalent

| Area | OMP | Pi | Gap |
|---|---|---|---|
| Config root | `~/.omp/agent` (`PI_CONFIG_DIR`) | `~/.pi/agent` (`PI_CODING_AGENT_DIR`) | No pi path helpers, env var differs |
| Installer platform | `--platform omp` | none | No `pi` platform, detection, or path-rewrite table |
| Subagents | native `task` tool, `~/.omp/agent/agents/*.md` | none native; `examples/extensions/subagent` spawns a `pi` subprocess | Hard gap |
| Agent frontmatter | `name`, `description`, `tools`, `spawns`, `output`, `autoloadSkills`, `thinking-level`, `blocking` | example ext: `name`, `description`, `tools`, `model` only | No `output` schema, `autoloadSkills`, `spawns`, `blocking` |
| Structured reply | `output` schema, `yield` tool | none | Roles can't return the `role_envelope` schema |
| Skill preload | `autoloadSkills` | none | Preload (frontmatter `skills:`) unsupported |
| Skill URI | `skill://<name>/SKILL.md` via `read` | no such protocol; skills read by path | Installer rewrite (`translate_skill_invocations`) breaks |
| Skill location | `~/.omp/agent/skills/` | `~/.pi/agent/skills/`, `~/.agents/skills/` | Path only |
| Skill frontmatter | OMP-tolerant | Agent Skills spec; honors `disable-model-invocation`, not `user-invocable` | Minor |
| Slash commands | `~/.omp/agent/commands/*.md` | prompt templates `~/.pi/agent/prompts/*.md`; skills as `/skill:name` | Emit as prompt templates |
| Builtin tools | `read write edit bash glob grep task web_search` (+ `apply_patch`, `yield`) | `read bash edit write grep find ls` | No `glob`, `web_search`, `task`, `yield` |
| `read` on URLs / `skill://` | yes | no | `WebFetch` and `Skill` mapping invalid |
| Guard extension | `@oh-my-pi/pi-coding-agent` API; `ctx.agent.kind`, `ctx.sessionManager.getSessionId()`; parses `apply_patch` / hashline edits | `pi.on("tool_call")`, different ctx and edit input shapes | Template must be rewritten |
| Model inheritance | omit `model` -> parent model | omit -> default model (unverified) | Check |
| Session format | root `.jsonl` + sibling dir of child `.jsonl` | `docs/session-format.md` differs | `nwdes measure` native mode (`host_sessions.read_tree`) unqualified; use `--requests` |

## What nWave expects from Claude Code that pi lacks

1. **Native role delegation.** `nw-role-invocation` requires `Agent(subagent_type="nw-<role>", prompt=...)` (or Codex `spawn_agent`), running the exact installed role with its declared tool ceiling. Pi has no `Agent`/`Task` tool or named-agent registry.
2. **Hooks** (`nwave_ai/hooks/registration.py`, `__main__.py`; Claude-shaped stdin JSON, exit 0/1/2, `hookSpecificOutput.permissionDecision`/`updatedInput`):
   - `PreToolUse` matchers `Agent` (pre-task), `SendMessage`, `TaskCreate|TaskUpdate`: tools do not exist in pi.
   - `PreToolUse` `Write`, `Edit`, `Bash` (git-stash guard, attribution rewrite): pi `tool_call` can block/mutate, payload differs.
   - `SubagentStop`: no subagents, no event.
   - `SessionStart` (`additionalContext` injection): pi `session_start` has no such return contract.
   - `SessionEnd`: nearest is `session_shutdown`.
   - `@hsingjui/pi-hooks` (already in `~/.pi/agent/settings.json`) adapts Claude command hooks; coverage not checked. Cannot supply `Agent` / `SubagentStop` without a subagent layer.
3. **Agent frontmatter semantics.** `model: claude-*`, `maxTurns`, `tools:` with scoped `Bash(...)` grants, `StructuredOutput` reply channel, `skills:` preload. Omitted `tools:` = inherit all in Claude (`capability.py` -> `INSTRUCTED`); `ENFORCED` needs the host to withhold tools.
4. **Role tools.** `SendMessage` (soft gap: root-mediated fallback documented), `TaskCreate`/`TaskUpdate`, `Skill`, `WebFetch`, `Glob`, `Agent`.
5. **Paths/conventions.** Hard-coded `~/.claude/skills/...`, `~/.claude/agents/...` read paths need a pi rewrite table; `/nw-*` as command files; `user-invocable: false` frontmatter.
6. **Host-driven workflow.** `nwdes` never launches a model; host must run roles, pick per-role model, observe RED/GREEN for declared commands. Per-role model needs agent files (absent in pi).
7. **Fresh-context review.** EXAMINE needs a source-blind isolated role run; pi only via subprocess example.

## Already host-neutral (works in pi)

- `nwdes` CLI, handoff JSON, rendered briefs/prompts/packets.
- Skill content (loadable from `~/.agents/skills` or `~/.pi/agent/skills`).

## Smallest path to viable

1. Subagent extension exposing `Agent(subagent_type=...)`: named role files, tool allowlist, skill autoload, model, structured `output`, `SubagentStop` event.
2. Pi hook shim (reuse `pi-hooks` if coverage suffices) running `python -m nwave_ai.hooks <Event> --host pi`; add `pi` to `HOSTS`.
3. Installer `pi` platform plugins: skills, agents, prompt templates, extension; pi path-rewrite table; `PI_CODING_AGENT_DIR` handling.
4. Verify model inheritance and session format for `nwdes measure`.
