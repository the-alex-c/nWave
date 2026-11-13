# ADR: how rung 3 delivers subagent delegation on pi

Status: accepted. Follows [adr-pi-installer-for-rung-2.md](../rung-2/adr-pi-installer-for-rung-2.md). Open gaps and evidence: [subagent-delegation-gaps.md](subagent-delegation-gaps.md).

## Context

pi core has no named roles, no delegation tool and no typed reply. pi-code ships a
working `subagent` tool and agent discovery (`~/.pi/agent/agents`), but rung 2 filters
the extension out (hooks only). nWave skills call `Agent(subagent_type=..., prompt=...)`
and expect a `role_envelope` reply.

## Decisions

### 1. Rung 3 ships in two parts, each a merge point

- **Part A:** agents plugin + unfiltered pi-code `subagent`. Delegation works on bare
  `subagent(agent, task)`. Experimental. No `Agent` name, no typed reply, no failure
  detection (`isError:false` on failure), roster leak stays.
- **Part B:** `Agent` wrapper over `subagent` (via `ctx.executeTool`, `subagent` hidden
  from the model) and per-role `submit_<role>` typed reply.

Why: Part A needs nothing Part B throws away (the role files and the widened filter are
both required later) and gives users delegation sooner.

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
- Rejected: only the 8 roles with envelope schemas. Schemas matter for `submit_<role>`
  (Part B), not for Part A.

### 4. A role that fails validation fails the whole install

Validate every role before writing anything: frontmatter parses, `tools:` resolve to pi
built-ins, `skills:` exist, pi-code lists the agent, prompt size reported. List all
failures. Leave the target untouched. The same check runs as a test over every role.

- Why: the maintainer wants to fix it, and a half-installed registry is worse.
- Cost: one bad role blocks every pi user. Revisit if this goes upstream.
- Rejected: skip with a warning.

### 5. Role file mapping

Drop `SendMessage` (no pi equivalent). Drop the Claude-only `model` (role inherits the
session model). Keep `maxTurns`. Apply `PI_PATH_REWRITES` and skill-invocation
translation. Inline `skills:` (pi-code does not inject skills into a child; confirm
before building). Part B adds `submit_<role>` plus a built-in to `tools:`; the plugin
must be idempotent.

### 6. Part B design (decided earlier, recorded here)

- Wrapper `Agent`; hide `subagent` via `prepareLoadout` `hiddenDeclarations`; remove the
  roster with `delete event.systemPromptOptions.sections.subagents`.
- Typed reply: per-role `submit_<role>` tools from `role_envelope_schemas.json`,
  registered only when `PI_CODE_SUBAGENT` is set. No valid submit after one nudge is a
  typed failure. No prose parsing.
- No `agent_type` on child payloads: accepted as Codex parity.
- No stall detection (installer's concern). Wall-clock cap optional, unmeasured.

Evidence for 6: [agent-wrapper-mechanics.md](agent-wrapper-mechanics.md), gaps 2-5.

## Accepted risks

- Part A: the rung 2 guard's treatment of a `subagent` call is unverified; one live run
  settles it.
- Part A: roles return prose; anything expecting `role_envelope` fails until Part B.
- pi-code also scans `~/.claude/agents`; `nw-*` names may clash (project `.pi` wins).
- Skill inlining may produce large prompts; sizes are reported, not capped.
