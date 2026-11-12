# Rung 3 delegation: naming decision

Status: decided (user), not yet implemented.

## Decision

The pi delegation tool is named **`Agent`**, with the Claude parameter shape.

- Compatible with Claude: `Agent(subagent_type="nw-<role>", prompt=..., description=..., model=..., max_turns=...)`.
- Easier for weaker models: same name and params as the Claude prompts they already see. No per-host prompt rewrite.
- One delegation tool only. No `spawn_agent`, no `subagent` alongside it.

## Evidence

- `nWave/skills/nw-role-invocation/SKILL.md` L21: Claude form `Agent(subagent_type=...)`.
- `nwave_ai/hooks/registration.py` L40: PreToolUse matcher `Agent` -> `pre-task`.
- `nwave_ai/hooks/__main__.py` L67: `_PRE_TOOL_ACTIONS` keys on `Agent`. The hook logs `subagent_type` from `tool_input` (L345).
- `nWave/templates/COMMAND_TEMPLATE.md` L150: `Task(subagent_type=...)`. Older name; `Agent` is the current one in the hook registry.

## Conflict with pi-code

pi-code 1.7.0 registers `subagent` (params `agent`, `task`), not `Agent`. Rung 2 filters it out, so it is not loaded today.

Consequences:
- Using pi-code's tool means renaming its params and tool name. Its name is fixed in the package, so this needs a wrapper.
- Wrapping pi-code's tool means two tools if pi-code's `subagent` stays loaded. Must be filtered out.
- Writing our own `Agent` tool avoids the wrapper but re-implements spawn, tool allowlist and JSONL parsing.

## Open points

1. **Implementation path.** Options:
   - (a) nWave extension registers `Agent`, reuses pi-code's `subagent/` internals by import. Fragile across pi-code versions.
   - (b) nWave extension registers `Agent`, spawns `pi --mode json -p --no-session` itself. Own code, no pi-code dependency for delegation.
   Pick (a) or (b) before the spike.
2. **Param mapping.** `subagent_type` is the only name the hook and prompts use. `prompt` replaces `task`. `description` is accepted and ignored unless the host renders it.
3. **Tool ceiling.** The `Agent` extension must read the role's `tools:` and pass them as the child's allowlist (same as pi-code's `--tools`).
4. **Hook input.** pi's `tool_call` event must expose `subagent_type` to `nwave_ai` hooks. Unverified.

## Spike impact

Spike config options from the previous message still stand. The tool under test is `Agent`, not pi-code's `subagent`. Under option 1 (isolated dir) the spike must load the nWave `Agent` extension, so the spike needs an implemented `Agent` tool first.

## Alias option: `Agent` wraps pi-code `subagent`

Status: feasible on paper, unverified on pi 1.4.0.

Mechanism (pi extension API, per docs under Cellar 0.85.1):
- Register `Agent` with `exposure: "direct"`.
- `execute` calls `ctx.executeTool("subagent", { agent: subagent_type, task: prompt }, { signal, onUpdate })`.
- Nested calls pass through `tool_call` and `tool_result` handlers like model calls.

Required:
- Widen the rung 2 filter to load `extensions/subagent/index.ts`.
- Hide pi-code's `subagent` from the model, so only `Agent` is declared. Options:
  - `pi.setActiveTools()` excluding `subagent`.
  - Re-register `subagent` with `exposure: "hidden"`. Unverified: name owned by another extension may throw.

Param mapping:
- `subagent_type` -> `agent`; `prompt` -> `task`.
- `max_turns`: no call param in pi-code. Only agent frontmatter `maxTurns`.
- `description`, `model`: map or drop.

Risks:
- The nWave `pre-task` hook matches `Agent` (`registration.py` L40). Nested `subagent` calls reach `tool_call` handlers too; confirm which name the guard sees.
- Docs read are for Cellar `0.85.1`. Global `pi --version` is `1.4.0`. Verify the API on 1.4.0 before code.
