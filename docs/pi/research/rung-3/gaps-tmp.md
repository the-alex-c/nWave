# Rung 3 gaps (temporary)

Temporary working list. Delete or fold into `subagent-delegation.md` when settled.
Sources: [subagent-delegation.md](subagent-delegation.md), [subagent-delegation-notes.md](subagent-delegation-notes.md), [stall-diagnostic.md](stall-diagnostic.md).

## Ranked by risk

1. **Implementation path undecided.** Name is decided (`Agent`, Claude param shape). Path is not.
   - Wrapper: `Agent` calls pi-code `subagent` via `ctx.executeTool`; widen the rung 2 filter; hide `subagent` from the model.
   - Own spawn: nWave registers `Agent` and runs `pi --mode json -p --no-session` itself.
   - The spike tested `subagent`, never `Agent`. Its evidence (discovery, ceiling) holds for the wrapper path. Own spawn is untested.
2. **Wrapper mechanics unverified.**
   - API was read from Cellar `0.85.1` docs; `pi --version` is `1.4.0`.
   - Untested: `ctx.executeTool` exists; a second extension can hide or re-register a tool owned by pi-code; `max_turns` maps (pi-code has `maxTurns` in agent frontmatter only).
   - Checkable with no model calls. Decides item 1.
   - **Source-read result (pi 1.4.0; the Cellar dir name `0.85.1` is misleading, `package.json` says 1.4.0, so the docs match):**
     - `ctx.executeTool(name, args, {signal, onUpdate})` exists in `ExtensionToolContext`; `execute()` receives it as `ctx`. It never rejects: failures return `isError: true`.
     - Nested calls pass through `tool_call`/`tool_result` handlers, so the rung 2 guard sees the nested `subagent` call (name `subagent`, not `Agent`). Not yet run.
     - Notes file is wrong on hiding: `exposure: "hidden"` is *unreachable* (breaks the wrapper), and `direct` is callable only while active (so `setActiveTools()` without `subagent` also breaks it).
     - Right mechanism: `Agent` defines `prepareLoadout()` returning `hiddenDeclarations: ["subagent"]`. The tool stays active and callable; the model is not shown it.
     - New gap: pi-code's `before_agent_start` handler injects a system-prompt section "Delegate isolated tasks with the subagent tool ({agent, task}). Available agents: ...". The model is told about a tool it cannot see. Needs rewriting or suppressing; handler order between the two extensions is unverified.
     - `max_turns`: no call param in pi-code, still unmapped.
     - pi-code refuses nested runs via `PI_CODE_SUBAGENT` env in the child (good: no grandchildren).
     - Still unrun: that `prepareLoadout` hiding actually works with another extension's tool.
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

Item 2: throwaway extension registering `Agent` that calls `subagent` via `ctx.executeTool`. Run on pi 1.4.0 in an isolated `PI_CODING_AGENT_DIR`. No model calls. Outcome picks wrapper or own spawn.
