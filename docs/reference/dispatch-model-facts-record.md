# Dispatch Model Facts — Investigation Record

Status: diagnosis complete, design agreed in conversation, slices not yet started.
Date: 2026-11-21 (session-recorded)
Origin: [`dispatch-defect-observation.md`](./dispatch-defect-observation.md) — the original model output reporting the observed defect
in `/home/llm/molfar/lanes/tui-observe` work, kept verbatim alongside this record
for future reference.

This document records the problem as researched, the boundary conditions the
owner specified, and the options discussed. It is a reference artifact; the
delivery itself proceeds through nwdes slices, not through this file.

---

## 1. Observed defect

`nw-acceptance-designer` role dispatches failed 4 of 4 times with:

```text
Agent failed (envelope): no valid submit_nw_acceptance_designer call
```

The sibling role `nw-solution-architect` succeeded through the same path (on its
third attempt), so the failure was not obviously deterministic per mechanism.

## 2. Root-cause research (evidence, not inference)

Each hypothesis was tested against the installed code or a live probe.

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| 1 | Submit tool not registered in the child | **Falsified** | Live probe: `nw-acceptance-designer` called `submit_nw_acceptance_designer`; the envelope accepted `{"outcome":"indeterminate","diagnostic":"probe"}` on the first attempt |
| 2 | Schema validation rejects realistic reports | **Falsified** | Live probe 2: an extra field (`summary`) did not error; the reply came back clean (extra fields are stripped, not rejected) |
| 3 | Child env missing `PI_CODE_SUBAGENT=1` | **Falsified** | `pi-code/extensions/subagent/run.ts:326` sets it for every child |
| 4 | Envelope requires submit as first/only call | **Falsified** | `pi-code-nwave/extensions/agent/classify.ts` accepts any *accepted* call anywhere in the child transcript; last accepted call wins. An errored/rejected call is excluded, which correctly reads as "no valid call" |
| 5 | Child never invokes submit before ending | **Confirmed** | All 4 failed dispatches ran 2.7–11.7 min (the child did real work), then ended without an accepted submit call. Probe tasks succeed first try; long real-work tasks end in prose |

Key mechanism chain, verified in source:

- `pi-code-nwave/extensions/submit/index.ts` registers one `submit_<role>` tool
  per published agent spec, only when `PI_CODE_SUBAGENT` is set (child runs).
- `pi-code-nwave/extensions/agent/classify.ts` turns the child result into a
  typed outcome; `envelope` failure means *no accepted submit call existed*.
- Child transcripts are not persisted, so the failed children's final turns
  could not be inspected directly; the probe-vs-real-work contrast is the
  decisive evidence.

### Root cause statement

Not an integration defect. The child model (`z-ai/glm-5.3-flash`, thinking
level `low`) reliably fails to terminate a **long real-work turn** with the
required submit call — probes end correctly; real work ends in plain prose.
Aggravating factor: the generated nwdes role bundle never names the submit
mechanism, so the child has no in-bundle reminder at the turn where it fails.

### Cheap durable fix (agreed, not yet delivered)

`nwdes prompt` generation appends one line to every role bundle: "your turn
must end with a call to `submit_<role>`". This converts the failure from
probabilistic to by-construction.

## 3. Follow-on problem: model facts across providers

The dispatch-defect diagnosis surfaced a second problem: dispatches run on whatever model
the pi session uses, and nothing records — or declares — which provider/model
each role ran on. The owner wants different models from different providers to
be usable per role, with the observed model name flowing from pi to nwdes.

What already exists (verified):

- pi child results already carry `model?: string`
  (`pi-code/extensions/subagent/types.ts:28`); agent specs may set
  `model`/`modelAlias`, resolved per child (`run.ts:281`). No new pi plumbing
  is needed to *know* the model.
- nWave's pi wrapper (`pi-code-nwave/extensions/agent/index.ts`, `logRequest`)
  writes role/start/end to `~/.pi/agent/nwave-requests/<sessionId>.jsonl` but
  drops the model — one added field.
