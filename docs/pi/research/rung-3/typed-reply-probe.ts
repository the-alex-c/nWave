import { appendFileSync } from 'node:fs'
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '/Users/USER/homebrew/Cellar/pi-coding-agent/0.85.1/libexec/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/index.js'
import sub from '/Users/USER/.pi/agent/npm/node_modules/pi-code/extensions/subagent/index.ts'
const child = !!process.env.PI_CODE_SUBAGENT
const L = (s: string) => appendFileSync('/tmp/probe2/log.txt', (child ? 'C ' : 'P ') + s + '\n')
export default function (pi: any) {
  L('load'); sub(pi)
  const f = fauxProvider({ models: [{ id: 'f1' }] })
  f.setResponses(child ? [
    fauxAssistantMessage(fauxToolCall('submit_result', { status: 'ok' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage(fauxToolCall('submit_result', { status: 'ok', summary: 'fine' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('done'),
  ] : [
    fauxAssistantMessage(fauxToolCall('Agent', { subagent_type: 'probe', prompt: 'go' }), { stopReason: 'toolUse' }),
    fauxAssistantMessage('parent done'),
  ])
  pi.registerProvider('faux', { baseUrl: 'http://localhost:0', apiKey: 'x', api: f.api, streamSimple: f.provider.streamSimple, models: [{ id: 'f1', name: 'f1', reasoning: false, input: ['text'], cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }, contextWindow: 128000, maxTokens: 4096 }] })
  pi.registerTool({
    name: 'submit_result', label: 'Submit', description: 'Submit final result',
    parameters: { type: 'object', properties: { status: { enum: ['ok', 'fail'] }, summary: { type: 'string' } }, required: ['status', 'summary'] },
    async execute(_i: string, p: any) { L('submit ' + JSON.stringify(p)); return { content: [{ type: 'text', text: 'recorded' }], details: p } },
  })
  pi.registerTool({
    name: 'Agent', label: 'Agent', description: 'probe',
    parameters: { type: 'object', properties: { subagent_type: { type: 'string' }, prompt: { type: 'string' } }, required: ['subagent_type', 'prompt'] },
    prepareLoadout: () => ({ hiddenDeclarations: ['subagent'] }),
    async execute(_id: string, p: any, signal: any, _u: any, ctx: any) {
      L('agent start'); let r: any; try { r = await ctx.executeTool('subagent', { agent: p.subagent_type, task: p.prompt }, { signal }) } catch (e: any) { L('threw ' + e?.message); throw e }
            const msgs = r.result?.details?.results?.[0]?.messages ?? []
      for (const m of msgs) L(m.role + ' ' + JSON.stringify(m.role==='system'?'':m.content).slice(0, 260))
      L('exit ' + r.result?.details?.results?.[0]?.exitCode + ' isError ' + r.isError)
      return r
    },
  })
}
