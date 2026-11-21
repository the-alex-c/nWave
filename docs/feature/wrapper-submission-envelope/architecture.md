# Architecture brief: wrapper\-submission\-envelope

## Paradigm

procedural

## Shared records

### Decisions

#### D1

```text
The reminder is appended by the pi wrapper only: agent/index.ts appends one host-scoped line naming submitToolName(subagent_type) to every nw- role child prompt; pi-code is never touched; non-nw subagent types keep the unchanged prompt
```

#### D2

```text
Resolves the product Open item: the shared pair-format design row is a JSON object {provider, model}. The wrapper derives it from pi's observed provider/model string (SingleResult.model) by splitting on the first '/', and writes model:{provider,model} into the requests log record; when pi reports no model the field is omitted. The deferred nwave-ai model slice reads the same row
```

#### D3

```text
Claim-to-checker: the change adds no state machine; envelope acceptance semantics are unchanged (classify.ts). Local claims are pure-function totality/agreement and additive record fields, checked by the repository's executable tests (vitest in pi-code-nwave, pytest in tests/pi). Quint/TLA+/Agda not selected; no state-model claim exists to model-check
```

#### D4

```text
Paradigm procedural: imperative wrapper glue; no domain objects or services are introduced
```

### Constraints

#### K1

```text
pi-code itself is never touched; the wrapper pi-code-nwave is nWave-owned and may consume pi-code's runtime output shape (SingleResult.model)
```

#### K2

```text
logRequest must never fail a delegation (existing catch-all is retained)
```

#### K3

```text
Bundle-based reminders are out of scope (bundles are host-agnostic); nwave-ai model provider expansion stays deferred per ADR
```

#### K4

```text
The recorded model is evidence from pi child results only; nwdes never executes models and selection is never derived from a competence label
```

### Reuse

submitToolName

pi\-code\-nwave\/extensions\/submit\-tool\.ts\:2

Reuse

```text
Single derivation the envelope check already uses; the reminder shares it so reminder and check cannot disagree by construction
```

submit\_tool

scripts\/shared\/pi\_role\_mapping\.py\:40

Reuse

```text
Python owner of the same derivation; the drift test consults it, not a copy
```

logRequest

pi\-code\-nwave\/extensions\/agent\/index\.ts\:21

Extend

```text
Gains the model pair field in the same record; catch-all retained
```

Child

pi\-code\-nwave\/extensions\/agent\/classify\.ts\:30

Extend

```text
Mirrors pi SingleResult; gains model?: string so the wrapper can observe the child model
```

to\_pi\_role

tests\/pi\/test\_pi\_role\_mapping\.py\:16

Extend

```text
S3 target: the drift test extends this file's submit-name coverage; to_pi_role is the existing owner the file maps, and submit_tool is consulted via scripts/shared/pi_role_mapping.py:40
```

### Impact

prompt\_contract

pi\-code\-nwave\/extensions\/agent\/index\.ts\:39

Changed

```text
nw- child prompts gain one trailing reminder line naming the role's submit tool
```

log\_record

pi\-code\-nwave\/extensions\/agent\/index\.ts\:21

Changed

```text
Requests log record gains optional model:{provider,model}
```

test

pi\-code\-nwave\/tests\/agent\.test\.ts\:1

Changed

```text
New reminder and model-field assertions
```

test

tests\/pi\/test\_pi\_role\_mapping\.py\:40

Changed

```text
New drift test
```

### Agreement

requests log record shape \(\~\/\.pi\/agent\/nwave\-requests\/\<sessionId\>\.jsonl\, one JSON object per line\: role\/task\/slice\/start\/end\/continuation\/rework\, \+ model\)

pi\-code\-nwave\/extensions\/agent\/index\.ts\:21

Producer

Migrated

```text
Additive optional model:{provider,model} field; record shape otherwise unchanged
```

requests log record shape

pi\-code\-nwave\/extensions\/agent\/index\.ts\:21

Consumer

UnchangedCompatible

```text
nwdes measure --requests reads via jq; JSONL consumers tolerate added fields
```

child prompt \-\> submit envelope \(wrapper prompt\, child reply\, classify envelope check\)

pi\-code\-nwave\/extensions\/agent\/classify\.ts\:46

Producer

Migrated

```text
Prompt gains one trailing reminder line; reply/acceptance semantics unchanged
```

child prompt \-\> submit envelope

pi\-code\-nwave\/extensions\/agent\/classify\.ts\:46

Consumer

UnchangedCompatible

```text
classify.ts is untouched; the reminder is additive text the check ignores
```

