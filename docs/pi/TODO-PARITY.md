# pi platform: parity TODO

> **Scope: parity only.** This file tracks capabilities pi lacks relative to other coding agents (Devin, Cursor, Copilot, Codex, OMP, Claude Code). Implementation choices, release splits (e.g. rung 3 parts A/B) and installer details belong in a separate TODO or the rung's ADR, not here.

Tracks progress on making nWave work on pi, climbing the host ladder from Devin
(lowest) to Claude Code (highest). What is built so far is described in
[README.md](README.md). Each rung's analysis is in the linked gap doc; the ladder
itself is in [pi-vs-devin-gaps.md](pi-vs-devin-gaps.md).

Rungs are cumulative: each one assumes the ones below it.

## Rung 1: Devin (skills only) — DONE

Gap doc: [pi-vs-devin-gaps.md](pi-vs-devin-gaps.md)

Branch: `pi-platform-rung-1`

- [x] `pi` installer plugin: copies public skills to `~/.pi/agent/skills/`, manifest-owned
- [x] `pi_config_dir()` / `pi_skills_dir()` honoring `PI_CODING_AGENT_DIR`
- [x] `PI_PATH_REWRITES` (`~/.claude/...` -> `~/.pi/agent/...`)
- [x] `--platform pi` in install / verify / uninstall
- [x] Installer tests; real-pi discovery test (`get_commands` over RPC, no LLM)
- [x] Isolated install + `verify_nwave.py --platform pi` run clean (183 skills)
- [x] Manual check inside pi: `nwdes` reachable (via skill + prompt and via `!nwdes`); `/skill:nw-nwdes` runs, and `/nw-nwdes` maps to `/skill:nw-nwdes`

Not yet proven, does not block the rung:

- [x] Run `uninstall_nwave.py` against a pi install (CLI path tested in `tests/pi/test_pi_uninstall_cli.py`; fixed a missing pi probe in `check_installation`, branch `pi-platform-rung-1`)
- [ ] Decide whether `--platform auto` detects pi (currently explicit `--platform pi` only)

## Rung 2: Cursor / Copilot (guard hook)

Gap docs: [pi-vs-cursor-gaps.md](pi-vs-cursor-gaps.md), [pi-vs-copilot-gaps.md](pi-vs-copilot-gaps.md)

Branch: `pi-platform-rung-2`

Pi already exceeds these on skills, commands and `AGENTS.md`. Only the guard is missing.

- [x] Guard extension: `pi-code` 1.7.0, hooks module only, no nWave extension code ([ADR](research/rung-2/adr-pi-code-for-rung-2.md), [falsifiers](research/rung-2/pi-code-falsifiers.md))
- [x] Add `pi` to `HOSTS` in `nwave_ai/hooks/__main__.py` and `registration.py`
- [x] Installer step: install pinned `pi-code` with the hooks-only filter; uninstall removes it
- [x] Installer step: write the `PreToolUse` entry in pi's `settings.json`
- [x] Installer step: `CLAUDE_CONFIG_DIR` shell function, added to the rc file on request; uninstall removes it
- [x] `verify --platform pi` checks pi-code, the guard entry and the rc block (warn only)
- [x] Tests: hook round trip against real `nwave_ai.hooks`; opt-in real-pi run (`NWAVE_PI_E2E=1`)
- [ ] Optional hygiene: inactive-repo behaviour; orphaned child after a hook timeout

Installer decisions: [ADR](research/rung-2/adr-pi-installer-for-rung-2.md); pi-code install evidence: [falsifier #8](research/rung-2/pi-code-falsifiers.md).

## Rung 3: Codex (roles, delegation, typed reply)

Gap doc: [pi-vs-codex-gaps.md](pi-vs-codex-gaps.md). This is the first rung that needs a real new host feature.

Branch: `pi-platform-rung-3`

- [ ] Named role registry (agent files pi can discover)
- [ ] `spawn_agent`-style delegation tool in a new extension (rung 2 has none; pi-code is hooks only). Starting points: pi's `examples/extensions/subagent` (spawns a `pi` subprocess) and `pi-code`'s own `subagent` tool (dropped by the rung 2 hooks-only filter)
- [ ] Typed reply equivalent of Codex `--output-schema` so roles can return `role_envelope`
- [ ] Installer: pi agents plugin; inline skills into role text and give the tool ceiling as a prompt preamble (model on `codex_agents_plugin.py`)
- [ ] Optional per-role `model`
- [ ] Optional, low priority, not a requirement: wall-clock cap on the `Agent` child (runaway backstop; kill tree, typed failure). No stall detection: the stall guard is the installer's concern. Default is unmeasured (900 s was sized against stalls, not task duration); measure real child durations first. See gap 5 in [subagent-delegation-gaps.md](research/rung-3/subagent-delegation-gaps.md)
- [ ] Verify: tool-ceiling enforcement, model inheritance, session format for `nwdes measure` (use `--requests` until then)

## Rung 4: OMP (commands, extension, autoload)

Gap doc: [pi-vs-omp-gaps.md](pi-vs-omp-gaps.md)

Branch: `pi-platform-rung-4`

- [ ] Emit `/nw-*` commands as pi prompt templates in `~/.pi/agent/prompts/`
- [ ] Skill preload equivalent of `autoloadSkills`
- [ ] `skill://` rewrite (`translate_skill_invocations`) has no pi equivalent; read skills by path instead
- [ ] Check the rung 2 guard (pi-code hooks) against pi's `tool_call` payloads; adapt it if needed (OMP's parses `apply_patch`/hashline edits; pi's `edit` differs)

## Rung 5: Claude Code (full hook set)

Gap doc: [pi-vs-claude-code-gaps.md](pi-vs-claude-code-gaps.md)

Branch: `pi-platform-rung-5`

- [ ] `Agent` tool with `subagent_type`, `maxTurns`, scoped tool grants
- [ ] `SubagentStop`, `SessionStart` (`additionalContext`), `SessionEnd` hooks
- [ ] Guards for `SendMessage`, `TaskCreate`/`TaskUpdate` (tools do not exist in pi; decide whether to add them or drop the guards)
- [ ] `StructuredOutput` reply channel
- [ ] Fresh-context runs for review and EXAMINE
- [ ] `nwave-ai doctor` and container e2e checks for pi

## Cross-cutting

- [ ] Shrink the pi plugin's duplication of the Devin plugin (shared base) before any upstream PR
- [ ] Decide what, if anything, goes upstream vs stays in the fork
- [ ] Verify `@hsingjui/pi-hooks` coverage or drop it (HANDOFF currently says ignore)
