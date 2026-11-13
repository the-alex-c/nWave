# pi-code: fit for the rung 2 guard

Package: [pi-code](https://github.com/ilovepixelart/pi-code) 1.7.0, MIT, single maintainer, updated 2026-11-04.
Checkout read: `pi-code/main` at commit `4d30da7` (`extensions/hooks/` is 2.4k lines, plus `extensions/internal/`). Source-read only; nothing was executed in pi.

Goal: run `python -m nwave_ai.hooks PreToolUse --host pi` on pi `bash`/`write`/`edit` calls without writing our own extension (see [TODO-PARITY.md](../../TODO-PARITY.md), rung 2). Sibling analysis, same questions for the other candidate: [pi-claude-hooks-analysis.md](pi-claude-hooks-analysis.md).

## Verdict

Fits for the guard, with one wrapper (non-0/2 exit codes) and the same install-location decision as `pi-claude-hooks`. It is probably the preferred candidate: it fails closed on timeout and spawn failure, and it is the only one with falsifiers run against real pi ([pi-code-falsifiers.md](pi-code-falsifiers.md)). The cost is the extra surface: it ships the whole pi-code suite (subagent, MCP, memory, web and more) and a much larger hooks module, though the hooks-only filter drops the rest. `pi-claude-hooks` stays as the alternative until it gets the same falsifiers. No extension code is needed in nWave either way.

## How the search ended up here

| Candidate | Result |
|---|---|
| `@jordyvanvorselen/pi-claude-hooks` | Alternative. Claude-shaped payloads, `updatedInput`, no subagent tool. Fails open. Standalone, about 1k lines. No falsifiers run. |
| `pi-code` 1.7.0 | **This document.** Fits. Claude-shaped payloads, `updatedInput`, **fails closed on timeout and spawn failure**. All-in-one package with its own subagent; hooks isolated with a package filter (falsifier #1). Probably preferred. |
| `@dianel/pi-hooks-rules` | Fails closed, but no `updatedInput`, so no attribution rewrite. |
| `@hsingjui/pi-hooks` | Raw pi names and fields, fails open. Dropped. |
| Others | Rule-config guards or unrelated. |

## What nWave needs and what the package gives

| Need | Source evidence | Result |
|---|---|---|
| Claude tool names | `internal/claude-tool-names.ts:31,33`: `write`->`Write`, `bash`->`Bash`; `claudeToolName` at `:65` | Yes |
| `tool_input.file_path` | `hooks/claude-tools.ts:37-41,63`: always absolute, resolved the way pi resolves it (`@`, `~`, `file://`) | Yes. Absolute, unlike `pi-claude-hooks`. nWave reads `file_path` and `cwd` (`nwave_ai/hooks/__main__.py:428-451`). |
| Edit shape | `claude-tools.ts:22-23,59-63`: first `edits[]` entry in `old_string`/`new_string`, full array in `edits` when more than one | Yes |
| Matchers `Write`, `Edit`, `Bash` | `hooks/matcher.ts`, `decisions.ts:242-244`: matches the pi name or the Claude name | Yes |
| Payload fields | `hooks/index.ts:319-327`: `session_id`, `cwd`, `permission_mode`, `transcript_path`, `effort`; `decisions.ts:245`: `hook_event_name`, `tool_name`, `tool_input` | Yes. No `agent_type`/`agent_id` (gap 4). |
| Block | `decisions.ts:121-150`: exit 2, `decision: block`, `permissionDecision: deny` | Yes |
| Bash `updatedInput` rewrite (attribution) | `decisions.ts:194-199,249`; `claude-tools.ts:85-86`: translated back to pi shape, replaced in place | Yes |
| `ask`/`defer` | `decisions.ts:141,147`; `index.ts:614`: UI confirm; blocks when no UI | Yes |
| SessionStart / SessionEnd | `index.ts:576,918-923` (SessionEnd on `session_shutdown`) | Yes |
| Fail-closed | `decisions.ts:203-214`: timeout and spawn failure block (default 60 s, `runners.ts:25`). Other exit codes allow (`interpretHookResult`, `decisions.ts:121-133`). | **Partial.** See gap 1. |
| SubagentStop / `agent_type` | `SubagentStop` fires (`index.ts:461,791`) only with the subagent extension loaded; no `agent_type` on tool payloads | **No** for identity |

## Gaps

1. **Exit codes other than 0 and 2 allow.** Timeouts and spawn failures fail closed (`decisions.ts:203-214`), but any other non-zero exit is read as allow, as in Claude Code. An unparseable settings file is not checked in this read.
   - Fix for exit codes: wrap our command so any non-zero exit becomes exit 2, for example `<cmd>; rc=$?; [ $rc -eq 0 ] || exit 2`.
2. **No pi-native hooks location.** Hooks come from the Claude settings chain (`hooks/config.ts:81-83`, `claudeSettingsChain` in `internal/settings-chain.ts:82`): `~/.claude/settings.json` (or `$CLAUDE_CONFIG_DIR`, `internal/config-dir.ts:17-24`) and, for trusted projects, `.claude/settings.json` and `.claude/settings.local.json`. It also loads hooks from Claude plugins (`index.ts:106,528`); not read further.
3. **SessionEnd budget is 1.5 s by default** (`runners.ts:80-90`); a declared per-hook `timeout` raises it up to 60 s. Set an explicit `timeout` on our SessionEnd hook.
4. **No `agent_type`/`agent_id` in tool payloads, and all-in-one package.** `commonPayload` (`index.ts:319`) carries no subagent identity. The identity appears only on SubagentStart/Stop (`index.ts:461,486`). A child `pi` process runs `tool_call` hooks too (`PI_CODE_SUBAGENT=1` skips only Stop, Session* and UserPromptSubmit; `index.ts:576,728,768,817,921`), but a gate cannot tell parent from child.
   - nWave reads `agent_type` for the lane guard (`lane_guard.py:53`) and the subagent host scan (`host_scan.py`, `lifecycle.py:153`).
   - A rung 5 problem for hooks (and a rung 3 one for delegation), not rung 2. It needs a patch that forwards an identity.
   - `package.json:36-41` exports `./extensions/claude-rules.ts` and the whole `./extensions` directory. No flag or environment variable turns a feature off; the `PI_CODE_*` variables are internal. Hooks import nothing from `subagent/`, `mcp/`, `memory`, `todo` or `web`; the seams are runtime only (`internal/subagent-hooks.ts` returns `[]` with no runner). Pi's package filter should drop the subagent: `{"source":"npm:pi-code","extensions":["extensions/hooks/index.ts"]}` or `!extensions/subagent/**`. Not tested; also check what `claude-rules.ts` needs.
5. **Matching hooks run in parallel** (`decisions.ts:246-253`). Another hook that also rewrites Bash input can race ours (`applyUpdatedInput` mutates the shared input).
6. **Untrusted projects** load no project hooks (`hookFiles(cwd, home, trusted)`, `config.ts:81`; `index.ts:495`). `disableAllHooks` anywhere in the settings chain turns every hook off, including our guard (`config.ts:90-92`).
7. **Size and coupling.** The hooks module leans on `internal/` helpers (settings chain, project approval, managed settings, shell resolve and others). Forking it means carrying them. Peer dependencies on pi are `*` (`package.json:59-65`), but `extensions/version-floor.ts` and `internal/pi-floor.ts` warn below a minimum pi version. Recheck on each pi upgrade. Not pre-1.0 (1.7.0), still a single maintainer.

## Where the hooks go (open decision)

Same options as in the `pi-claude-hooks` analysis, with one extra.

| Option | Consequence |
|---|---|
| (a) `~/.claude/settings.json` | Shared with Claude Code. If both `--host claude` and `--host pi` entries are there, they fire twice in both hosts. Works only by reusing the Claude entries. |
| (b) Per-project `.claude/nwave-pi.json` | Not read: the chain lists fixed file names only. Would need `.claude/settings.local.json` or a patch. |
| (c) Small upstream change or fork adding a `~/.pi/agent/` hooks file | Clean. Costs a PR, and the hooks module is large. |
| (d) `CLAUDE_CONFIG_DIR=~/.pi/agent` for the pi process | pi-code reads `<dir>/settings.json`. Needs the variable set wherever pi starts, and it also redirects the other pi-code readers. Not tested. |

Recommendation: (c) long term. (d) is the cheapest, and falsifier #5 passed, so use it first.

## Rung 2 work if this is adopted

- Add `pi` to `HOSTS` in `nwave_ai/hooks/__main__.py:61`. It is only an argparse choice; the host maps to `claude-code` for everything except `codex` (`__main__.py:674`). Probably not needed in `registration.py` (no file merge for pi). Not verified: whether any invariant requires the two `HOSTS` tuples to match.
- Installer step: install the package (`pi install npm:pi-code`) with the package filter that keeps hooks only, and write the hooks entries, with the exit-code wrapper and explicit timeouts.
- Tests: hook round trip with a stub; real-pi run (isolated `PI_CODING_AGENT_DIR`).

## Falsifiers to run before committing

Results: [pi-code-falsifiers.md](pi-code-falsifiers.md) (#1 to #5 passed).

1. Real pi 1.4.0: install the package with the hooks-only filter, point a logging hook at it, run `bash`, `write` and `edit`. Check the payload, the exit-2 block, and that the subagent tool is absent from pi's tool list.
2. `updatedInput` on `bash` changes the command pi runs.
3. The wrapped non-zero-to-2 command blocks a call; a hook that sleeps past its timeout also blocks.
4. With pi's example subagent extension, check that `tool_call` hooks also fire in the child `pi` process (global install, trusted project), and what the payload lacks.
5. `CLAUDE_CONFIG_DIR=<isolated dir>`: hooks are read from there and not from `~/.claude`.
