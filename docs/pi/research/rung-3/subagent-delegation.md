# Rung 3 research: delegation (`spawn_agent`) on pi

Status: research, no code. Question: can pi run nWave roles (`nw-<role>`) as isolated delegated
agents with a tool ceiling and a typed reply, and what does rung 2's pi-code already give us?

## Sources read

- `docs/pi/pi-vs-codex-gaps.md` (rows: role registry, delegation, typed reply, tool ceiling, model per role)
- `docs/pi/TODO.md` (rung 3 items)
- `scripts/shared/pi_code_package.py` (rung 2 install and filter)
- pi-code 1.7.0, installed at `~/.pi/agent/npm/node_modules/pi-code`:
  - `extensions/subagent/params.ts`, `agents.ts`, `child.ts`, `run.ts`, `background.ts`, `index.ts`
- pi's own example `examples/extensions/subagent` (per TODO; not re-read here)

Nothing was executed. Findings are source-read only.

## Current state

- Rung 2 installs pi-code pinned to `1.7.0` with `FILTER = ["extensions/hooks/index.ts"]`.
  The subagent extension ships in the same package but is filtered out. Rung 2 chose hooks-only on purpose.
- `pi-vs-codex-gaps.md` marks delegation and the role registry as "Hard gap / none native".
  That is true for pi core. It is not true for pi-code, which ships a working implementation.

## What pi-code already provides

| Need (from Codex row) | pi-code 1.7.0 | Evidence |
|---|---|---|
| Named role registry | Agents loaded from `~/.pi/agent/agents`, `~/.claude/agents`, project `.pi/agents` and `.claude/agents` (recursive). Name clashes: project `.pi` wins. | `agents.ts` L377-425 |
| Delegation tool | Tool `subagent` with single (`agent`, `task`), parallel (`tasks`), chain (`{previous}`), and background modes | `params.ts`, `index.ts` L235 |
| Spawn isolated run | Spawns `pi --mode json -p --no-session`; parses JSONL event stream; returns final assistant text | `child.ts` L154, `run.ts` |
| Tool ceiling | Agent `tools:` becomes `--tools` allowlist; `disallowedTools` becomes `--exclude-tools`; MCP patterns expanded | `child.ts` L171-172 |
| Per-role model | Agent `model` passed as `--model`; Claude tier aliases (`opus`, `sonnet`, ...) resolved against available models, else session model | `agents.ts` L64-88, `child.ts` L166 |
| Effort | Agent `effort` appended to `--model` or passed as `--thinking` | `child.ts` L166-167 |
| Isolation | `isolation: worktree` supported; other values warned and ignored | `agents.ts` L245 |
| Hooks in child | `PI_CODE_AGENT_HOOKS` env passed to child; SubagentStart hook seam | `child.ts` L189, `run.ts` L219 |

## Gaps against nWave

1. **Typed reply.** Not enforced. `child.ts` L25 asks the model to respond "with ONLY a JSON object"
   (used by a hook-decision child). No output schema parameter exists in `params.ts`. Codex
   `--output-schema` has no pi-code equivalent. Options: post-hoc validation of the final text
   with a retry, or a tool the child must call to submit the envelope. Unverified which fits.
2. **Name shape.** nWave's skill `nw-role-invocation` calls `Agent(subagent_type="nw-<role>", prompt=...)`
   (or Codex `spawn_agent`). pi-code exposes `subagent(agent=..., task=...)`. Needs an alias
   or a prompt-level mapping.
3. **Skill inlining.** Codex inlines skills into `developer_instructions`. Not checked whether
   pi-code injects skills into a child. Treat as open.
4. **Output envelope.** `run.ts` returns final assistant text. Structured parsing is not present.
5. **Session format for `nwdes measure`.** Children run with `--no-session`. The TODO says to use
   `--requests` until a session format exists. Still open.

## Ceiling enforcement: what is actually enforced

- `--tools` is an allowlist passed to pi. This is host-enforced, stronger than Codex's
  prompt-only grant lines. Confirm in a real run (open).
- Model inheritance: an agent without `model` runs on the session model. Confirmed by source.

## Options

- **A. Reuse pi-code subagent.** Widen the rung 2 filter to include `extensions/subagent/index.ts`
  (and its imports). Add an nWave layer for the typed reply and the `nw-*` name shape.
  Cost: third-party dependency already pinned; larger footprint; ADR for rung 2 must be revised.
- **B. Thin nWave extension calling pi's spawn path.** Own code, smaller surface, no pi-code
  dependency for delegation. Cost: re-implements tool allowlist, JSONL parsing, and model
  resolution that pi-code already has and tests.
- **C. Hybrid.** Spike on A to learn the real behaviour (typed reply, ceiling, names). Decide
  A or B from the spike result.

Recommendation: C. The spike resolves the three open questions (typed reply, ceiling, names)
at lowest cost.

## Spike plan (red test first)

1. One role (`nw-<small role>`) in `~/.pi/agent/agents/`, with `tools:` set.
2. Invoke via pi-code `subagent` with the filter temporarily widened (local only, not installed).
3. Assert: child received only the allowed tools; output parses as a `role_envelope`;
   failing envelope is detected.
4. Record the result in this doc. Then pick A or B.

## Open questions (need a decision or a test)

- Does a prompt-only JSON reply plus a validator meet the typed-reply requirement, or does nWave need
  a submit tool the child must call?
- Is widening the pi-code filter acceptable under the rung 2 ADR, or does it need a new ADR?
- Should nWave use the `nw-*` name directly in agent files, or map `subagent_type` at the tool edge?
