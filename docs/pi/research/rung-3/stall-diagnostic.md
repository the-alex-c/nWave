# Rung 3 research: root pi session stalls

Status: open. Symptom: a long pi session takes very long or stops responding with no error.
The user kills the process, or waits. Not subagent-specific: it also happens with no subagents.

Related: [subagent-delegation.md](subagent-delegation.md) (parent hang section).

## Runbook: capture the next stall

Run the script (read-only, writes to `~/stall-captures/<timestamp>/`, not the repo):

    docs/pi/research/rung-3/stall-capture.sh 10

It covers steps 1-5 below. Read the report, then decide. Step notes:
- Children include pi-lens LSP servers (marksman, typos-lsp, ast-grep, etc.). They are long-lived and expected.
- The `bash` child running the script itself is you, not a hung tool.
- `pgrep -x pi` misses pi (process name is not `pi`); the script matches on the command word.

Do not kill the process until steps 1-5 are done.

1. Note the time. List pi processes exactly: `pgrep -x pi` (exact name; `pgrep pi` also matches
   unrelated processes such as `pi-lens` helpers, Python, and Apple daemons).
2. CPU and state: `ps -o pid,%cpu,state,etime,command -p <pid>`
   - High CPU: local loop in pi.
   - Near 0% CPU: waiting on I/O or the network.
3. Network: `lsof -a -p <pid> -i`
   - Open TCP socket to the provider (`160.79.104.10:443` seen for Anthropic): waiting on a model stream.
   - No socket: not waiting on the provider.
4. Child processes: `pgrep -P <pid>`
   - A running child (bash, rg, git, node): a tool is hung.
5. Session file: newest file under `~/.pi/agent/sessions/--<cwd-slug>--/`, where `<cwd-slug>` is the
   cwd with `/` replaced by `-`. Read the last 3 entries and the timestamps.
   - Last entry is a user message with no reply after minutes: model request pending.
   - Last entry is assistant `toolUse` with no `toolResult`: that tool is pending.
   - Long gap between entries: note the gap; compare with context size (see Findings 4).
6. Then kill if still needed, and record the result in Findings.

Decision table:

| Evidence | Likely location | Next step |
|---|---|---|
| Open provider socket, no child, last entry user, gap of minutes, large context | provider latency at large context | measure latency vs. context (Findings 4); consider context trimming or model choice |
| Open provider socket, no child, gap > 10 min | provider stream stall | add stream idle timeout upstream |
| Child process running, last entry `toolUse` | that tool | fix the tool; find the command in the child's args |
| No socket, no child, high CPU | pi local loop | profile with `node --cpu-prof` on a repro |
| No socket, no child, idle | pi waiting on something local | check pi's own waits |

## Findings

### 1. Subagent hang (spike, 2026-11-11)

- One of 4 spike runs (parent + pi-code subagent) hung. Signature: child finished, tool result
  emitted, parent never began its next assistant turn, no stderr, no `agent_end`. Killed externally.
- Repro harness, same prompt, 120 s cap: 24 runs, 0 hangs.
- Control, parent only, no extension, 120 s cap: 10 runs, 0 hangs.
- Code: pi-code `subagent/run.ts` resolves on child `close` and has no parent-side timeout.

### 2. Session logs (`~/.pi/agent/sessions`, 334 files, read-only scan)

- Dangling ends: 8 sessions end with a user message or an assistant `toolUse` with no result.
  Lengths 3-144 messages. A kill writes nothing, so these may be kills rather than stalls.
- Stop reasons: `stop` 260, `aborted` 58, `error` 4, `toolUse` 2.
- Errors: `Request timed out.` (3), `fetch failed` (1), `This operation was aborted` (5),
  quota/429 (20, unrelated), model not supported (4).
- The three `Request timed out.` errors fired 10-13 s after the previous entry, not 10 min.

### 3. Source notes

- Anthropic SDK (bundled in pi-coding-agent, v0.129.0): default request timeout 10 min
  (`client.js` L103, L911). Not overridden in the paths grepped; not exhaustively checked.

### 4. Latency vs. context size (session `01a1cd14…`, plus all sessions, 534 assistant replies)

Latency = time from the user/tool-result entry to the next assistant entry (model time only).

| Context tokens | Replies | Median latency | Max |
|---|---|---|---|
| >= 80k | 157 | 5 s | 566 s |
| < 30k | 144 | 2 s | 211 s |

Top latencies, all at large context:
- 566 s, sonnet-5-5, 90.7k context (session from 2026-11-10)
- 520 s, haiku-5-5, 100.7k context (session `01a1cd14`, 2026-11-11 20:30-20:39 local)

The 520 s case: user prompt 20:30:50; pi wrote a `cache_warm` usage entry at 20:35:22 (100,669
cache-write tokens); assistant reply at 20:39:30. Two long calls, each minutes.

Reading: large context makes calls take minutes. The user's "stall" may be this latency rather
than a silent hang. Not yet shown: whether these calls were still streaming or idle.

### 5. Stalled process (captured 2026-11-11 ~20:34-20:43 local)

- PID 86189, started 19:07, S+, 17.9% CPU avg. Open TCP ESTABLISHED to `160.79.104.10:443`. No children.
- Hosts session `01a1cd14` (the conversation where the stall was reported). Still running after the other pi was closed.
- The stalled prompt is the user message at 01:30:50Z, reply at 01:39:30Z (see Findings 4).

### 5b. Prompt-cache expiry vs. latency (948 user-prompt turns, all sessions)

| Idle before prompt | Turns | Median latency | Latency >= 60 s | cacheRead = 0 |
|---|---|---|---|---|
| 0-60 s | 472 | 3 s | 1% | 51% |
| 60-300 s | 357 | 5 s | 3% | 23% |
| 300-3600 s | 105 | 6 s | 2% | 75% |
| > 3600 s | 14 | 5 s | 0% | 86% |

- Cache does expire: after 5+ min idle, most turns read no cache (75-86%).
- Expiry does not explain slow replies: after idle, latency is still a few seconds, and the slow share is
  no higher than at short idle. Expiry raises cost (cache rewrite), not minutes of latency.
- Slow replies (>= 60 s, 51 of ~6,200) are rare and not clearly tied to idle time. Cause still open.

### 6. Ruled out (for the root stall)

- pi-code subagent: root stall also seen without subagents (user report).
- Short-context slowness: contexts under 30k median 2 s.

### Open

- Did the user's stalls match the >= 80k context cases (latency, not hang)? Compare user's
  stall times with session timestamps.
- Whether pi streams tokens during the long calls (watch the socket byte count of PID 86189 over time).
- Whether pi-ai sets a stream idle timeout (not inspected).
- Context size at which latency becomes a problem: needs more sessions.
