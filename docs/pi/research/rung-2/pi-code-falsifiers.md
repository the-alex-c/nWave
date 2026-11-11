# pi-code: falsifier results

Run log for the falsifiers in [pi-code-analysis.md](pi-code-analysis.md). One section per falsifier; add as they run.

| # | Falsifier | Result | Date |
|---|---|---|---|
| 1 | Hooks-only install, payload, exit-2 block, no subagent tool | **Pass** | 2026-11-10 |
| 2 | `updatedInput` on `bash` | **Pass** | 2026-11-10 |
| 3 | Non-zero-to-2 wrapper; timeout blocks | **Pass** | 2026-11-10 |
| 4 | Child `pi` process fires `tool_call` hooks; payload gaps | **Pass** (hooks fire; identity gap confirmed) | 2026-11-10 |
| 5 | `CLAUDE_CONFIG_DIR` redirects hook lookup | **Pass** | 2026-11-10 |
| 6 | Real nWave guard (`nwave_ai.hooks`) behind the wrapper: block, allow, rewrite | **Pass** | 2026-11-10 |

## 1. Hooks-only install, payload, block

**Setup.** pi 1.4.0, pi-code 1.7.0 (`pi install npm:pi-code`). Isolated `PI_CODING_AGENT_DIR` and `CLAUDE_CONFIG_DIR`, scratch git repo as cwd, model `anthropic/claude-haiku-4-5` (`pi -p --mode json --no-session --offline`). `auth.json` symlinked from `~/.pi/agent`. Pi settings:

```json
{"packages":[{"source":"npm:pi-code","extensions":["extensions/hooks/index.ts"]}]}
```

Hook: `PreToolUse`, matcher `Bash|Write|Edit`, `timeout: 10`, in `$CLAUDE_CONFIG_DIR/settings.json`. The script appends stdin to a JSONL file and exits 2 when the input contains `BLOCKME`, else 0.

Prompt: `bash echo hello-bash`; `write a.txt 'one'`; `edit a.txt one->two`; `bash echo BLOCKME`; then list the tool names.

**Results.**

| Check | Result |
|---|---|
| Payload tool names | `Bash`, `Write`, `Edit` |
| Payload fields | `session_id`, `cwd`, `permission_mode` (`default`), `tool_use_id`, `hook_event_name`, `tool_name`, `tool_input` |
| `Write` / `Edit` `file_path` | Absolute |
| `Edit` shape | `old_string`, `new_string`, `replace_all:false` |
| Exit 2 | `echo BLOCKME` did not run. Tool result `isError:true`, text = hook stderr |
| Allowed calls | Ran. `a.txt` ended as `two` |
| Tools, filtered install | `Read, Bash, Edit, Write` |
| Tools, unfiltered baseline | `Read, Bash, Edit, Write, memory, plan_mode_complete, question, subagent, todo, web_search, web_fetch` |

**Deviations from the analysis.**

- No `transcript_path` or `effort` in the payload (the analysis lists both from `index.ts:319-327`). nWave treats `transcript_path` as optional (`nwave_ai/hooks/hosts.py:172`). `effort` has no hit under `nwave_ai/hooks`.
- The `read` tool was not covered; the matcher did not include it.

**Limits.**

- Tool lists come from the model's self-report, not from pi's request body.
- Only the `PreToolUse` path ran. No SessionStart/End, no `ask`/`defer`.
- One run, one model.
- Falsifier 5 is only partly shown: hooks fired from `$CLAUDE_CONFIG_DIR`. That `~/.claude/settings.json` is ignored was not checked.
- The package filter is now tested for dropping `subagent`. `claude-rules.ts` was excluded by the filter; what hooks need from it is still open (nothing broke).

## 2. `updatedInput` on `bash`

**Setup.** Same isolated pi as #1. Hook matcher `Bash`. On stdout the hook prints `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","updatedInput":{...}}}` and exits 0. Prompt: three `bash` calls, one per case.

| Case | Hook output | What pi ran / returned |
|---|---|---|
| Full rewrite | `{"command":"echo rewritten-ok"}` | `rewritten-ok` (original `echo REWRITEME-original` did not run) |
| Append (attribution-shaped) | original command `&& echo appended-ok` | `APPENDME-original` then `appended-ok` |
| Incomplete rewrite | `{"timeout":5}` (no `command`) | Original ran unchanged (`BADREWRITE-original`) |

**Notes.**

