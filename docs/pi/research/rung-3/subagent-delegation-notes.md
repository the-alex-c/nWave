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

Status: feasible, unrun. Source-read on pi 1.4.0 (the Cellar `0.85.1` path holds 1.4.0): see [agent-wrapper-mechanics.md](agent-wrapper-mechanics.md).

Mechanism (pi extension API, per docs under Cellar 0.85.1):
- Register `Agent` with `exposure: "direct"`.
- `execute` calls `ctx.executeTool("subagent", { agent: subagent_type, task: prompt }, { signal, onUpdate })`.
- Nested calls pass through `tool_call` and `tool_result` handlers like model calls.

Required:
- Widen the rung 2 filter to load `extensions/subagent/index.ts`.
- Hide pi-code's `subagent` from the model, so only `Agent` is declared. Use `prepareLoadout()` on `Agent` returning `hiddenDeclarations: ["subagent"]` (stays active and callable).
  - Does NOT work: `pi.setActiveTools()` excluding `subagent` (`direct` tools are callable only while active).
  - Does NOT work: re-registering `subagent` with `exposure: "hidden"` (`hidden` is unreachable, so `executeTool` fails).
- pi-code's `before_agent_start` handler injects a system-prompt section naming `subagent`; replace or suppress it.

Param mapping:
- `subagent_type` -> `agent`; `prompt` -> `task`.
- `max_turns`: no call param in pi-code. Only agent frontmatter `maxTurns`.
- `description`, `model`: map or drop.

Risks:
- The nWave `pre-task` hook matches `Agent` (`registration.py` L40). Nested `subagent` calls reach `tool_call` handlers too; confirm which name the guard sees.
- Version check resolved: the Cellar `0.85.1` path contains pi 1.4.0, so the docs read match.

## Hook visibility (gap 3), source-read

Nothing executed. Sources: pi-code 1.7.0 `hooks/index.ts`, `internal/claude-tool-names.ts`; nWave `nwave_ai/hooks/{__main__,registration,lifecycle,host_scan}.py`; live `settings.json`.

Findings:
- **The pi installer registers `Bash|Write|Edit` only.** `Agent` is not matched, so the `pre-task` hook never fires on pi. Matches the Codex floor (bash guard only).
- **`pre-task` only logs.** `handle_pre_tool_use` writes `subagent_type` to the hook log and exits 0. No block, no mutation. Missing it costs a log line, nothing else.
- **pi-code reports its `subagent` tool as `tool_name: "Agent"`** (`claude-tool-names.ts`), but `tool_input` stays pi-shaped (`{agent, task}`), so `subagent_type` is absent. An nWave-owned `Agent` tool would carry `subagent_type` (input passes through unchanged).
- **Wrapper path:** if `Agent` wraps `subagent` via `executeTool`, two PreToolUse events named `Agent` are likely (outer and nested). Unverified; only matters if a matcher is added.
- **Children run the guard.** The child is a full `pi` with `PI_CODE_SUBAGENT=1`, which skips only Stop, Session* and UserPromptSubmit. `Bash|Write|Edit` hooks fire in the child (rung 2 analysis, not yet run against a child).
- **Real gap: no child identity on tool payloads.** `commonPayload` has no `agent_type` or `agent_id`. `agent_type` appears only on SubagentStart/Stop, and only if hooks are registered for them.
  - `resolve_subagent_agent_type` needs `agent_type` or a subagent transcript sidecar. Children run `--no-session`, so neither exists.
  - Effect: `_is_nwave_subagent` is false in children. The host-scan lockdown (`find`/`bfs`) and the lane guard (`lane_guard.py:53`) silently do not apply to pi children.
  - Codex floor likely has the same limit (not checked).
- `PI_CODE_AGENT_HOOKS` (env, carries agent name) is set only when the agent file has frontmatter hooks.

Decision input: if pi must enforce host-scan/lane guard in children, the spawn must put the role in the child env (e.g. `NWAVE_AGENT_TYPE`) and `nwave_ai` must read it. pi-code's spawn does not. Own spawn (option b) can; wrapper cannot without frontmatter hooks.

### Decision: child identity gap accepted (Codex parity)

Status: decided (user).

- Pi children get no `agent_type` on tool payloads, so host-scan lockdown and the lane guard do not apply to them.
- Accepted as Codex parity: Codex registers one `PreToolUse` hook on shell only (`pi-vs-codex-gaps.md`), and the Codex plugin code has no `agent_type`, host-scan or lane-guard handling (grep, not confirmed against a live Codex run).
- No `NWAVE_AGENT_TYPE` env plumbing and no `nwave_ai` change for rung 3.
- Consequence: the wrapper path (alias over pi-code `subagent`) is not ruled out by hook visibility.
- Revisit if: Codex is shown to carry `agent_type`, or nWave wants enforcement beyond Codex.
