# ADR: defer the nwave-ai model provider expansion (Slice 1)

Status: accepted. Evidence and context: [dispatch-model-facts-record.md](dispatch-model-facts-record.md).

## Context

The goal: run role dispatches on different models from different providers, with
the observed model name recorded. Slice 1 proposed widening `nwave-ai model set`
beyond `codex|claude` providers. Investigation of the installed code showed what
the widened authority would actually be:

- `model_runtime` in `~/.nwave/config.json` / `.nwave/config.json` is a
  **write-only store**: the resolver chain (`NWaveConfig.role_runtime()` →
  `resolve_role_runtime()` → `_runtime()` → `ModelProvider` enum,
  `nwave_ai/platform/roles.py:22,82`) has **zero live callers**. No top-level
  process — `nwdes`, nWave hooks, doctor, pi, the codex/claude CLIs — reads it.
- The only live enforcement is the CLI's write-time literal set
  (`cli.py:1251`); the enum guard sits in a resolver corridor nobody walks.
- The goal pi-side is already served natively: agent specs accept
  `model`/`modelAlias`, resolved per child (`pi-code/extensions/subagent/run.ts:281`).

## Decision

**Defer Slice 1** (provider expansion in `nwave-ai model`). Proceed with
Slice 2 (pi wrapper capture of the observed child model) and use pi-native
per-role `model`/`modelAlias` declarations where a role needs a different
model now.

Why: a widened allowlist on a store no process consumes is a diary entry, not a
feature. Slice 1 earns its cost only when its store gains a first live consumer
— which becomes real when a non-pi host (codex/claude native) actually dispatches
nWave roles. That trigger has not occurred; deferring removes the cost without
losing the goal, because pi consumes its own declarations on every dispatch.

- Rejected: Slice 1 as originally framed (widen provider allowlist + read
  surface, no consumer). Delivers dead authority; guard widened where no path
  walks.
- Rejected: Slice 1 with a read surface as its first consumer. Makes the store
  readable but still decides nothing; dispatch through non-pi hosts — the only
  thing that consumes the decision — does not exist yet.
- Rejected: doing Slice 1 and Slice 2 in parallel. The wrapper lane would wait
  on Slice 1's pair-format design row anyway; parallelism buys nothing while
  Slice 1 has no consumer.

## Conditions for revisiting

Slice 1 is taken off the shelf when any of these becomes true:

1. A nWave dispatch actually runs through a codex/claude native host (the
   resolver chain's intended consumer), or a second host joins pi, and
   per-role model selection must be one authority across hosts.
2. Recorded-but-unused declarations start causing real drift between what is
   declared and what runs, and a single source of truth is needed to stop it.

On revisit, the design constraints carry over unchanged (from the record):

- `ModelProvider` (roles.py:22) is the SSOT of the guard; the CLI's literal set
  and the read-time enum must move together — widening only the CLI writes
  values that refuse on every read.
- The `{"provider", "model"}` pair shape stays atomic (no per-field merge
  across tiers).
- The existing refusal properties carry over: role resolution before write, no
  availability check, no fallback, no competence→model mapping.

## Immediate consequences

- Slice order: **Slice 2 (pi wrapper capture) is next**; the pair-format
  design row stays a shared contract so a future Slice 1 cannot drift.
- Roles needing a non-default model now: set `model`/`modelAlias` in the pi
  agent spec — pi natively consumes it; no nwave-ai change required.
- `dispatch-model-facts-record.md` open items updated accordingly.