- pi's `tool_execution_start` event (and so the `--mode json` stream) shows the **pre-rewrite** input. Only the result shows the rewritten command. Do not use the stream's `args` to audit what ran.
- First attempt hung for 3 min with an empty output file and no hook call; the retry (stdin from `/dev/null`) ran in seconds. Cause unknown; possibly a stdin wait. Run pi with `< /dev/null` in scripts.
- Only `bash` was tested. The `write`/`edit` mappings (`claude-tools.ts` `FROM_CLAUDE_INPUT`) were read, not run.

## 3. Non-zero-to-2 wrapper; timeout blocks

**Setup.** Same isolated pi as #1 (copy of its `PI_CODING_AGENT_DIR`, hooks-only filter), one run per case, own `CLAUDE_CONFIG_DIR` each. Hook matcher `Bash`, `timeout: 2`. Prompt: one `bash` call `touch ran-<case> && echo ran-<case>`; the marker file shows whether the call executed. Wrapper: `<cmd>; rc=$?; [ $rc -eq 0 ] || exit 2`.

| Case | Hook | Marker | Tool result |
|---|---|---|---|
| A | raw, exit 1 | **present** (ran) | normal output |
| B | wrapped, exit 1 | absent | `isError` text = inner stderr |
| C | wrapped, exit 3 | absent | inner stderr |
| D | raw, sleeps 20 s | absent | `Hook timed out after 2000ms: <cmd>` |
| E | wrapped, sleeps 20 s | absent | same timeout text |
| F | raw, missing script (shell exit 127) | **present** (ran) | normal output |
| G | wrapped, missing script | absent | `/bin/sh: ...: No such file or directory` |
| H | wrapped, exit 0 (control) | present | normal output |

**Notes.**

- Confirms gap 1: raw non-zero exits other than 2 allow, including 127 for a missing hook script. A typo in the registered command fails open without the wrapper.
- The wrapper fixes both. The inner stderr still reaches the tool result.
- Timeout blocks with or without the wrapper (2 s took effect; run took about 6 s end to end).
- A missing script is exit 127 from the shell, not a spawn failure, so the "spawn failure blocks" path (`decisions.ts:203-214`) was not exercised. Not tested: spawn failure proper (for example no `/bin/sh`).
- Timeout kill: the `sleep 20` child was not checked for orphaning after the hook was killed.
- First attempt was void: macOS has no `timeout`, pi never started. Use `perl -e 'alarm N; exec @ARGV'`.
- One model, `PreToolUse` on `bash` only.

## 4. Child `pi` process: hooks fire, identity gap

**Setup.** Isolated pi as #3 (pi-code hooks-only filter, `CLAUDE_CONFIG_DIR` with a logging hook on `PreToolUse`, `SessionStart`, `UserPromptSubmit`, `Stop`; no matcher). pi's example subagent extension symlinked into `$PI_CODING_AGENT_DIR/extensions/subagent`; `scout.md` agent in `$PI_CODING_AGENT_DIR/agents/`. The hook logs stdin, `$PI_CODE_SUBAGENT` and its parent pid. Prompt: one `subagent` call (agent `scout`, task: run `bash echo CHILD-MARK`). Project directory is not a Claude-trusted one; hooks come from the user-level `CLAUDE_CONFIG_DIR`.

| Process (hook parent pid) | Events logged |
|---|---|
| Parent (51445) | `SessionStart`, `UserPromptSubmit`, `PreToolUse` (`tool_name` `Agent`, input `{agent, task}`), `Stop` |
| Child (51472) | `SessionStart`, `UserPromptSubmit`, `PreToolUse` (`Bash`, `echo CHILD-MARK`), `Stop` |

**Results.**

