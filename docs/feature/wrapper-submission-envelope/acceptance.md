# Acceptance brief: wrapper\-submission\-envelope

## Slices

### S1

##### Covers

P1

P2

```text
dispatch the Agent tool with subagent_type nw-x and a task
```

```text
the task argument passed to pi's subagent tool ends with one line naming submit_nw_x
```

```text
the child prompt pi receives ends with the submit-tool reminder, so the child is reminded to end with an accepted submit call
```

##### Disposition

Tested

pi\-code\-nwave\/tests\/agent\.test\.ts\@Tested

```text
a reminder line naming the tool but not placed as the final line, or naming it twice
```

###### Obligations


##### Covers

P2

```text
dispatch the Agent tool with subagent_type nw-solution-architect and a task
```

```text
the reminder line names the hyphenated role's submit tool submit_nw_solution_architect, the same name the envelope check derives
```

```text
any nw- role gets its own tool name in the reminder, not a generic one
```

##### Disposition

Tested

pi\-code\-nwave\/tests\/agent\.test\.ts\@Tested

```text
a literal name string that coincides with the derived name for this role
```

###### Obligations


##### Covers

P2

```text
dispatch the Agent tool with a non-nw subagent_type and a task
```

```text
the task argument passed to pi's subagent tool is unchanged, with no reminder line
```

```text
non-nw delegations keep their original prompt
```

##### Disposition

Tested

pi\-code\-nwave\/tests\/agent\.test\.ts\@Tested

```text
a reminder appended only to nw- prompts but visible to non-nw agents through the shared roster
```

###### Obligations


### S2

##### Covers

P3

```text
dispatch an nw- role child whose result carries model z-ai/glm-5.3-flash
```

```text
the per-session jsonl record gains model with provider z-ai and model glm-5.3-flash, derived by splitting the observed string on the first slash
```

```text
the owner inspects the per-session requests log and sees which model actually ran for the dispatch
```

##### Disposition

Tested

pi\-code\-nwave\/tests\/agent\.test\.ts\:requests log \> observed child model \> should record the observed child model as the pair \{provider\, model\}

```text
the wrapper logs a model pair derived from any fixed default instead of the child's observed result string
```

###### Obligations



##### Covers

P3

```text
dispatch an nw- role child whose result carries no model
```

```text
the per-session jsonl record omits the model field entirely
```

```text
the owner sees no model claim in the log when no model was observed, so the log never asserts a model that did not run
```

##### Disposition

Tested

pi\-code\-nwave\/tests\/agent\.test\.ts\:requests log \> observed child model \> should omit the model field when pi reports no child model

```text
the wrapper logs a model pair with empty or null parts when no child model is observed
```

###### Obligations


## Expectations

### Rows

#### E1

##### Promises

P1

P2

```text
When a pi session dispatches any nw- role child, the built child prompt ends with a single host-scoped line naming that role's submit tool (submit_<role>), so even a long real-work child is reminded to terminate with the accepted submit call by construction (P1, P2).
```

#### E2

##### Promises

P3

```text
After a pi session dispatches an nw- role child that runs, the wrapper logs the role start and end, and the per-session requests log (~/.pi/agent/nwave-requests/<sessionId>.jsonl) gains a field recording the child model that actually ran (P3).
```

#### E3

##### Promises

P4

```text
When the Python and TypeScript submit-tool name derivations in the wrapper disagree (one changed, the other not), a test fails and names the divergence, instead of a role dispatch failing after minutes of real work (P4).
```

## Charter

None.

## Examination

### E1

met

#### Observations

```text
vitest run tests/agent.test.ts: 35 passed. Reminder rows observed: nw-x child prompt ends with one line containing submit_nw_x (exactly one occurrence); nw-solution-architect prompt ends with submit_nw_solution_architect once; non-nw (explore) prompt passed through unchanged with no reminder line. The reminder shares submitToolName with the envelope check (pi-code-nwave/extensions/agent/index.ts appends it as the final line only for nw- prefixed subagent_type).
```

### E2

met

#### Observations

```text
Scratch vitest fixture (workspace scratch/cfg, imports the candidate's extensions/agent/index.ts with a stubbed pi host): dispatch nw-x with child result carrying model 'z-ai/glm-5.3-flash' -> the record gains model {provider:'z-ai', model:'glm-5.3-flash'}; 'a/b/c' splits on the FIRST slash into {provider:'a', model:'b/c'}; a result with no model field omits the model field; role 'nw-x' and start/end still recorded. 4/4 passed.
```

```text
vitest requests-log rows observed: one record per Agent call appended to <session>.jsonl with role, start, end (ISO start<=end), per-session file separation, and a delegation still succeeding when the log dir is unwritable (catch-all retained). These suite tests assert start/end and role but do NOT assert the model field.
```

### E3

met

#### Observations

```text
Negative stimulus executed: mutated only the TS derivation (submit-tool.ts replaceAll('-','_X')), Python owner unchanged -> pytest fails all 3 drift cases with 'TypeScript submitToolName derivation changed shape ... current TS: ...replace All..._X; Python owner: scripts/shared/pi_role_mapping.py submit_tool'. File restored byte-identical; pytest passes again.
```

```text
pytest tests/pi/test_pi_role_mapping.py -k submit (derivations agreeing): 3 parametrized cases (nw-x, nw-solution-architect, nw-software-crafter) pass - the falsifier side (agreement -> test passes) holds.
```
