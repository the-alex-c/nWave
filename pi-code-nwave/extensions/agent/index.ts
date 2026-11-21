/** nWave's `Agent` tool: Claude's delegation call, backed by pi-code's hidden `subagent`. */

import { appendFileSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'

import type { ExtensionAPI } from '@earendil-works/pi-coding-agent'
import { Type } from 'typebox'

import { piAgentDir } from '../agent-dir.ts'
import { submitToolName } from '../submit-tool.ts'
import { classify, type Child, type Outcome } from './classify.ts'

const PI_CODE_INTRO = 'Delegate isolated tasks with the subagent tool ({agent, task}). Available agents:'
const AGENT_INTRO = 'Delegate isolated tasks with the Agent tool (Agent({subagent_type, prompt})). Available agents:'

// One `nwdes measure --requests` record per call, in one file per pi session (--requests has no session
// field, so a shared file would merge unrelated runs); `jq -s . <file> > requests.json` makes the array.
// continuation/rework are unknown here, so false. ponytail: edit the file by hand if a call was either.
const defaultLogDir = () => join(piAgentDir(), 'nwave-requests')

// pi reports the child model as a single string ('provider/model', e.g. z-ai/glm-5.3-flash);
// the shared record format is the pair {provider, model} (docs/feature/wrapper-submission-envelope D2).
const modelPair = (observed: string): { provider?: string; model: string } => {
  const slash = observed.indexOf('/')
  return slash === -1 ? { model: observed } : { provider: observed.slice(0, slash), model: observed.slice(slash + 1) }
}

function logRequest(logDir: string, sessionId: string, role: string, start: string, observedModel?: string): void {
  try {
    const record = {
      role,
      task: null,
      slice: null,
      start,
      end: new Date().toISOString(),
      continuation: false,
      rework: false,
      ...(observedModel === undefined ? {} : { model: modelPair(observedModel) }),
    }
    mkdirSync(logDir, { recursive: true })
    appendFileSync(join(logDir, `${sessionId}.jsonl`), JSON.stringify(record) + '\n')
  } catch {} // the log must never fail a delegation
}

// One trailing line per nw- role child prompt: names the role's own submit tool so a long
// real-work turn still ends with the accepted submit call. Shares submitToolName with the
// envelope check, so reminder and check cannot disagree.
const submitReminder = (submitTool: string): string =>
  `When your task is complete, end your final turn by calling ${submitTool} with your typed reply ({outcome, diagnostic}); a final reply in prose fails the dispatch.`

function toToolResult(out: Outcome) {
  if (!out.ok) return { isError: true, content: [{ type: 'text' as const, text: `Agent failed (${out.kind}): ${out.detail}` }], details: undefined }
  const details = { ...(out.envelope !== undefined && { envelope: out.envelope }), ...(out.partial && { partial: true }) }
  return { content: [{ type: 'text' as const, text: out.text }], details: Object.keys(details).length ? details : undefined }
}

export default function agentExtension(pi: ExtensionAPI, logDir: string = defaultLogDir()): void {
  pi.registerTool({
    name: 'Agent',
    label: 'Agent',
    description: 'Delegate an isolated task to a named agent.',
    parameters: Type.Object({ subagent_type: Type.String(), prompt: Type.String() }),
    prepareLoadout: () => ({ hiddenDeclarations: ['subagent'] }),
    async execute(_id, { subagent_type, prompt }, signal, _u, ctx) {
      const submitTool = subagent_type.startsWith('nw-') ? submitToolName(subagent_type) : undefined
      // Host-scoped reminder: bundles are host-agnostic, so only the pi wrapper reminds the
      // child to terminate with the accepted submit call (docs/reference/dispatch-model-facts-record.md).
      const task = submitTool === undefined ? prompt : `${prompt}\n${submitReminder(submitTool)}`
      const start = new Date().toISOString()
      const raw = await ctx.executeTool('subagent', { agent: subagent_type, task }, { signal })
      // Observed child model: pi's SingleResult carries `model?: string` (run.ts:281);
      // Child is the wrapper's structural mirror of it (ADR 6).
      const child = raw.result?.details?.results?.[0] as Child | undefined
      logRequest(logDir, ctx.sessionManager.getSessionId(), subagent_type, start, child?.model)
      return toToolResult(classify(raw, submitTool))
    },
  })

  pi.on('before_agent_start', (event) => {
    const sections = event.systemPromptOptions?.sections as Record<string, unknown> | undefined
    const roster = sections?.subagents
    if (sections && typeof roster === 'string') sections.subagents = roster.replace(PI_CODE_INTRO, AGENT_INTRO)
  })
}
