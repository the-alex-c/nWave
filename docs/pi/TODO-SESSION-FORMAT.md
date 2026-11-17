# Session format for `nwdes measure`: TODO

Parity tracking stays in [TODO-PARITY.md](TODO-PARITY.md) (rung 3, Verify). Gap row: [pi-vs-codex-gaps.md](pi-vs-codex-gaps.md), [pi-vs-omp-gaps.md](pi-vs-omp-gaps.md).

## Verified (live, 2026-11-17)

Probe: install at level 3, `Agent` -> `nw-troubleshooter`, session kept with `--session-dir`, then `nwdes measure --host-sessions <root.jsonl>`.

- [x] `nwdes` native mode expects OMP's format (`measurement._session`, `host_sessions.read_tree`): line 1 `title`; line 2 `session` v3 with lowercase UUID; `session_init` with `agent: nw-*` marks a role child; children are `*.jsonl` in a sibling dir named like the root stem; each `message` has a UTC-ms `timestamp`; `bash` toolCall has `arguments.command`.
- [x] pi writes one root file: `session` (v3), `model_change`, `thinking_level_change`, then `message` records (all with timestamps). No `title`, no `session_init`.
- [x] No child files: pi-code runs children with `--no-session`. The `Agent` call is one `toolCall` + `toolResult` in the root.
- [x] Result: `nwdes measure --host-sessions` refuses the root (`First record must be a title`, `Expected a version-3 session...`); every metric is `not measured`.

## Decision

Fallback today: `nwdes measure --requests` (no per-role data from sessions).

- [x] Chosen: **E** ([ADR](research/rung-3/adr-pi-session-format.md), accepted). Options considered:
  - **A. Keep `--requests`.** Document only. Costs nothing; no per-role measurement.
  - **B. pi reader in `nwdes`.** Parse pi's native format. Cleanest; changes `nwdes`, outside pi platform work. Still needs child data (see C); blocked while pi-code stays unmodified.
  - **C. Child session files.** pi-code drops `--no-session` for children (needs a pi-code change: out for now), or the `Agent` wrapper writes child files with `session_init` + `parentSession`. Needed by B and by any synthesis route.
  - **E. Requests log from the `Agent` wrapper.** One record per call, wrapped into the `--requests` array. No pi-code or `nwdes` change; same ceiling as `--requests`.
  - **D. Synthesize OMP-shaped records** (`title`, `session_init`) from pi's root. Fragile; copies a format pi does not own.

## Build E

- [x] `Agent` appends one record per call (also failed ones) to one file per pi session, `$PI_CODING_AGENT_DIR/nwave-requests/<session-id>.jsonl` (default `~/.pi/agent/`; `--requests` has no session field, so a shared file would merge parallel pis into one run): `pi-code-nwave/extensions/agent/index.ts`. Unit-tested (`tests/agent.test.ts`, `requests log`); a log write failure never fails the delegation.
- [x] Array step: `jq -s . ~/.pi/agent/nwave-requests/<session-id>.jsonl > requests.json`, then `nwdes measure --requests requests.json`. Checked with sample records of this shape: `nwdes` accepts them.
- [x] `continuation`/`rework` are always `false`; `task`/`slice` are `null`. Edit the log by hand if a call was a continuation or rework.
- [x] Live check (real pi 1.4.0, pi-code 1.7.0, haiku-4-5): one `Agent` run to `nw-troubleshooter` wrote one record; `jq -s .` then `nwdes measure --requests` reported `role_seconds: nw-troubleshooter 3.121`, `requests: 1`. One run.
- [ ] Files grow without bound; delete old ones. One session holding several features is measured as one run (`--requests` has no scope). Rotate only if that bites.

Not chosen (B, C, D): see the [ADR](research/rung-3/adr-pi-session-format.md), including what to check if native-mode evidence is ever needed on pi.
