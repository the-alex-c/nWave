# ADR: mapping Claude role tools to pi

Status: **accepted**. Decisions 1-5 accepted. Extends decision 5 of [adr-pi-delegation-for-rung-3.md](adr-pi-delegation-for-rung-3.md). Issue definition and evidence: [role-tool-mapping-issues.md](role-tool-mapping-issues.md).

## Context

Roles declare `Task` (14 roles), `Skill` (4), `WebFetch` (4) and `WebSearch` (3). pi has no built-in for any of them, and validation rejects them. Other harnesses map or drop them with their own table. pi-code ships `web_search` and `web_fetch` in an extension our filter excludes, and pi loads skills through plain `read`.

## Decisions

### 1. `Task` maps to the delegation tool: `subagent` now, `Agent` when the wrapper lands (accepted)

`Task` (and `Agent`) in a role's `tools:` becomes `subagent`, the name pi-code registers
today and already resolves from `Task` (F3). The validator allows `subagent`. When the
`Agent` wrapper ships, the target changes to `Agent`: one table value in
`pi_role_mapping.py` (`DELEGATION_TOOL`), one validator entry, one test row. A reinstall
regenerates the files (the install is idempotent).

- Why: the wrapper is a separate TODO item and the mapping needs nothing from it. `subagent`
  is the real name until then, so no role file names a tool that does not exist.
- Why `Agent` later: the wrapper is the delegation tool the model sees (`subagent` is hidden).
- Risk: whether a child can call the delegation tool is unverified (U2). If not, the entry is
  inert in children; it does not fail the launch (F4).
- Rejected: write `Agent` now. Roles would name a tool nothing registers.

### 2. `Skill` is dropped from `tools:`; the body directive becomes a `read` (accepted)

Remove `Skill` from `tools:`. Translate `Invoke Skill(X)` (and `Invoke ONE Skill(X)`) to `` Read `~/.pi/agent/skills/X/SKILL.md` ``, keeping any trailing ON-TRIGGER text. Report the drop.

- Why: pi loads skills through `read` (F1). All four roles with `Skill` also declare `Read`.
- Rejected: map to `slash_command`. It needs `commands.ts`, which loads custom commands, a wider surface than needed.
- Rejected: leave `Skill` and allow it in the validator. Nothing would resolve it.

### 3. `WebFetch` and `WebSearch` map to `web_fetch` and `web_search`; the level 3 filter keeps `extensions/web.ts` (accepted)

Add `extensions/web.ts` to `DELEGATION_FILTER`. The validator allows both names.

- Why: pi-code's tools mirror the Claude ones (cache, https upgrade, `prompt`, domain filters), so role bodies keep working unchanged. A Bash `curl` replacement would lose the SSRF guard, markdown conversion and domain filters, and would grant `bash` to roles that do not have it.
- Cost: a wider extension surface at level 3; U1 must be verified live before this ships.
- Rejected: drop and report. Four roles would silently lose web access.
- Fallback if U1 fails: drop and report, and say so in the install output.

### 4. Never widen: scoped grants and unmapped tools are dropped and reported (accepted)

Follow the OMP laws. A scoped entry (`Bash(...)`) is dropped, not mapped to bare `bash` (F5 makes the widening real under pi-code). An unmapped tool (`SendMessage`, anything unknown) is dropped. Each drop is returned as a report line; the generator prints them at install.

- Consequence: `to_pi_role` returns `(text, reports)`, not just text.
- Rejected: silent drop (invisible capability loss; the Codex plugin found this out for `model`).

### 5. Own table, copied logic; no shared mapper (for now) (accepted)

`pi_role_mapping.py` holds a pi tool table and its own mapping function. `omp_common.map_declared_tools` stays untouched.

- Why: its table is a module constant, so sharing means changing OMP code and its tests for a ~30-line function (YAGNI). Revisit if a third harness needs the same shape.
- Rejected: parametrize the OMP function by table. Touches working OMP code for no pi behavior.

### Final mapping table

| Claude | pi `tools:` | Report |
|---|---|---|
| Read, Write, Edit, Bash, Grep | `read write edit bash grep` | |
| Glob | `find` | |
| Task, Agent | `subagent` (becomes `Agent` with the wrapper) | |
| WebFetch | `web_fetch` | |
| WebSearch | `web_search` | |
| Skill | dropped | body directive translated |
| SendMessage, other unmapped | dropped | reported |
| scoped `X(...)` | dropped | reported |
| (added) | `submit_<role>` | |

`model` dropped, `maxTurns` kept, `skills:` kept (decision 5 of the parent ADR).

## Consequences

- Every current role validates after mapping; none fails the all-or-nothing check on a tool name.
- Validator: `PI_BUILTINS` gains `subagent`, `web_fetch`, `web_search` (`subagent` becomes `Agent` with the wrapper).
- `pi_code_package`: `DELEGATION_FILTER` gains `extensions/web.ts`; `tests/pi/test_pi_levels.py` updated.
- Tests to add before the green step: each table row, the scoped drop with its report, the `Invoke Skill(X)` translation, and the filter entry.

## Accepted risks

- U1 and U2 are unverified until a live run (`NWAVE_PI_E2E`).
- Writing the delegation tool name into child roles is inert if children cannot call it.
- The rename `subagent` → `Agent` is a follow-up; roles generated before it name `subagent` until reinstall.
- DuckDuckGo scraping (`web_search`) is key-free and may break upstream; not under our control.
- Depends on pi-code's `web.ts` staying at that path (the filter is path-based).

## Open

- U4: `nwdes_cli_role_tools` roles (Bash plus CLI, or `submit_<role>` too). Not decided here.
