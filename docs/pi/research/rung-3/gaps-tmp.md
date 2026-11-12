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
4. **Typed reply: verified (pi 1.4.0). Mechanism offline with faux model ([typed-reply-probe.ts](typed-reply-probe.ts)); real model `claude-haiku-4-5` for parent and child ([typed-reply-probe-real.ts](typed-reply-probe-real.ts)).**
   - Chosen design: submit tool. Fence-strip + retry is not needed as the primary path.
   - Child (full `pi`, loads the same extension) has a `submit_result` tool with the envelope schema. pi validates args in the child: a call missing `summary` got a `Validation failed ...` tool result, the model re-called with valid args. Retry is free and in-loop.
   - Wrapper gets the envelope from `executeTool(...).result.details.results[0].messages` (note: `executeTool` returns `{toolCall, result, isError, durationMs}`; payload is under `result`). Take the last `submit_result` toolCall whose toolResult is not an error.
   - No such call = failing envelope (child ended with text only).
   - Constraint: agent `tools:` must list a built-in too (e.g. `read, submit_result`). pi-code's `unresolvedToolsError` checks only built-ins and MCP aliases, else "would launch with zero tools".
   - Register `submit_result` only when `PI_CODE_SUBAGENT` is set, so the parent never sees it.
   - One schema per tool name: a single role envelope fits; per-role schemas need per-role tool names.
   - Real model (haiku-4-5, n=6): 6/6 called `submit_result` with a valid envelope, 3 with the agent prompt telling it to, 3 with the prompt silent (the tool description alone sufficed). Child often ends with empty final text after submitting, so the envelope must come from the tool call, not the final message.
   - Failing envelope (run, n=1): agent `tools: read` only, no submit tool. Child answered in prose; lookup returned `undefined`. Detected.
   - **Codex comparison (source: `codex/main/codex-rs`).** Codex `--output-schema` is provider-level constrained decoding: `core/src/session/turn.rs` L1875 passes `final_output_json_schema` into the request, `codex-api/src/common.rs` `create_text_param_for_request` sends it as `text.format` `json_schema` (`strict` true except for guardian sessions). The API enforces the shape on the final message; Codex has no client-side validate/retry. pi has no equivalent (provider-specific, not exposed), so the submit tool is the substitute: same schema, enforced by pi validation plus in-loop retry instead of decoding. Difference: the tool path is model-behaviour dependent, constrained decoding is not.
   - **Reuse nWave's frozen schemas.** `nwave_ai/platform/role_envelope_schemas.json` holds 8 per-role schemas (with `if/then`). Run: the `nw-acceptance-designer` schema as the `submit_result` parameters; `{outcome:"rejected", diagnostic:""}` was rejected by pi ("must match then schema"), a corrected call accepted. Offline faux model. So `if/then` works under pi validation.
   - **Revises the one-schema constraint:** schemas are per role, so register one submit tool per covered role (e.g. `submit_<role>`), each listed only in that role's `tools:`; or one tool with the role's schema chosen at child start (no per-call env channel in the wrapper path, so per-role names are the simple option).
   - Model-dependent. Reliable on haiku-4-5; weaker models may skip the tool or send bad args repeatedly (untested; inference). **Decided:** the tool is the only contract. No valid submit after one nudge retry = typed failure to the parent. No prose parsing, no fence-strip fallback.
   - Weak-model remedy is per-model prompt tuning (DSPy-style optimization), not a second reply path. Implies a model-keyed prompt table, selected from the detected model. Not designed yet; not needed until a model fails.
   - Open: nudge text and retry count (one assumed); where the model-keyed prompts live; behaviour on a long/complex task (probe task was `17+25`); other models.
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
