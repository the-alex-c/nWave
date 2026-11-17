# ADR: how `nwdes measure` reads pi sessions

Status: accepted (option E). Evidence and probe: [TODO-SESSION-FORMAT.md](../../TODO-SESSION-FORMAT.md). Related: [adr-pi-delegation-for-rung-3.md](adr-pi-delegation-for-rung-3.md) (children run `--no-session`; the `Agent` wrapper sees child messages).

## Context

`nwdes measure --host-sessions` reads OMP's session layout: a `title` first record, a `session` v3 record, a `session_init` record naming the role, and one `*.jsonl` per child in a sibling directory. pi writes a single root file with no `title` and no `session_init`, and pi-code runs children with `--no-session`. The native mode therefore refuses every pi session (live probe). Today the only working path is `--requests`.

## Options

- **A. Keep `--requests`.** Document only.
- **B. pi reader in `nwdes`.** `nwdes` learns pi's native root format.
- **C. Child session files.** Children stop being `--no-session`, or the `Agent` wrapper writes a file per child.
- **D. Records synthesized by the `Agent` wrapper.** The wrapper writes OMP-shaped files (root and children) that `nwdes` already reads.
- **E. Requests log from the `Agent` wrapper.** The wrapper appends one record per call (`role`, `task`, `slice`, `start`, `end`, `continuation`, `rework`) to a log; a small step wraps it into the array `nwdes measure --requests` takes. No change to pi-code or `nwdes`; no session files.

B alone is not enough: with no child files there is nothing for a reader to read. B needs C. D includes C.

Constraints (user): no own spawn wrapper; pi-code stays unmodified. C by patching pi-code is therefore out, so B is blocked. Remaining: A, D, E.

E tradeoffs: automates only what `--requests` already offers (per-role time, request counts, max concurrency; "supplied, not host-recorded"; no commit-history or `--rework` evidence). `continuation`/`rework` are unknown to the wrapper and default to `false` unless the caller supplies them. Open: log location and who builds the array.

## Decision

**E.** The `Agent` wrapper appends one request record per call to a log; a small step wraps it into the array `nwdes measure --requests` takes.

Why: `nwdes measure` is an after-the-fact report, not a route step (`nw-nwdes` skill: "Measurement is not a route step"). E needs no pi-code change, no own spawn wrapper and no change to `nwdes`, and it matches the fallback the parity doc already names.

Rejected:
- **A.** Nothing produces the `--requests` file today; E automates it.
- **B, C.** Need child session files, which need a pi-code change (out of scope; a runtime `spawn` patch from the wrapper was considered and declined).
- **D.** Copies OMP's format, which pi does not own; measures an imitation of a session.

## Consequences

- Numbers are "supplied, not host-recorded". No commit-history binding, `--candidate`, `--rework` session pairs or bash-occurrence evidence on pi.
- `continuation` and `rework` default to `false` unless the caller supplies them.
- Revisit B/C if native-mode evidence is needed on pi.

## If B, C or D is revisited

- Check whether pi writes anything `nwdes` could use for role detection (the `agent` name is only in the `Agent` toolCall arguments today).
- Check child message shape: timestamps, `bash` `arguments.command`.
- Test against a live probe (`NWAVE_PI_E2E=1`).
- C needs a pi-code change (or a runtime `spawn` patch, declined); B needs C.
