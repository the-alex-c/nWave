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

- [x] Run `uninstall_nwave.py` against a pi install (CLI path tested in `tests/pi/test_pi_uninstall_cli.py`; fixed a missing pi probe in `check_installation`, branch `pi-platform-rung-1`)
- [ ] Decide whether `--platform auto` detects pi (currently explicit `--platform pi` only)

## Rung 2: Cursor / Copilot (guard hook)

Gap docs: [pi-vs-cursor-gaps.md](pi-vs-cursor-gaps.md), [pi-vs-copilot-gaps.md](pi-vs-copilot-gaps.md)

Branch: `pi-platform-rung-2`

Pi already exceeds these on skills, commands and `AGENTS.md`. Only the guard is missing.

- [x] Guard extension chosen: `pi-code` 1.7.0, hooks module only, no nWave extension code. [ADR](research/rung-2/adr-pi-code-for-rung-2.md); evidence in [pi-code-falsifiers.md](research/rung-2/pi-code-falsifiers.md) #1 to #6 (real nWave guard blocks, allows and rewrites through pi)
- [x] Add `pi` to `HOSTS` in `nwave_ai/hooks/__main__.py` (test: `tests/pi/test_pi_hook_host.py`). `registration.py` `HOSTS` left alone: it lists file-merge hosts only, and `omp`/`opencode` are already absent there, so the tuples need not match
- [ ] Installer step: `pi install npm:pi-code` with the hooks-only filter `{"source":"npm:pi-code","extensions":["extensions/hooks/index.ts"]}` in pi's settings
- [ ] Installer step: write the `PreToolUse` entry (matcher `Bash|Write|Edit`) with the exit-code wrapper `<cmd>; rc=$?; [ $rc -eq 0 ] || exit 2` and an explicit `timeout`
- [x] Hook file location: `~/.pi/agent/settings.json`, shared with pi's own keys. Coexistence passes ([falsifier #7](research/rung-2/pi-code-falsifiers.md))
- [x] Decision: `CLAUDE_CONFIG_DIR=~/.pi/agent` reaches pi through a shell function, not a global export (that moves Claude Code's config) and not an alias. The guard fails open without it (#7)
- [x] Installer step: print `pi() { CLAUDE_CONFIG_DIR="$HOME/.pi/agent" command pi "$@"; }`; on a TTY, ask to add it to the rc file chosen from `$SHELL` (zsh `~/.zshrc`; bash `~/.bash_profile` on macOS, `~/.bashrc` on Linux; other shells print only). Marked block, idempotent, `--shell-rc yes|no` (default: ask on TTY, else print only). Code: `scripts/shared/pi_shell_rc.py`, wired in `pi_skills_plugin.py`. Deviation: the rc path is not recorded in the pi manifest (its strict schema would need a format change); uninstall instead strips the marked block from `.zshrc`, `.bash_profile` and `.bashrc`
- [x] Uninstall removes exactly the marked rc block. Tests: `tests/pi/test_pi_shell_rc.py`, `tests/pi/test_pi_shell_rc_wiring.py`
- [ ] `verify --platform pi` checks the rc block and warns when `CLAUDE_CONFIG_DIR` is not set in the current environment (IDE, cron or other-shell launches still fail open)
- [ ] Tests: hook round trip against real `nwave_ai.hooks` (stub exit codes, wrapper); real-pi run in an isolated `PI_CODING_AGENT_DIR` through the installer, not hand-built config
- [ ] Optional hygiene: inactive-repo behaviour; orphaned child after a hook timeout

## Rung 3: Codex (roles, delegation, typed reply)

Gap doc: [pi-vs-codex-gaps.md](pi-vs-codex-gaps.md). This is the first rung that needs a real new host feature.

Branch: `pi-platform-rung-3`

- [ ] Named role registry (agent files pi can discover)
- [ ] `spawn_agent`-style delegation tool in a new extension (rung 2 has none; pi-code is hooks only). Starting points: pi's `examples/extensions/subagent` (spawns a `pi` subprocess) and `pi-code`'s own `subagent` tool (dropped by the rung 2 hooks-only filter)
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
