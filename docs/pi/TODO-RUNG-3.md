# Rung 3: TODO

Implementation TODO. Decisions: [adr-pi-delegation-for-rung-3.md](research/rung-3/adr-pi-delegation-for-rung-3.md). Evidence: [subagent-delegation-gaps.md](research/rung-3/subagent-delegation-gaps.md), [agent-wrapper-mechanics.md](research/rung-3/agent-wrapper-mechanics.md). Parity tracking stays in [TODO-PARITY.md](TODO-PARITY.md).

One delivery: agents plugin + `Agent` wrapper + per-role `submit_<role>`.

## Verify first (unknowns that could change the design)

- [x] Run `subagent(agent, task)` live. Does the rung 2 guard block or allow it? **Allowed.** The installed matcher is `Bash|Write|Edit`, so the guard never sees `subagent` (or `Agent`). Synthetic payloads to `hooks PreToolUse --host pi` also exit 0. Child ran and returned `PONG`. The child 404 on `claude-opus-4-8` was a missing model option in the test setup, not a design issue.
- [x] Does pi-code inject `skills:` into a child? **Yes** (`withPreloadedSkills` inlines bodies; live: marker returned). Only from `$CLAUDE_CONFIG_DIR/skills` (rung 2 sets it to `~/.pi/agent`) or project `.claude/skills`; without it: `(skill not found)`, no error. So no inlining by the plugin; ADR 5 should change. Validation must check `skills:` resolve under `~/.pi/agent/skills`, and the child needs `CLAUDE_CONFIG_DIR` (inherited env).
- [x] Spike the wrapper: `ctx.executeTool("subagent", ...)` works while `subagent` is hidden via `prepareLoadout` `hiddenDeclarations`. **Works with a real model** (faux-provider run already in `agent-wrapper-mechanics.md`): `Agent` -> `subagent` -> child returned `PONG`; hook saw `call Agent`, `call subagent`; model answered it has no `subagent` tool; roster section removed (spike; the decision is now to rewrite it, see `Agent` wrapper).
- [x] Check `nw-*` name clashes with `~/.claude/agents`. **No clash problem.** `~/.pi/agent/agents` beats `~/.claude/agents` (live: same name `nw-zz` in both, pi dir won). With `CLAUDE_CONFIG_DIR=~/.pi/agent` (rung 2) `~/.claude/agents` is not scanned at all. A project `.claude/agents` dir was ignored in the untrusted test repo; trusted-project precedence not run.

## Role registry (plugin)

- [x] Add level 3 (`--pi-level 3`, new default = highest level). `pi_code_package.filter_for(level)`: level 2 keeps hooks only, level 3 adds `extensions/subagent/index.ts`. Tests in `tests/pi/test_pi_levels.py`. Not yet verified against a live pi (`NWAVE_PI_E2E`).
- [ ] Agents plugin modeled on `codex_agents_plugin.py`, sharing its helpers.
- [x] Generate `~/.pi/agent/agents/nw-*.md` from every public role in `nWave/agents/` (`PiAgentsPlugin`, `scripts/install/plugins/pi_agents_plugin.py`; wired into install, verify, uninstall; tests `test_pi_agents_plugin.py`, `test_pi_agents_wiring.py`). Runs at every level until the gate below lands.
- [x] Role mapping: `scripts/shared/pi_role_mapping.py`, `to_pi_role(name, text) -> (text, reports)`. Decisions: [adr-pi-role-tool-mapping.md](research/rung-3/adr-pi-role-tool-mapping.md); evidence: [role-tool-mapping-issues.md](research/rung-3/role-tool-mapping-issues.md). All 37 roles map and validate. Tests in `tests/pi/test_pi_role_mapping.py`.
  - drop `SendMessage` and `model`
  - keep `maxTurns`
  - apply `PI_PATH_REWRITES`
  - translate skill invocations (`Invoke Skill(X)` becomes a `Read` of the pi skill path; `Skill` dropped from `tools:`)
  - keep `skills:` (pi-code preloads them; no inlining)
  - add `submit_<role>` plus a built-in to `tools:`
  - `Task`/`Agent` become `subagent` (`DELEGATION_TOOL`); becomes `Agent` when the wrapper lands
  - `WebFetch`/`WebSearch` become `web_fetch`/`web_search`; level 3 filter keeps `extensions/web.ts` (not yet verified live: U1)
  - scoped grants and unmapped tools dropped and reported, never widened
- [ ] Gate the plugin on the delegation extension being installed, not on a rung.
- [x] Manifest-owned files, removed on uninstall. Idempotent install. Also prunes owned roles dropped from the source and refuses foreign `nw-*.md` files.

## Validation (all-or-nothing)

- [x] `scripts/shared/pi_role_validation.py`: check each generated role:
  - frontmatter parses
  - `tools:` resolve to pi built-ins or `submit_<role>`
  - `skills:` exist
- [ ] Check pi-code lists the agent (planned: E2E test, not install time).
- [ ] Report prompt size per role (`prompt_chars` returned; warn on large not yet; no cap).
- [x] List all failures at once.
- [x] Leave target untouched on any failure.
- [x] Map or drop Claude tools `Task`, `Skill`, `WebFetch`, `WebSearch`: decided in the ADR above; the validator accepts `subagent`, `web_fetch`, `web_search`.
- [x] Run the same check as a test over every role (`tests/pi/test_pi_all_roles.py`; skills resolved against `nWave/skills`).

## `Agent` wrapper

- [x] Register `Agent(subagent_type, prompt)` delegating to `subagent` via `ctx.executeTool`.
- [x] Hide `subagent` from the model via `prepareLoadout` `hiddenDeclarations`.
- [x] Rewrite the roster, do not delete it: pi-code's `subagents` section names the hidden `subagent` tool and `{agent, task}`. Our `before_agent_start` handler (runs after pi-code's) replaces the intro with `Agent({subagent_type, prompt})` wording and keeps the agent list. Order and wording coupling to pi-code: check in the live E2E test. Unit-tested only; live check pending.
- [x] Detect child failure and return a typed failure (not `isError:false`): `Agent` calls `classify` and returns `Agent failed (<kind>): <detail>` with `isError:true` (unit-tested; real pi-code contract test is under Ship).

## Typed reply

- [ ] Generate `submit_<role>` tools from `role_envelope_schemas.json`.
- [ ] Register them only when `PI_CODE_SUBAGENT` is set.
- [ ] No valid submit after one nudge: typed failure. No prose parsing.
- [ ] A `partial` run (stopped at `maxTurns`; pi-code forces exit 0) is ok with `partial: true`, not a failure (same as pi-code, which documents it as Claude's behavior; accepted as is). With no valid submit it is a typed failure at once: the child was killed, so no nudge is possible.
- [ ] Optional: wall-clock cap (unmeasured).

## Ship

- [ ] End-to-end test: install, `Agent` call to one role, valid envelope returned, uninstall cleanly.
- [ ] Failure-path test: invalid or missing submit yields a typed failure.
- [ ] Contract test against real pi-code (`NWAVE_PI_E2E`): drive `subagent` and assert the `classify` kind for (1) an unknown agent, (2) a child that errors with a nonzero exit, (3) a `maxTurns`-capped child (`partial: true`, ok). `stopReason` and `partial` renames fail silently, so cases 2 and 3 matter most. Re-run whenever `pi_code_package.SOURCE` changes. See ADR 6.
- [ ] Update `subagent-delegation-gaps.md` with live-run results.
