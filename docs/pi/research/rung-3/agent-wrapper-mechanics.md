# Rung 3 research: `Agent` wrapping pi-code `subagent` (gap 2)

Status: source-read only. Nothing executed. Resolves part of gap 2 in [gaps-tmp.md](gaps-tmp.md)
and corrects [subagent-delegation-notes.md](subagent-delegation-notes.md) ("Alias option").

## Question

Can an nWave extension register `Agent(subagent_type, prompt, ...)` that delegates to pi-code's
`subagent` tool, with `subagent` hidden from the model, on the installed pi?

## Version

`pi --version` is `1.4.0`. The install path is `Cellar/pi-coding-agent/0.85.1/...`, but its
`package.json` says `1.4.0`. The docs and `dist/*.d.ts` under that path therefore match the
running pi. The earlier worry about a docs/version mismatch does not hold.

## Findings

1. **`ctx.executeTool` exists.**
   - `ExtensionToolContext.executeTool(name, args, { signal, onUpdate })` (`dist/core/extensions/types.d.ts` L280).
   - `execute(toolCallId, params, signal, onUpdate, ctx)` receives it as `ctx` (L505-ish).
   - It never rejects: unknown tools, validation errors, blocked calls and thrown errors return `isError: true`.
2. **Nested calls reach hooks.** Nested calls pass argument validation and the `tool_call` /
   `tool_result` handlers like model calls, with `parentToolCallId` on events. The guard from rung 2
   should see the nested call under the name `subagent`, not `Agent`. Not run.
3. **Hiding `subagent` with `exposure: "hidden"` does not work.** `hidden` means "registered but
   unreachable" (`docs/extensions.md`, Tool exposure). `executeTool` could not call it. The notes
   file proposes this; it is wrong.
4. **Hiding via `setActiveTools()` does not work.** `direct` tools are callable only while active
   (same section). Removing `subagent` from the active set makes it uncallable.
5. **Hiding via `prepareLoadout()` should work.**
   - `ToolDefinition.prepareLoadout(loadout)` may return `hiddenDeclarations: ["subagent"]`:
     "declared tools whose declarations requests leave out. They stay active and callable".
   - `Agent` defines it. `subagent` stays callable by `Agent` and absent from the model's tool list.
   - `codemode` uses this same pattern (docs state it can be reimplemented under another name).
   - Unrun: not confirmed against a tool registered by another extension.
6. **pi-code injects a system-prompt section naming `subagent`.** `subagent/index.ts`,
   `before_agent_start` handler (about L215-232): "Delegate isolated tasks with the subagent tool
   ({agent, task}). Available agents: ...". After hiding, the model reads about a tool it cannot
   see and `Agent` has no roster. Needs an nWave handler to replace or suppress it. Handler order
   between extensions is unverified.
7. **No grandchildren.** pi-code's `execute()` returns "Nested subagent runs are not allowed" when
   `PI_CODE_SUBAGENT` is set (child env). Delegation depth stays one.
8. **Param mapping** (from `params.ts`): `subagent_type` -> `agent`, `prompt` -> `task`.
   `max_turns` has no call parameter (only agent frontmatter `maxTurns`). `model` and
   `description` are unmapped.
9. **Loading.** Widening the rung 2 filter to `extensions/subagent/index.ts` loads the tool and the
   roster handler together. Filtering the handler out is not possible at file granularity.

## Verdict

The wrapper path is feasible. Hiding is by `prepareLoadout`, not by `exposure` or active set.
Remaining wrapper risk is the roster text (6) and `max_turns` (8).

## To run (needs a throwaway extension, in an isolated `PI_CODING_AGENT_DIR`)

1. `Agent` registered with `prepareLoadout` hiding `subagent`. Check `--mode json` tool list
   shows `Agent`, not `subagent`.
2. Print the system prompt (`ctx.getSystemPrompt()` or event) and confirm the pi-code roster text.
3. Log `tool_call` names seen by a handler during one `Agent` call (expect `Agent`, then `subagent`).
4. One model call (haiku) through `Agent` end to end, as in the first spike.
