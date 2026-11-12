# Rung 3 (`Agent` subagent delegation on pi): open gaps, ranked by risk (temporary)

Temporary working list. Delete or fold into `subagent-delegation.md` when settled.
Sources: [subagent-delegation.md](subagent-delegation.md), [subagent-delegation-notes.md](subagent-delegation-notes.md), [stall-diagnostic.md](stall-diagnostic.md).

## Ranked by risk

1. **Implementation path undecided.** Name is decided (`Agent`, Claude param shape). Path is not.
   - Wrapper: `Agent` calls pi-code `subagent` via `ctx.executeTool`; widen the rung 2 filter; hide `subagent` from the model.
   - Own spawn: nWave registers `Agent` and runs `pi --mode json -p --no-session` itself.
   - The spike tested `subagent`, never `Agent`. Its evidence (discovery, ceiling) holds for the wrapper path. Own spawn is untested.
2. **Wrapper mechanics: verified (pi 1.4.0, no model calls; details in [agent-wrapper-mechanics.md](agent-wrapper-mechanics.md)).**
   - `ctx.executeTool` exists and works; the Cellar dir name `0.85.1` is misleading, `package.json` says 1.4.0, docs match.
   - Hiding: `exposure: "hidden"` and `setActiveTools()` break the wrapper. `prepareLoadout()` returning `hiddenDeclarations: ["subagent"]` works across extensions: payload tools are `Read, Bash, Edit, Write, Agent`.
   - Roster leak: pi-code's `before_agent_start` injects "Delegate isolated tasks with the subagent tool...". A later-loaded handler doing `delete event.systemPromptOptions.sections.subagents` removes it (order = load order).
   - Nested hooks: `call Agent`, `call subagent`, `result subagent`, `result Agent`. Rung 2 guard sees `subagent`; it must allow it when nested.
   - New: unknown agent returns `isError: false` with text "Agent failed: ...". Wrapper must detect failure itself.
   - pi-code refuses grandchildren via `PI_CODE_SUBAGENT` env in the child (source-read, not run).
   - Still open: `max_turns` has no call param in pi-code (frontmatter `maxTurns` only), unmapped.

3. **Hook visibility.** Already noted in `subagent-delegation-notes.md` (Open point 4, Risks). Not re-analysed here.
4. **Typed reply has no design.** Spike: child wraps JSON in a fence and ignores format instructions.
   - Options: fence-strip + validate + retry, or a submit tool the child must call.
   - Failing-envelope detection untested.
5. **Stall cause not closed.**
   - Spike hang: 1 of 4 runs; 0 of 24 on the repro harness; 0 of 10 on parent-only control. Root stall also happens with no subagents.
   - Captured stall (PID 86189): open provider socket, no children, reply after 520 s at 100k context. Latency, not a hang.
   - Spike context was tiny, so the latency explanation does not fit the spike hang. Unexplained at n=1.
   - Open: did tokens stream during long calls; does pi-ai set an idle timeout; do reported stalls match the >= 80k cases.
   - pi-code `run.ts` has no parent-side timeout on the child. The wrapper path inherits that; `Agent` needs a cap regardless of cause.
6. **Lower-risk.**
   - Skill inlining unchecked.
   - Children run `--no-session`: `nwdes measure` has nothing to read (use `--requests`).
   - `--tools` argv never captured.
   - Per-role model and `description` mapping unmapped.
7. **Stale docs.** `TODO.md` and `pi-vs-codex-gaps.md` still say "no equivalent". `subagent-delegation.md` still frames the tool as `subagent` and A/B as open.

## Next step

Item 2 DONE: see [agent-wrapper-mechanics.md](agent-wrapper-mechanics.md) "Run results"; wrapper path verified (hiding, roster override, nested hooks work; nested failure is `isError:false`). Decide item 1 = wrapper unless own-spawn needs justify.

(old plan) Item 2: throwaway extension registering `Agent` that calls `subagent` via `ctx.executeTool`. Run on pi 1.4.0 in an isolated `PI_CODING_AGENT_DIR`. No model calls. Outcome picks wrapper or own spawn.
