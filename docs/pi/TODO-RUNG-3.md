# Rung 3: TODO

Implementation TODO. Decisions: [adr-pi-delegation-for-rung-3.md](research/rung-3/adr-pi-delegation-for-rung-3.md). Evidence: [subagent-delegation-gaps.md](research/rung-3/subagent-delegation-gaps.md), [agent-wrapper-mechanics.md](research/rung-3/agent-wrapper-mechanics.md). Parity tracking stays in [TODO-PARITY.md](TODO-PARITY.md).

One delivery: agents plugin + `Agent` wrapper + per-role `submit_<role>`.

## Verify first (unknowns that could change the design)

- [x] Run `subagent(agent, task)` live. Does the rung 2 guard block or allow it? **Allowed.** The installed matcher is `Bash|Write|Edit`, so the guard never sees `subagent` (or `Agent`). Synthetic payloads to `hooks PreToolUse --host pi` also exit 0. Child ran and returned `PONG`. The child 404 on `claude-opus-4-8` was a missing model option in the test setup, not a design issue.
- [x] Does pi-code inject `skills:` into a child? **Yes** (`withPreloadedSkills` inlines bodies; live: marker returned). Only from `$CLAUDE_CONFIG_DIR/skills` (rung 2 sets it to `~/.pi/agent`) or project `.claude/skills`; without it: `(skill not found)`, no error. So no inlining by the plugin; ADR 5 should change. Validation must check `skills:` resolve under `~/.pi/agent/skills`, and the child needs `CLAUDE_CONFIG_DIR` (inherited env).
- [x] Spike the wrapper: `ctx.executeTool("subagent", ...)` works while `subagent` is hidden via `prepareLoadout` `hiddenDeclarations`. **Works with a real model** (faux-provider run already in `agent-wrapper-mechanics.md`): `Agent` -> `subagent` -> child returned `PONG`; hook saw `call Agent`, `call subagent`; model answered it has no `subagent` tool; roster section removed.
- [x] Check `nw-*` name clashes with `~/.claude/agents`. **No clash problem.** `~/.pi/agent/agents` beats `~/.claude/agents` (live: same name `nw-zz` in both, pi dir won). With `CLAUDE_CONFIG_DIR=~/.pi/agent` (rung 2) `~/.claude/agents` is not scanned at all. A project `.claude/agents` dir was ignored in the untrusted test repo; trusted-project precedence not run.

## Role registry (plugin)

- [x] Add level 3 (`--pi-level 3`, new default = highest level). `pi_code_package.filter_for(level)`: level 2 keeps hooks only, level 3 adds `extensions/subagent/index.ts`. Tests in `tests/pi/test_pi_levels.py`. Not yet verified against a live pi (`NWAVE_PI_E2E`).
- [ ] Agents plugin modeled on `codex_agents_plugin.py`, sharing its helpers.
- [ ] Generate `~/.pi/agent/agents/nw-*.md` from every role in `nWave/agents/`.
- [ ] Role mapping:
  - drop `SendMessage` and `model`
  - keep `maxTurns`
  - apply `PI_PATH_REWRITES`
  - translate skill invocations
  - keep `skills:` (pi-code preloads them; no inlining)
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
