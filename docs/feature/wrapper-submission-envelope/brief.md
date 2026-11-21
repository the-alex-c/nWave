# Product brief: wrapper\-submission\-envelope

## Request

```text
Harden the pi wrapper's role-dispatch envelope: append a host-scoped submit-tool reminder to every nw- role child prompt (dispatch-defect fix, relocated from the bundle per the record), record the observed child model in the per-session requests log, and pin the Python/TypeScript submit-tool name derivations against silent drift. Boundaries: pi-code itself is never touched; the wrapper is nWave-owned (pi-code-nwave). Evidence: docs/reference/dispatch-model-facts-record.md
```

## Work

S

```text
Role dispatches on pi end with an accepted submit call by construction, and every dispatch records the model that actually ran; a future submit-name drift fails a test instead of a role after minutes of work
```

### Rework

None.

## Promises

### P1

Outcome

```text
Role dispatches on pi end with an accepted submit call by construction, and every dispatch records the model that actually ran; a future submit-name drift fails a test instead of a role after minutes of work
```

### P2

Scenario

```text
Child prompt carries the submit reminder
```

```text
A pi session dispatches any nw- role child
```

```text
the wrapper builds the child prompt
```

```text
the prompt ends with one host-scoped line naming the role's submit tool (submit_<role>), so a long real-work child is reminded to terminate with the accepted submit call
```

### P3

Scenario

```text
Dispatch logs the observed model
```

```text
A pi session dispatches an nw- role child that runs
```

```text
the wrapper logs the role start/end
```

```text
the per-session requests log (~/.pi/agent/nwave-requests/<sessionId>.jsonl) gains a field recording the child model that actually ran
```

### P4

Scenario

```text
Submit-name drift fails a test
```

```text
The Python and TypeScript submit-tool name derivations exist in the wrapper
```

```text
one derivation is changed while the other is not
```

```text
a test fails naming the divergence, instead of a role dispatch failing after minutes of work
```

## Scope

```text
Append a host-scoped submit-tool reminder line to every nw- role child prompt in the pi wrapper (pi-code-nwave/extensions/agent/index.ts), using the same submitToolName(role) derivation the envelope check uses
```

```text
Record the observed child model in the per-session requests log (logRequest) in the agreed provider/model pair shape
```

```text
Pin the Python and TypeScript submit-tool name derivations with a drift-detecting test
```

```text
Nothing excluded because the slice is the whole feature
```

```text
pi-code itself is never touched (owner boundary; wrapper is nWave-owned pi-code-nwave)
```

```text
Bundle-based reminders (nwdes prompt appending to role bundles) are out of scope: bundles are host-agnostic and the submit envelope is pi-only, so the fix was relocated to the pi wrapper
```

```text
nwave-ai model provider expansion (deferred slice) is not part of this feature; it stays deferred per the ADR
```

## Decisions

```text
Fix lives in the pi wrapper (agent/index.ts), not the nwdes bundle: bundles are host-agnostic by contract, the submit_<role> envelope is pi-only; the wrapper already computes submitToolName(role) so the reminder shares that single derivation
```

#### Status

Confirmed


```text
The model recorded in the requests log is the observed child model from pi child results (model field), recorded as evidence; nwdes never executes models and selection is never derived from a competence label
```

#### Status

Confirmed


```text
Pair-format design row (provider/model shape shared with the deferred nwave-ai model slice) is still an open item to record as durable authority
```

#### Status

Open

Product

## Journey

```text
A host session dispatches a long real-work nw- role child; the child is reminded in its prompt to end with the accepted submit call, so the lane unblocks instead of failing after minutes of work
```

```text
Relief: the failure mode that wasted minutes per dispatch is gone
```

```text
The owner inspects the per-session requests log and sees which model actually ran for each role dispatch, without guessing
```

```text
Confidence: model facts are evidence, not intent
```

## Slices

### S1

```text
A dispatched nw- role child's prompt ends with one host-scoped line naming its submit tool; the child ends with an accepted submit call instead of prose
```

#### Promises

P1

P2

#### Depends on

None.

#### Slice work

S

```text
Dispatches stop failing with 'no valid submit call' on long real-work turns
```

##### Rework

None.

### S2

```text
A dispatch adds a model field to ~/.pi/agent/nwave-requests/<sessionId>.jsonl recording the child model that actually ran
```

#### Promises

P3

#### Depends on

S1

#### Slice work

S

```text
Model facts are recorded evidence per dispatch
```

##### Rework

None.

### S3

```text
Changing one submit-name derivation without the other makes a test fail naming the Python/TypeScript divergence
```

#### Promises

P4

#### Depends on

S1

#### Slice work

S

```text
Future submit-name drift is caught by a test, not by a role after minutes of work
```

##### Rework

None.
