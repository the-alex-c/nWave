# pi-claude-hooks: fit for the rung 2 guard

Package: [@jordyvanvorselen/pi-claude-hooks](https://github.com/jordyvanvorselen/pi-claude-hooks) 0.1.2, MIT, single maintainer, pre-1.0.
Checkout read: `pi-claude-hooks/main` (about 1,000 lines in `src/`, plus `extensions/claude-hooks.ts`). Source-read only; nothing was executed in pi.

Goal: run `python -m nwave_ai.hooks PreToolUse --host pi` on pi `bash`/`write`/`edit` calls without writing our own extension (see [TODO.md](../../TODO.md), rung 2).

## Verdict

Fits for the guard, with one wrapper (fail-open) and one install-location decision. No extension code is needed in nWave. Probably not the preferred candidate: [pi-code](pi-code-analysis.md) fails closed and has falsifiers run against real pi. This one has none yet.

## How the search ended up here

| Candidate | Result |
|---|---|
| `@jordyvanvorselen/pi-claude-hooks` | **This document.** Claude-shaped payloads, `updatedInput`, no subagent tool. Fails open. Alternative. |
| `pi-code` 1.7.0 | Also fits. All-in-one package with its own subagent. Its hooks can be isolated (`extensions/hooks/index.ts`); tested in [pi-code-falsifiers.md](pi-code-falsifiers.md) #1. Probably preferred. |
| `@dianel/pi-hooks-rules` | Fails closed, but no `updatedInput`, so no attribution rewrite. |
| `@hsingjui/pi-hooks` | Raw pi names and fields, fails open. Dropped. |
| Others | Rule-config guards or unrelated. |

## What nWave needs and what the package gives

| Need | Source evidence | Result |
|---|---|---|
| Claude tool names | `src/tools.ts:1-10`: `bash`->`Bash`, `write`->`Write`, `edit`->`Edit` | Yes |
| `tool_input.file_path` | `src/tools.ts:30-44`: copied from `path` for read/write/edit. The path is not resolved, so it can be relative. | Yes. Hooks run with `cwd` = session cwd (`claude-hooks.ts:78-92`). nWave reads `file_path` and `cwd` (`nwave_ai/hooks/__main__.py:428-451`). |
| Edit shape | `src/tools.ts:35-39`: `old_string`/`new_string` joined from `edits[]` | Yes |
| Matchers `Write`, `Edit`, `Bash` | `src/matcher.ts:42`: matches either the pi or the Claude name | Yes |
| Payload fields | `claude-hooks.ts:55-63`: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `permission_mode` | Yes. No `agent_type`. |
| Block | `src/output.ts:68-69,100-110`: exit 2, `decision: block`/`deny`, `permissionDecision: deny` | Yes |
| Bash `updatedInput` rewrite (attribution) | `claude-hooks.ts:211-215`, `src/tools.ts:51-100`: bash passes through; in-place replace | Yes |
| `ask`/`defer` | `claude-hooks.ts:204-209`: UI confirm; blocks when no UI | Yes |
| SessionStart / SessionEnd | `claude-hooks.ts:146-162` | Yes |
| Fail-closed | See gap 1 | **No** |
| SubagentStop / `agent_type` | No subagent code in the package | **No** |

## Gaps

1. **Fails open.** A timeout (`output.ts:63-66`), any exit code other than 0 or 2 (`output.ts:72-73`) and a spawn failure (`runner.ts:117-120`) only notify and let the call through. An unparseable settings file is skipped with a warning (`config.ts:101-104`).
   - Fix for exit codes: wrap our command so any non-zero exit becomes exit 2, for example `<cmd>; rc=$?; [ $rc -eq 0 ] || exit 2`.
   - A timeout and an unparseable settings file cannot be wrapped away. The installer must verify them.
2. **No pi-native hooks location.** It reads only `~/.claude/settings.json` and, for trusted projects, `.claude/settings.json`, `.claude/settings.local.json` and other `.claude/*.json` files (`config.ts:68-75`). `~/.pi/agent/claude-hooks.json` holds options only (`config.ts:33`), not hooks.
3. **SessionEnd timeout is 1.5 s by default** (`config.ts:20,168`). Set an explicit `timeout` on our SessionEnd hook.
4. **No `SubagentStop`, no `agent_type`.** A rung 5 problem, not rung 2.
5. **Matching hooks run in parallel** (`engine.ts:43`). Another hook that also rewrites Bash input can race ours.
6. **Untrusted projects** load no project hooks, only a warning (`claude-hooks.ts:36-42`).
7. **Pre-1.0**, single maintainer. Pi peer dependency is `*`; dev-tested against `^1.4.0` (local pi is 1.4.0).

## Where the hooks go (open decision)

| Option | Consequence |
|---|---|
| (a) `~/.claude/settings.json` | Shared with Claude Code. If both `--host claude` and `--host pi` entries are there, they fire twice in both hosts. Works only by reusing the Claude entries. |
| (b) Per-project `.claude/nwave-pi.json` | Claude Code ignores it. Needs a project install and a trusted project. |
| (c) Small upstream change or fork adding a `~/.pi/agent/` hooks file | Clean. Costs a PR to a pre-1.0 package. |

Recommendation: (c). (b) works as a first step.

## Rung 2 work if this is adopted

- Add `pi` to `HOSTS` in `nwave_ai/hooks/__main__.py:61`. It is only an argparse choice; the host maps to `claude-code` for everything except `codex` (`__main__.py:674`). Probably not needed in `registration.py` (no file merge for pi). Not verified: whether any invariant requires the two `HOSTS` tuples to match.
- Installer step: install the package (`pi install npm:@jordyvanvorselen/pi-claude-hooks`) and write the hooks entries, with the fail-closed wrapper and explicit timeouts.
- Tests: hook round trip with a stub; real-pi run (isolated `PI_CODING_AGENT_DIR`).

## Falsifiers to run before committing

1. Real pi 1.4.0: install the package, point a logging hook at it, run `bash`, `write` and `edit`. Check the payload and the exit-2 block.
2. `updatedInput` on `bash` changes the command pi runs.
3. The wrapped non-zero-to-2 command blocks a call.
4. With pi's example subagent extension, check that `tool_call` hooks also fire in the child `pi` process (global install, trusted project).