- The child `pi` process runs the hooks, including `PreToolUse` on its `bash` call. The child inherits `PI_CODING_AGENT_DIR` and `CLAUDE_CONFIG_DIR`, so a guard registered for the parent also guards children.
- Payload fields are identical in both processes (`session_id`, `cwd`, `permission_mode`, `effort`, `tool_use_id`, `hook_event_name`, `tool_name`, `tool_input`). No `agent_type`, `agent_id`, parent session id or any other subagent marker.
- The child has its own `session_id` (parent `01a1c7e8-c015-…`, child `01a1c7e8-d1c9-…`). The hook cannot tell from the payload that one is a child; the only link is the process tree.
- `PI_CODE_SUBAGENT` is empty in both. The example extension does not set it (pi-code's own subagent does). So the skip rule for Stop, `Session*` and `UserPromptSubmit` (`index.ts:576,728,768,817,921`) did not apply: the child fired all four. A guard that relies on those events once per session would run twice per delegation.
- The example subagent tool shows as `Agent` in `tool_name`, with `tool_input` `{agent, task}` (not Claude's `subagent_type`/`prompt`).
- `effort` is present here (a `-p` run); #1 reported it absent. Not investigated; payload may vary by mode or model.

**Limits.** pi-code's own subagent was not run (filtered out), so its `SubagentStart`/`SubagentStop` and `PI_CODE_SUBAGENT` behaviour is unverified. One model, one delegation, no trusted-project variant, no `ask`/`defer`.

## 5. `CLAUDE_CONFIG_DIR` redirects hook lookup

**Setup.** Isolated pi as #3. Fake `HOME` (so the real `~/.claude` is untouched) with three `PreToolUse` `Bash` hooks, each appending its tag to a file: A in `$HOME/.claude/settings.json`, B in `$CLAUDE_CONFIG_DIR/settings.json`, C in `<cwd>/.claude/settings.json` (scratch git repo, not marked trusted anywhere). Two runs, one `bash echo f5` call each.

| Run | Fired |
|---|---|
| `CLAUDE_CONFIG_DIR` set | **B only** |
| `CLAUDE_CONFIG_DIR` unset (control) | **A only** |

**Results.**

- With the variable set, `$HOME/.claude/settings.json` is not read. The unset control shows the file would be read otherwise, so the miss is not a setup error. This completes option (d): `CLAUDE_CONFIG_DIR=<dir>` gives a pi-only hooks file, with no interference from Claude Code's `~/.claude`.
- Project hook C fired in neither run. The project was not trusted, which matches gap 6 (untrusted projects load no project hooks). So a project-level guard cannot be relied on without a trust step; user-level hooks in the redirected dir do not have this problem. Trust approval was not tested.
- The variable must reach the pi process. It also redirects other pi-code readers of the config dir (not enumerated).

**Limits.** One model, `PreToolUse` on `bash`. Hooks in Claude plugins (`index.ts:106,528`) and managed settings were not checked; they may still load.

## 6. Real nWave guard end to end

**Setup.** Isolated pi as #1 (fresh `pi install npm:pi-code`, hooks-only filter). Scratch git repo, activated with `.nwave/config.json` `{"enabled": true}`; `NWAVE_AGENTS_HOME` and `CLAUDE_CONFIG_DIR` isolated. `PreToolUse`, matcher `Bash|Write|Edit`, `timeout: 30`, command `<repo>/.venv/bin/python -m nwave_ai.hooks PreToolUse --host claude; rc=$?; [ $rc -eq 0 ] || exit 2`, plus a logging hook. `--host claude` because `pi` is not yet in `HOSTS` (`__main__.py:61`); the host only picks the argparse choice, both map to `claude-code`. Repo state before: tracked `t.txt` dirty, untracked `execution-log.json` = `a`. Model `anthropic/claude-haiku-4-5`, six sequential calls.

| # | Call | Guard (stdin run first) | In pi | Effect |
|---|---|---|---|---|
| 1 | `bash: git stash` | exit 2, `decision: block` | `isError`, text = guard reason | `t.txt` still dirty, `git stash list` empty |
| 2 | `bash: echo hello-bash` | exit 0, stdout has a `freshness.stale` JSON line | ran, normal output | pi ignored the stray stdout JSON |
| 3 | `bash: git commit --allow-empty -m hello` | exit 0, `updatedInput` | ran rewritten | commit body carries the nWave trailers |
| 4 | `write: execution-log.json` | exit 2, block | `isError`, guard reason | file still `a` |
| 5 | `write: ok.txt` | exit 0 | ran | `ok.txt` = `fine` |
| 6 | `edit: execution-log.json` | exit 2, block | `isError`, guard reason | file still `a` |

**Results.**

- The real guard blocks, allows and rewrites through pi-code exactly as it does on stdin. Block reasons reach the model as the tool result.
- Logger saw the same payload for all six calls: `session_id`, `cwd`, `permission_mode`, `effort`, `tool_use_id`, `hook_event_name`, `tool_name`, `tool_input`. `Write`/`Edit` `file_path` absolute. nWave needed nothing more.
- `git stash` is blocked before the activation gate; the other blocks and the rewrite needed an activated repo (not re-tested inactive here).
- `--host pi` is rejected by argparse (exit 2) today, so with the wrapper every call would be blocked. `pi` must be added to `HOSTS` before the registered command can use it.

**Limits.** One run, one model. Single-entry `edit` only; a multi-edit `edits[]` payload was not sent. `write`/`edit` `updatedInput` not exercised (nWave only rewrites Bash). Hooks ran from `$CLAUDE_CONFIG_DIR` at user level; a trusted-project variant, `SessionStart`/`SessionEnd`, `ask`/`defer` and a sub-agent were not run. The `freshness.stale` line appears because the scratch home has no install manifest.
