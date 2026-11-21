Blocked — reporting the missing capability instead of substituting.

Context

The acceptance-designer role (nw-acceptance-designer) cannot run in this host. Four dispatch
attempts all failed identically before any work happened: the harness envelope rejects the
role's response with no valid submit_nw_acceptance_designer call.

What I verified (falsifier confirmed)

- The role definition /home/llm/.pi/agent/agents/nw-acceptance-designer.md declares the tool:
  tools: read, write, edit, bash, submit_nw_acceptance_designer — so the required submit tool
  exists in the spec.
- The generated bundle /home/llm/.cache/nwdes/tui-observe/acceptance-bundle.txt never names
  the submit mechanism, so the agent has no in-bundle instruction to call it.
- The sibling role nw-solution-architect has the same pattern (submit_nw_solution_architect)
  and succeeded after retries — the difference is not the definition, but that this agent
  isn't actually invoking the submit tool before ending.

Owning authority

Per the nwdes rule, only your explicit authorization permits the host's default agent to run
the exact generated role prompt and verb contract in the role's place, reporting the
substitution. Otherwise this stays blocked on the harness/role integration defect.

Options

1. Authorize substitution — I run the exact generated bundle myself (host default agent),
   recording through the same nwdes acceptance verb contract; reported as a substitution, per
   the rule. Risk: weaker role isolation.
2. Retry once more — the architect succeeded on attempt 3; attempt 5 might land. Cost:
   another failed round-trip if the failure is deterministic.
3. Fix the integration first — check whether the envelope requires the submit call as the
   first or only tool call (it may be wrapping the whole turn); likely a pi harness issue,
   not a role issue.

Question

Do you authorize option 1 (host substitution, exact bundle, same verb contract, reported as a
substitution), or should I retry/repair the role dispatch first?