submit\_\<role\> name derivation \(\'submit\_\' \+ role with \'\-\'\-\>\'\_\'\)

pi\-code\-nwave\/extensions\/submit\-tool\.ts\:2

Producer

UnchangedCompatible

```text
Name shape unchanged; the S3 drift test pins it against the Python owner
```

submit\_\<role\> name derivation

scripts\/shared\/pi\_role\_mapping\.py\:40

Consumer

UnchangedCompatible

```text
Python derivation unchanged; the drift test now cross-checks it against the TS owner
```

### Not applicable

prefactoring

```text
No existing oracle to relocate and no target to prefactor: all three slices are small additive changes behind existing seams (agent/index.ts, existing test files) already exercised by their current oracles
```

### Boundaries

```text
pi wrapper Agent tool execute(subagent_type, prompt) in pi-code-nwave/extensions/agent/index.ts
```

#### Driven ports

```text
pi subagent tool receives the child prompt
```

```text
~/.pi/agent/nwave-requests/<sessionId>.jsonl record
```

```text
wrapper -> pi-code subagent runtime API and filesystem log; nothing depends back on the wrapper
```

#### Failures

None.

### Observations

None.

### Equality

None.

### Constructors

None.

### Laws

#### L1

```text
submit_tool(r) in Python equals submitToolName(r) in TypeScript for every role name r
```

Algebraic

Infrastructure

pi\-code\-nwave\/extensions\/submit\-tool\.ts\:2

##### Treatment

Broad

###### Generator

```text
role names matching ^[a-z][a-z0-9-]*$
```

128

fixed seed list

###### Must include

```text
nw-solution-architect
```

```text
nw-acceptance-designer
```

None.

```text
n/a for pure string map
```

```text
run both derivations on the same inputs and compare outputs
```

```text
change one derivation while the other is unchanged
```

##### Evidence

tests\/pi\/test\_pi\_role\_mapping\.py

#### L2

```text
every nw- role child prompt ends with exactly one reminder line naming submitToolName(role)
```

Invariant

Adapter

pi\-code\-nwave\/extensions\/agent\/index\.ts\:39

##### Treatment

Finite

###### Cases

```text
nw-x
```

```text
nw-solution-architect
```

```text
one line per dispatch is observable from the mocked subagent task argument
```

##### Evidence

pi\-code\-nwave\/tests\/agent\.test\.ts

#### L3

```text
logRequest never fails a delegation
```

Invariant

Infrastructure

pi\-code\-nwave\/extensions\/agent\/index\.ts\:21

##### Treatment

Finite

###### Cases

```text
unwritable log dir
```

```text
existing catch-all is retained
```

##### Evidence

pi\-code\-nwave\/tests\/agent\.test\.ts

### Refuted

None.

### Claims

#### C1

```text
every nw- role child prompt carries one host-scoped reminder line naming the role's submit tool
```

```text
a long real-work child ends in prose and the dispatch fails with 'no valid submit call' after minutes of work
```

pi\-code\-nwave\/extensions\/agent\/index\.ts\:39

```text
subagent_type starting with 'nw-'
```

submitToolName

pi child model reading the prompt

```text
the task argument passed to pi's subagent tool ends with the reminder line
```

```text
direct subagent tool dispatch and non-pi hosts (no reminder, envelope check still rejects non-submit replies)
```

### States

Admitted

```text
subagent_type starting with nw- and a role name matching ^[a-z][a-z0-9-]*$
```

pi\-code\-nwave\/extensions\/agent\/index\.ts\:39

Excluded

```text
non-nw subagent_type (no reminder line; prompt unchanged)
```

pi\-code\-nwave\/extensions\/agent\/index\.ts\:39

Unknown

```text
pi child result without a model field (model pair omitted from the log record)
```

pi\-code\-nwave\/extensions\/agent\/index\.ts\:21

### Models

None.

### Closure

```text
candidate
```

Safety

Pass

DesignedNotBuilt

```text
argued: the reminder shares the single submitToolName derivation with the envelope check (classify.ts), so reminder and check cannot disagree by construction; the S3 drift test pins the Python/TS agreement
```

##### Evidence

tests\/pi\/test\_pi\_role\_mapping\.py

```text
candidate
```

Inhabitation

Pass

DesignedNotBuilt

```text
argued: the reminder is constructed for any nw- role via submitToolName; non-nw subagent types take the unchanged path
```

##### Evidence

pi\-code\-nwave\/tests\/agent\.test\.ts

```text
candidate
```

PublicReachability

Pass

DesignedNotBuilt

```text
argued: the reminder is observed in the task argument the wrapper passes to pi's subagent tool, mocked in vitest
```

##### Evidence

pi\-code\-nwave\/tests\/agent\.test\.ts

```text
candidate
```

Liveness

Pass

DesignedNotBuilt

```text
argued: accepted-submit enforcement is the existing envelope check (classify.ts); the reminder raises child compliance but no temporal guarantee is claimed
```

##### Evidence

pi\-code\-nwave\/tests\/agent\.test\.ts

### Risks

#### Y1

Stressor

```text
pi changes or drops SingleResult.model
```

```text
log stays additive; model pair omitted when absent
```

```text
log records without model
```

```text
a delegation failing because of logging
```

```text
model facts missing until the pi contract is rechecked
```

pi\-code\-nwave\/extensions\/agent\/index\.ts maintainer

#### Y2

Bypass

```text
dispatch that bypasses the wrapper (direct subagent tool, non-pi hosts)
```

```text
envelope check still rejects non-submit replies
```

```text
no reminder on those paths
```

```text
silent acceptance of a prose reply
```

```text
reminder absent by design outside pi dispatches
```

pi\-code\-nwave\/extensions\/agent\/index\.ts maintainer

#### Y3

SinglePointOfFailure

```text
submitToolName is the single derivation
```

```text
one derivation shared by reminder and envelope check
```

```text
changing both TS and Python with the drift test green
```

```text
one-sided derivation change
```

```text
none; S3 drift test pins the pair
```

tests\/pi\/test\_pi\_role\_mapping\.py drift test

### Architectural tests

#### T1

```text
The reminder is appended only in pi-code-nwave/extensions/agent/index.ts and uses submitToolName(subagent_type), never a re-derived or literal name; reminder and envelope check share one derivation
```

pi\-code\-nwave\/tests\/agent\.test\.ts

```text
bash -c 'cd pi-code-nwave && ./node_modules/.bin/vitest run tests/agent.test.ts'
```

### Contract tests

#### T2

```text
The requests log record gains model in the agreed pair shape when the child result carries a model
```

requests log record shape \(\~\/\.pi\/agent\/nwave\-requests\/\<sessionId\>\.jsonl\, one JSON object per line\, \+ model\)

pi\-code\-nwave\/extensions\/agent\/index\.ts\:21 logRequest

nwdes measure \-\-requests \(jq reader\)

```text
the per-session jsonl record contains model:{provider,model} derived from the observed provider/model string
```

pi\-code\-nwave\/tests\/agent\.test\.ts

```text
bash -c 'cd pi-code-nwave && ./node_modules/.bin/vitest run tests/agent.test.ts'
```

#### T3

```text
One-sided change of the TS or Python submit-name derivation makes a test fail naming the divergence
```

submit\_\<role\> name derivation \(\'submit\_\' \+ role with \'\-\'\-\>\'\_\'\)

pi\-code\-nwave\/extensions\/submit\-tool\.ts\:2 submitToolName

scripts\/shared\/pi\_role\_mapping\.py\:40 submit\_tool

```text
both derivations produce identical names for representative role names
```

tests\/pi\/test\_pi\_role\_mapping\.py

```text
bash -c '.venv/bin/pytest tests/pi/test_pi_role_mapping.py -k drift'
```

## Slices

### S1

#### Targets

pi\-code\-nwave\/extensions\/agent\/index\.ts

Extend

```text
Append one host-scoped reminder line naming submitToolName(subagent_type) to every nw- role child prompt
```

pi\-code\-nwave\/tests\/agent\.test\.ts

#### Verification

```text
bash -c 'cd pi-code-nwave && ./node_modules/.bin/vitest run tests/agent.test.ts'
```

#### Supports

pi\-code\-nwave\/extensions\/submit\-tool\.ts

#### Public oracle

```text
dispatch the Agent tool with subagent_type nw-x and a task
```

```text
the task argument passed to pi's subagent tool ends with one line naming submit_nw_x
```

```text
a dispatch whose prompt lacks the reminder line (or names a different tool)
```

##### Promises

P1

P2

#### Prefactoring

None.

#### Records

None.

### S2

#### Targets

pi\-code\-nwave\/extensions\/agent\/index\.ts

Extend

```text
logRequest gains model:{provider,model} derived from the observed child result model; Child interface gains model?: string
```

pi\-code\-nwave\/tests\/agent\.test\.ts

#### Verification

```text
bash -c 'cd pi-code-nwave && ./node_modules/.bin/vitest run tests/agent.test.ts'
```

#### Supports

pi\-code\-nwave\/extensions\/agent\/classify\.ts

#### Public oracle

```text
dispatch an nw- role child whose result carries model z-ai/glm-5.3-flash
```

```text
the per-session jsonl record gains model:{provider:z-ai,model:glm-5.3-flash}
```

```text
a record without the model pair, or a pair not derived from the observed string
```

##### Promises

P3

#### Prefactoring

None.

#### Records

None.

### S3

#### Targets

tests\/pi\/test\_pi\_role\_mapping\.py

Extend

```text
Add the drift test cross-checking the TS submitToolName derivation against the Python submit_tool owner
```

tests\/pi\/test\_pi\_role\_mapping\.py

#### Verification

```text
bash -c '.venv/bin/pytest tests/pi/test_pi_role_mapping.py -k drift'
```

#### Supports

pi\-code\-nwave\/extensions\/submit\-tool\.ts

scripts\/shared\/pi\_role\_mapping\.py

#### Public oracle

```text
change one derivation (TS or Python) while the other keeps its shape
```

```text
pytest fails naming the Python/TypeScript divergence
```

```text
both derivations agree on representative role names -> the test passes
```

##### Promises

P4

#### Prefactoring

None.

#### Records

None.

## ADRs

None.
