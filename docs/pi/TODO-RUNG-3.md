# Rung 3: TODO

Implementation TODO. Decisions: [adr-pi-delegation-for-rung-3.md](research/rung-3/adr-pi-delegation-for-rung-3.md). Evidence: [subagent-delegation-gaps.md](research/rung-3/subagent-delegation-gaps.md), [agent-wrapper-mechanics.md](research/rung-3/agent-wrapper-mechanics.md). Parity tracking stays in [TODO-PARITY.md](TODO-PARITY.md).

One delivery: agents plugin + `Agent` wrapper + per-role `submit_<role>`.

## Verify first (unknowns that could change the design)

- [ ] Run `subagent(agent, task)` live. Does the rung 2 guard block or allow it?
- [ ] Does pi-code inject `skills:` into a child? ADR assumes no, so inlining is needed.
- [ ] Spike the wrapper: `ctx.executeTool("subagent", ...)` works while `subagent` is hidden via `prepareLoadout` `hiddenDeclarations`.
- [ ] Check `nw-*` name clashes with `~/.claude/agents`. Project `.pi` should win.

## Role registry (plugin)

- [ ] Widen the rung 2 extension filter so pi-code's `subagent` extension is kept (hooks only today).
- [ ] Agents plugin modeled on `codex_agents_plugin.py`, sharing its helpers.
- [ ] Generate `~/.pi/agent/agents/nw-*.md` from every role in `nWave/agents/`.
- [ ] Role mapping:
  - drop `SendMessage` and `model`
  - keep `maxTurns`
  - apply `PI_PATH_REWRITES`
  - translate skill invocations
  - inline `skills:`
  - add `submit_<role>` plus a built-in to `tools:`
- [ ] Gate the plugin on the delegation extension being installed, not on a rung.
- [ ] Manifest-owned files, removed on uninstall. Idempotent install.

## Validation (all-or-nothing)

- [ ] Before writing, check each role:
  - frontmatter parses
  - `tools:` resolve to pi built-ins or `submit_<role>`
  - `skills:` exist
  - pi-code lists the agent
- [ ] Report prompt size per role (warn on large; no cap).
- [ ] List all failures at once; leave target untouched on any failure.
- [ ] Run the same check as a test over every role.

## `Agent` wrapper

- [ ] Register `Agent(subagent_type, prompt)` delegating to `subagent` via `ctx.executeTool`.
- [ ] Hide `subagent` from the model via `prepareLoadout` `hiddenDeclarations`.
- [ ] Remove the roster: `delete event.systemPromptOptions.sections.subagents`.
- [ ] Detect child failure and return a typed failure (not `isError:false`).

## Typed reply

- [ ] Generate `submit_<role>` tools from `role_envelope_schemas.json`.
- [ ] Register them only when `PI_CODE_SUBAGENT` is set.
- [ ] No valid submit after one nudge: typed failure. No prose parsing.
- [ ] Optional: wall-clock cap (unmeasured).

## Ship

- [ ] End-to-end test: install, `Agent` call to one role, valid envelope returned, uninstall cleanly.
- [ ] Failure-path test: invalid or missing submit yields a typed failure.
- [ ] Update `subagent-delegation-gaps.md` with live-run results.
