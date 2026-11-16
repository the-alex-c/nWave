/** nWave's `Agent` tool: Claude's delegation call, backed by pi-code's hidden `subagent`. */

import type { ExtensionAPI } from '@earendil-works/pi-coding-agent'
import { Type } from 'typebox'

import { classify } from './classify.ts'

const PI_CODE_INTRO = 'Delegate isolated tasks with the subagent tool ({agent, task}). Available agents:'
const AGENT_INTRO = 'Delegate isolated tasks with the Agent tool (Agent({subagent_type, prompt})). Available agents:'

export default function agentExtension(pi: ExtensionAPI): void {
  pi.registerTool({
    name: 'Agent',
    label: 'Agent',
    description: 'Delegate an isolated task to a named agent.',
    parameters: Type.Object({ subagent_type: Type.String(), prompt: Type.String() }),
    prepareLoadout: () => ({ hiddenDeclarations: ['subagent'] }),
    async execute(_id, { subagent_type, prompt }, signal, _u, ctx) {
      const submitTool = subagent_type.startsWith('nw-') ? 'submit_' + subagent_type.replaceAll('-', '_') : undefined
      const out = classify(await ctx.executeTool('subagent', { agent: subagent_type, task: prompt }, { signal }), submitTool)
      if (!out.ok) return { isError: true, content: [{ type: 'text', text: `Agent failed (${out.kind}): ${out.detail}` }], details: undefined }
      const content = [{ type: 'text' as const, text: out.text }]
      const details = { ...(out.envelope !== undefined && { envelope: out.envelope }), ...(out.partial && { partial: true }) }
      return { content, details: Object.keys(details).length ? details : undefined }
    },
  })

  pi.on('before_agent_start', (event) => {
    const sections = event.systemPromptOptions?.sections as Record<string, unknown> | undefined
    const roster = sections?.subagents
    if (sections && typeof roster === 'string') sections.subagents = roster.replace(PI_CODE_INTRO, AGENT_INTRO)
  })
}
