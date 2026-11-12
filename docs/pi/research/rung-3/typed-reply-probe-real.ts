import { appendFileSync } from 'node:fs'
import sub from '/Users/USER/.pi/agent/npm/node_modules/pi-code/extensions/subagent/index.ts'
const child = !!process.env.PI_CODE_SUBAGENT
const L = (s: string) => appendFileSync('/tmp/probe3/log.txt', (child ? 'C ' : 'P ') + s + '\n')
export default function (pi: any) {
  sub(pi)
  if (child) pi.registerTool({
    name: 'submit_result', label: 'Submit', description: 'Submit the final result. Call exactly once when done.',
    parameters: { type: 'object', properties: { status: { enum: ['ok', 'fail'] }, summary: { type: 'string' } }, required: ['status', 'summary'] },
    async execute(_i: string, p: any) { return { content: [{ type: 'text', text: 'recorded' }], details: p } },
  })
  pi.registerTool({
    name: 'Agent', label: 'Agent', description: 'Delegate a task to a subagent',
    parameters: { type: 'object', properties: { subagent_type: { type: 'string' }, prompt: { type: 'string' } }, required: ['subagent_type', 'prompt'] },
    prepareLoadout: () => ({ hiddenDeclarations: ['subagent'] }),
    async execute(_id: string, p: any, signal: any, _u: any, ctx: any) {
      const r = await ctx.executeTool('subagent', { agent: p.subagent_type, task: p.prompt }, { signal })
      const res = r.result?.details?.results?.[0]
      const msgs = res?.messages ?? []
      const calls = msgs.filter((m: any) => m.role === 'assistant').flatMap((m: any) => m.content.filter((c: any) => c.type === 'toolCall'))
      L('exit ' + res?.exitCode + ' tools ' + calls.map((c: any) => c.name).join(','))
      const sub = calls.filter((c: any) => c.name === 'submit_result').pop()
      L('envelope ' + JSON.stringify(sub?.arguments))
      L('final ' + JSON.stringify(msgs.at(-1)?.content).slice(0, 200))
      return r.result
    },
  })
}