- `nwave-ai model set` (nw-rigor skill) records explicit provider/model pairs
  per scope/role — but accepts only `codex` or `claude` providers today, and it
  records *intent*, not what actually ran.
- Standing rule: nwdes never executes models, and selection is never derived
  from a competence label. "pi sends the model name to nwdes" therefore means
  *recording evidence*, not nwdes choosing.

## 4. Owner-specified boundaries

These constraints were stated by the owner and govern every option:

1. **pi-code is not to be touched** — the owner does not own that package.
   (No option in this record requires touching it.)
2. **The pi wrapper modification is approved** — `pi-code-nwave` is
   nWave-owned; consuming pi-code's runtime output shape is acceptable.
3. **The pi-platform-facing part and the `nwave-ai model` part must be kept
   separable** — the owner wants to explore each slice independently, with
   referenceable files per slice.
4. **`nwave-ai model` should be forked/extended to provide non-pi support for
   other models** — it must serve hosts beyond pi.

Dependency analysis performed for boundary 3:

- Part A (pi wrapper capture) depends on pi only at runtime, through the
  already-shipped `model` field in child results. It is not a code dependency
  on a fork.
- Part B (`nwave-ai model` provider expansion) is pure Python CLI
  (`nwave_ai/cli.py` + `nWave/skills/nw-rigor`) and has **zero pi dependency**.
- The only shared thing is a small contract: the shape of a recorded
  provider/model pair (`{"provider": ..., "model": ...}`). That is an
  agreement recordable in one design row, not a code dependency; either slice
  can land first.

## 5. Options discussed

| Option | Scope | Consequence | Risk | Verdict in conversation |
|---|---|---|---|---|
| Dispatch-defect option 1: host substitution | run the exact generated bundle from the host default agent | unblocks the blocked lane today | weaker role isolation, permanently; defect stays unfixed for future roles | rejected as the fix; remains available as an explicit authorization if a lane must move now |
| Dispatch-defect option 2: retry dispatch | retry as-is | might land (architect landed on attempt 3) | another failed round-trip if failure is model-driven (it is) | rejected as primary |
| Dispatch-defect option 3: bundle fix | `nwdes prompt` names the submit mechanism in every bundle | permanent, by-construction fix; one retry needed after | none beyond one retry | agreed (cheap durable fix, §2) |
| Model option 1: passive capture only (S) | add `model` to `logRequest()` in the pi wrapper | measurement becomes truthful today; no behavior change | none identified | approved as part of the full route |
| Model option 2: full model-facts route (M) | capture + `nwave-ai model` provider expansion + shared pair-format design row | durable authority; per-role model facts recorded and declared; host-agnostic CLI | more ceremony; ~2 slices | **approved by owner** |
| Model option 3: spine wave | full DISCUSS→DELIVER for the whole change | maximum ceremony | cost far above the change size | rejected |

Route decision: one Request, **two independent slices in two parallel lanes**
(fits the human WIP limit of 2), under the nwdes route:

- **Slice 1 — nwave-ai model facts** (no pi involvement): expand
  `nwave-ai model set` to arbitrary providers; nw-rigor skill text updated to
  match. Host-agnostic deliverable.
- **Slice 2 — pi wrapper capture**: `logRequest()` records the observed child
  `model` (and provider if derivable) in the pair shape agreed in slice 1's
  design row.

The shared pair format is recorded once as a durable design decision so the
two slices cannot drift. Slices are order-independent.

The owner further chose to **explore the two slices separately** and keep
reference files for each, before (or instead of) immediately bundling them
into one Request.

## 6. Open items

- [ ] Record the pair-format design row (durable authority).
- [ ] Deliver Slice 1 (nwave-ai model provider expansion) via nwdes.
- [ ] Deliver Slice 2 (pi wrapper `logRequest` model capture) via nwdes.
- [ ] Deliver the dispatch-defect bundle-line fix (§2) — independent of both slices.
- [ ] Retry the `nw-acceptance-designer` dispatch for `tui-observe` S1 after
      the bundle fix lands.
