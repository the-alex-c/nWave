# ADR: use pi-code for the rung 2 guard

Date: 2026-11-10. Status: accepted.

## Context

Rung 2 needs one thing on pi: run the nWave guard
(`python -m nwave_ai.hooks PreToolUse`) before `bash`, `write` and `edit` calls.
We looked for an existing pi extension to do this, so nWave carries no extension code.

## Decision

Use [pi-code](https://github.com/ilovepixelart/pi-code) 1.7.0, hooks module only.
We write no pi extension.

## Why

- It sends Claude-shaped hook payloads, so the nWave guard needs no change.
- It supports `updatedInput`, so the commit-attribution rewrite works.
- It blocks on timeout and on spawn failure. The other candidate that sends Claude-shaped payloads, `pi-claude-hooks`, lets those calls through.
- Tested on real pi 1.4.0, including the real nWave guard: block, allow and rewrite all work ([results](pi-code-falsifiers.md)).

## Rejected

| Candidate | Reason |
|---|---|
| `@jordyvanvorselen/pi-claude-hooks` | Fits, but fails open on timeout and spawn failure. Never tested. Not needed now. |
| `@dianel/pi-hooks-rules` | No `updatedInput`, so no attribution rewrite. |
| `@hsingjui/pi-hooks` | Raw pi names and fields. Fails open. |
| Our own extension | Costs code we do not need. pi-code already works. |

## Conditions

1. Install with the hooks-only filter: `{"source":"npm:pi-code","extensions":["extensions/hooks/index.ts"]}`. This drops the subagent, MCP, memory and web tools.
2. Wrap the hook command so any non-zero exit becomes exit 2: `<cmd>; rc=$?; [ $rc -eq 0 ] || exit 2`. Without it, exit 1 and a missing script allow the call. Always set an explicit `timeout`.
3. Register the hook at user level with `CLAUDE_CONFIG_DIR=~/.pi/agent`. Project-level hooks do not load in untrusted projects.
4. Add `pi` to `HOSTS` in `nwave_ai/hooks/__main__.py`. Until then, `--host pi` is rejected and the wrapper blocks every call.

## Accepted risks

- One maintainer.
- pi-code warns below a minimum pi version. Recheck on each pi upgrade.
- `disableAllHooks` in the Claude settings chain turns the guard off.
- The payload has no `agent_type`. The lane guard cannot tell parent from child. This is a rung 5 problem.
- The installer must make `CLAUDE_CONFIG_DIR` reach the pi process.

## More

- [pi-code-analysis.md](pi-code-analysis.md): source read, gaps.
- [pi-code-falsifiers.md](pi-code-falsifiers.md): test runs #1 to #6.
- [pi-claude-hooks-analysis.md](pi-claude-hooks-analysis.md): the other candidate.
- [TODO-PARITY.md](../../TODO-PARITY.md): rung 2 work.
