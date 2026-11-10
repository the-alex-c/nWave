# pi platform: master TODO

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

- [ ] Run `uninstall_nwave.py` against a pi install (plugin uninstall is tested; the CLI path is not)
- [ ] Decide whether `--platform auto` detects pi (currently explicit `--platform pi` only)

## Rung 2: Cursor / Copilot (guard hook)

Gap docs: [pi-vs-cursor-gaps.md](pi-vs-cursor-gaps.md), [pi-vs-copilot-gaps.md](pi-vs-copilot-gaps.md)

Branch: `pi-platform-rung-2`

Pi already exceeds these on skills, commands and `AGENTS.md`. Only the guard is missing.

- [ ] New repo `nwave-pi`: pi extension (TypeScript), installed as a pi package
- [ ] Extension on `tool_call` runs `python -m nwave_ai.hooks PreToolUse --host pi`; maps `bash`/`write`/`edit` to `Bash`/`Write`/`Edit`; translates exit 0/1/2 and `permissionDecision`/`updatedInput` back
- [ ] Add `pi` to `HOSTS` in `nwave_ai/hooks/registration.py` and `nwave_ai/hooks/__main__.py`
- [ ] Installer step that installs the `nwave-pi` package
- [ ] Tests: hook shim round trip; extension loads in real pi

## Rung 3: Codex (roles, delegation, typed reply)

Gap doc: [pi-vs-codex-gaps.md](pi-vs-codex-gaps.md). This is the first rung that needs a real new host feature.

Branch: `pi-platform-rung-3`

- [ ] Named role registry (agent files pi can discover)
- [ ] `spawn_agent`-style delegation tool in `nwave-pi` (the existing `examples/extensions/subagent` spawns a `pi` subprocess; starting point only)
- [ ] Typed reply equivalent of Codex `--output-schema` so roles can return `role_envelope`
- [ ] Installer: pi agents plugin; inline skills into role text and give the tool ceiling as a prompt preamble (model on `codex_agents_plugin.py`)
- [ ] Optional per-role `model`
- [ ] Verify: tool-ceiling enforcement, model inheritance, session format for `nwdes measure` (use `--requests` until then)

## Rung 4: OMP (commands, extension, autoload)

Gap doc: [pi-vs-omp-gaps.md](pi-vs-omp-gaps.md)

Branch: `pi-platform-rung-4`

- [ ] Emit `/nw-*` commands as pi prompt templates in `~/.pi/agent/prompts/`
- [ ] Skill preload equivalent of `autoloadSkills`
- [ ] `skill://` rewrite (`translate_skill_invocations`) has no pi equivalent; read skills by path instead
- [ ] Rewrite the guard extension for pi's `tool_call` payloads (OMP's parses `apply_patch`/hashline edits; pi's `edit` differs)

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
