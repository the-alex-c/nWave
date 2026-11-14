# ADR: how rung 3 delivers subagent delegation on pi

Status: accepted. Follows [adr-pi-installer-for-rung-2.md](../rung-2/adr-pi-installer-for-rung-2.md). Open gaps and evidence: [subagent-delegation-gaps.md](subagent-delegation-gaps.md).

## Context

pi core has no named roles, no delegation tool and no typed reply. pi-code ships a
working `subagent` tool and agent discovery (`~/.pi/agent/agents`), but rung 2 filters
the extension out (hooks only). nWave skills call `Agent(subagent_type=..., prompt=...)`
and expect a `role_envelope` reply.

## Decisions

### 1. Rung 3 ships as one delivery

One delivery: agents plugin, unfiltered pi-code `subagent`, an `Agent` wrapper over
`subagent` (via `ctx.executeTool`, `subagent` hidden from the model) and per-role
`submit_<role>` typed reply. Experimental until validated live.

Why: a bare-`subagent` first release would ship known defects (`isError:false` on
failure, prose replies, roster leak, param shape differing from Claude's) that the
wrapper removes. The maintainer prefers one delivery over a staged one; release order
is not a concern.

- Rejected: staged release (bare `subagent` first, wrapper later). Rework cost is low,
  but the interim defects need documenting and testing only to be deleted.
- Rejected: bare `subagent` as the final design. No failure detection, no typed reply,
  no cap, param shape differs from Claude's.
- Rejected: own spawn (`pi --mode json -p --no-session`). Not needed unless the wrapper
  hits a wall.

### 2. Installer components are independent of rungs

A rung is a capability level for gap analysis, not an install level. The role registry
is plain file install, so it is its own plugin. It is not rung 1 work: the files do
nothing without a delegation tool, and their content depends on rung 3 choices
(`tools:`, skill inlining). Gate it on the delegation extension being installed, not on
a rung.

- Rejected: user-switchable components (`--components`). Nothing needs it yet.

### 3. The registry is every role in `nWave/agents/`

Generate `~/.pi/agent/agents/nw-*.md`, manifest-owned, removed on uninstall. Model on
`codex_agents_plugin.py`, sharing its helpers.

- Why all: nWave skills call roles by name. A missing role returns "Agent failed" with
  `isError:false`, which looks like success. A hand-picked subset also needs a rule.
- Rejected: only the 8 roles with envelope schemas. Roles without a schema still need
  to exist for delegation by name.

### 4. A role that fails validation fails the whole install

Validate every role before writing anything: frontmatter parses, `tools:` resolve to pi
built-ins or `submit_<role>`, `skills:` exist, pi-code lists the agent, prompt size
reported. List all failures. Leave the target untouched. The same check runs as a test
over every role.

- Why: the maintainer wants to fix it, and a half-installed registry is worse.
- Cost: one bad role blocks every pi user. Accepted. Revisit if this goes upstream.
- Rejected: skip with a warning.

### 5. Role file mapping

Drop `SendMessage` (no pi equivalent). Drop the Claude-only `model` (role inherits the
session model). Keep `maxTurns`. Apply `PI_PATH_REWRITES` and skill-invocation
translation. Inline `skills:` (pi-code does not inject skills into a child; confirm
before building). Add `submit_<role>` plus a built-in to `tools:`. The plugin must be
idempotent.

### 6. Wrapper and typed reply

- Wrapper `Agent`; hide `subagent` via `prepareLoadout` `hiddenDeclarations`; remove the
  roster with `delete event.systemPromptOptions.sections.subagents`.
- Typed reply: per-role `submit_<role>` tools from `role_envelope_schemas.json`,
  registered only when `PI_CODE_SUBAGENT` is set. No valid submit after one nudge is a
  typed failure. No prose parsing.
- No `agent_type` on child payloads: accepted as Codex parity.
- No stall detection (installer's concern). Wall-clock cap optional, unmeasured.

Evidence: [agent-wrapper-mechanics.md](agent-wrapper-mechanics.md), gaps 2-5.

## Accepted risks

- The rung 2 guard's treatment of a `subagent` call is unverified; one live run settles
  it.
- The wrapper mechanics (`ctx.executeTool`, `hiddenDeclarations`) are documented but not
  yet exercised; spike them first.
- pi-code also scans `~/.claude/agents`; `nw-*` names may clash (project `.pi` wins).
- Skill inlining may produce large prompts; sizes are reported, not capped.
