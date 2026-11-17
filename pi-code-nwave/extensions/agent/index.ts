/** nWave's `Agent` tool: Claude's delegation call, backed by pi-code's hidden `subagent`. */

import { appendFileSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'

import type { ExtensionAPI } from '@earendil-works/pi-coding-agent'
import { Type } from 'typebox'

import { piAgentDir } from '../agent-dir.ts'
import { submitToolName } from '../submit-tool.ts'
import { classify, type Outcome } from './classify.ts'

const PI_CODE_INTRO = 'Delegate isolated tasks with the subagent tool ({agent, task}). Available agents:'
const AGENT_INTRO = 'Delegate isolated tasks with the Agent tool (Agent({subagent_type, prompt})). Available agents:'

// One `nwdes measure --requests` record per call, in one file per pi session (--requests has no session
// field, so a shared file would merge unrelated runs); `jq -s . <file> > requests.json` makes the array.
// continuation/rework are unknown here, so false. ponytail: edit the file by hand if a call was either.
const defaultLogDir = () => join(piAgentDir(), 'nwave-requests')

function logRequest(logDir: string, sessionId: string, role: string, start: string): void {
  try {
    const record = { role, task: null, slice: null, start, end: new Date().toISOString(), continuation: false, rework: false }
    mkdirSync(logDir, { recursive: true })
    appendFileSync(join(logDir, `${sessionId}.jsonl`), JSON.stringify(record) + '\n')
  } catch {} // the log must never fail a delegation
}

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
      const start = new Date().toISOString()
      const raw = await ctx.executeTool('subagent', { agent: subagent_type, task: prompt }, { signal })
      logRequest(logDir, ctx.sessionManager.getSessionId(), subagent_type, start)
      return toToolResult(classify(raw, submitTool))
    },
  })

  pi.on('before_agent_start', (event) => {
    const sections = event.systemPromptOptions?.sections as Record<string, unknown> | undefined
    const roster = sections?.subagents
    if (sections && typeof roster === 'string') sections.subagents = roster.replace(PI_CODE_INTRO, AGENT_INTRO)
  })
}
