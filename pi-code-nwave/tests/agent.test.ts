import type { BeforeAgentStartEvent, ExtensionAPI, ExtensionToolContext, ToolDefinition } from '@earendil-works/pi-coding-agent'
import { mkdtempSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { Value } from 'typebox/value'
import { describe, expect, it, vi } from 'vitest'

import agentExtension from '../extensions/agent/index.ts'

type StartHandler = (event: BeforeAgentStartEvent) => unknown
type ExecuteTool = ExtensionToolContext['executeTool']

const tmpLog = () => mkdtempSync(join(tmpdir(), 'nw-agent-'))

function load(logDir = tmpLog()) {
  const tools: ToolDefinition[] = []
  const handlers: StartHandler[] = []
  const pi = {
    registerTool: (t: ToolDefinition) => tools.push(t),
    on: (event: string, h: StartHandler) => {
      if (event === 'before_agent_start') handlers.push(h)
    },
  }
  agentExtension(pi as unknown as ExtensionAPI, logDir)
  return { tools, handlers, agent: tools.find((t) => t.name === 'Agent') }
}

// What ctx.executeTool('subagent', ...) returns: AgentToolCallOutcome.
const outcome = (text: string, over: { isError?: boolean; results?: object[] } = {}) =>
  ({
    toolCall: { type: 'toolCall', id: 'id1/1', name: 'subagent', arguments: {} },
    isError: over.isError ?? false,
    result: { content: [{ type: 'text', text }], details: { results: over.results ?? [{ exitCode: 0, stopReason: 'stop' }] } },
  }) as Awaited<ReturnType<ExecuteTool>>

const childOk = (text: string) => outcome(text)

const toolCtx = (executeTool: ExecuteTool, session = 'sess-1') =>
  ({ executeTool, sessionManager: { getSessionId: () => session } }) as unknown as ExtensionToolContext

function run(executeTool: ExecuteTool, params = { subagent_type: 'explore', prompt: 'go' }, logDir?: string, session?: string) {
  const { agent } = load(logDir)
  if (!agent) throw new Error('Agent tool not registered')
  return agent.execute('id1', params, undefined, undefined, toolCtx(executeTool, session))
}

function schema() {
  const { agent } = load()
  if (!agent) throw new Error('Agent tool not registered')
  return agent.parameters
}

describe('Agent extension', () => {
  describe('registration', () => {
    it('should register a tool named Agent', () => {
      expect(load().agent).toBeDefined()
    })

    it('should accept a call with subagent_type and prompt', () => {
      expect(Value.Check(schema(), { subagent_type: 'nw-x', prompt: 'go' })).toBe(true)
    })

    it.each(['subagent_type', 'prompt'])('should reject a call without %s', (missing) => {
      const args: Record<string, string> = { subagent_type: 'nw-x', prompt: 'go' }
      delete args[missing]
      expect(Value.Check(schema(), args)).toBe(false)
    })

    it('should hide the subagent tool from the model while keeping it callable', () => {
      expect(load().agent?.prepareLoadout?.({} as never)).toEqual({ hiddenDeclarations: ['subagent'] })
    })
  })

  describe('delegation', () => {
    it('should call subagent with subagent_type as agent and prompt as task', async () => {
      const executeTool = vi.fn(async () => childOk('PONG'))
      await run(executeTool as unknown as ExecuteTool)
      expect(executeTool).toHaveBeenCalledWith('subagent', { agent: 'explore', task: 'go' }, expect.anything())
    })

    it('should pass the abort signal through to subagent', async () => {
      const { agent } = load()
      const signal = new AbortController().signal
      const executeTool = vi.fn(async () => childOk('PONG'))
      await agent?.execute('id1', { subagent_type: 'nw-x', prompt: 'go' }, signal, undefined, toolCtx(executeTool as unknown as ExecuteTool))
      expect(executeTool).toHaveBeenCalledWith('subagent', expect.anything(), { signal })
    })

    it('should return the child text when the child succeeds', async () => {
      const r = await run(async () => childOk('PONG'))
      expect(r.content).toEqual([{ type: 'text', text: 'PONG' }])
      expect(r.isError).toBeFalsy()
    })
  })

  describe('child stopped at its maxTurns limit', () => {
    const capped = async () => outcome('partial work', { results: [{ exitCode: 0, stopReason: 'stop', partial: true }] })

    it('should return the child text without isError', async () => {
      const r = await run(capped)
      expect(r.isError).toBeFalsy()
      expect((r.content[0] as { text: string }).text).toContain('partial work')
    })

    it('should mark the result partial in details so a later envelope check can see it', async () => {
      expect((await run(capped)).details).toMatchObject({ partial: true })
    })
  })

  describe('child failure', () => {
    // pi-code reports an unknown agent with isError false.
    const unknown = async () => outcome('Agent failed: Unknown agent "nope".', { results: [] })

    it('should return isError true when the child fails although subagent reported isError false', async () => {
      expect((await run(unknown)).isError).toBe(true)
    })

    it('should start the text the model sees with the failure kind and carry the detail', async () => {
      expect(((await run(unknown)).content[0] as { text: string }).text).toMatch(/^Agent failed \(subagent\): .*Unknown agent/)
    })
  })

  describe('typed reply from an nw role', () => {
    const call = (name: string, id: string, args: object) => ({ type: 'toolCall', id, name, arguments: args })
    const assistant = (...content: object[]) => ({ role: 'assistant', content })
    const toolResult = (toolCallId: string, isError = false) => ({ role: 'toolResult', toolCallId, isError })
    const envelope = { outcome: 'accepted', diagnostic: '' }
    const withMessages = (messages: object[], over: object = {}) => async () =>
      outcome('', { results: [{ exitCode: 0, stopReason: 'stop', messages, ...over }] })
    const nw = (executeTool: ExecuteTool) => run(executeTool, { subagent_type: 'nw-x', prompt: 'go' })
    const text = (r: { content: object[] }) => (r.content[0] as { text: string }).text

    it('should return the submitted envelope as the reply text and in details', async () => {
      const r = await nw(withMessages([assistant(call('submit_nw_x', 'a', envelope)), toolResult('a')]))
      expect(r.isError).toBeFalsy()
      expect(JSON.parse(text(r))).toEqual(envelope)
      expect(r.details).toMatchObject({ envelope })
    })

    it('should use the last valid submit when the model submitted twice', async () => {
      const second = { outcome: 'rejected', diagnostic: 'why' }
      const r = await nw(
        withMessages([assistant(call('submit_nw_x', 'a', envelope)), toolResult('a'), assistant(call('submit_nw_x', 'b', second)), toolResult('b')]),
      )
      expect(JSON.parse(text(r))).toEqual(second)
    })

    it('should ignore a submit pi rejected as invalid', async () => {
      const bad = { outcome: 'rejected', diagnostic: '' }
      const r = await nw(
        withMessages([assistant(call('submit_nw_x', 'a', envelope)), toolResult('a'), assistant(call('submit_nw_x', 'b', bad)), toolResult('b', true)]),
      )
      expect(JSON.parse(text(r))).toEqual(envelope)
    })

    it('should fail with kind envelope when the child answered in prose only', async () => {
      const r = await nw(withMessages([assistant({ type: 'text', text: 'done' })]))
      expect(r.isError).toBe(true)
      expect(text(r)).toMatch(/^Agent failed \(envelope\): /)
    })

    it('should fail with kind envelope when every submit was invalid', async () => {
      const r = await nw(withMessages([assistant(call('submit_nw_x', 'a', {})), toolResult('a', true)]))
      expect(text(r)).toMatch(/^Agent failed \(envelope\): /)
    })

    it('should ignore a submit tool of another role', async () => {
      const r = await nw(withMessages([assistant(call('submit_nw_other', 'a', envelope)), toolResult('a')]))
      expect(text(r)).toMatch(/^Agent failed \(envelope\): /)
    })

    it('should accept a maxTurns-capped child that submitted, marked partial', async () => {
      const r = await nw(withMessages([assistant(call('submit_nw_x', 'a', envelope)), toolResult('a')], { partial: true }))
      expect(r.isError).toBeFalsy()
      expect(r.details).toMatchObject({ envelope, partial: true })
    })

    it('should fail a maxTurns-capped child that never submitted', async () => {
      const r = await nw(withMessages([assistant({ type: 'text', text: 'cut off' })], { partial: true }))
      expect(text(r)).toMatch(/^Agent failed \(envelope\): /)
    })

    it('should not demand an envelope from a non-nw agent', async () => {
      const r = await run(async () => childOk('plain'))
      expect(r.isError).toBeFalsy()
      expect(text(r)).toBe('plain')
    })
  })

  describe('submit reminder in the child prompt', () => {
    // A host-scoped reminder line names the role's submit tool so a long real-work child
    // ends with an accepted submit call instead of prose (P2).
    const dispatch = async (subagent_type: string, prompt = 'go') => {
      const executeTool = vi.fn(async () => childOk('PONG'))
      await run(executeTool as unknown as ExecuteTool, { subagent_type, prompt })
      const call = executeTool.mock.calls[0] as unknown as [string, { agent: string; task: string }, object]
      return call[1].task
    }

    it('should end an nw-x child prompt with one line naming its submit tool', async () => {
      const task = await dispatch('nw-x')
      expect(task.split('\n').at(-1)).toContain('submit_nw_x')
      expect(task.split('submit_nw_x')).toHaveLength(2)
    })

    it('should name the submit tool of a hyphenated role', async () => {
      const task = await dispatch('nw-solution-architect')
      expect(task.split('\n').at(-1)).toContain('submit_nw_solution_architect')
      expect(task.split('submit_nw_solution_architect')).toHaveLength(2)
    })

    it('should append no reminder to a non-nw child prompt', async () => {
      expect(await dispatch('explore', 'go')).toBe('go')
    })
  })

  describe('system prompt roster', () => {
    // The text pi-code writes (subagent/index.ts, before_agent_start).
    const LIST = '- nw-software-crafter (user): Builds code.\n- explore (builtin): Reads code.'
    const piCodeText = `Delegate isolated tasks with the subagent tool ({agent, task}). Available agents:\n${LIST}`

    const start = () => load().handlers[0]
    const rewrite = (sections: Record<string, unknown>) => {
      const event = { systemPromptOptions: { sections } } as unknown as BeforeAgentStartEvent
      start()?.(event)
      return event.systemPromptOptions.sections as Record<string, unknown>
    }

    it('should register a before_agent_start handler', () => {
      expect(start()).toBeDefined()
    })

    it('should not mention the hidden subagent tool in the roster', () => {
      expect(String(rewrite({ subagents: piCodeText }).subagents)).not.toMatch(/subagent tool/i)
    })

    it('should tell the model to call Agent with subagent_type and prompt', () => {
      expect(String(rewrite({ subagents: piCodeText }).subagents)).toMatch(/Agent.*subagent_type.*prompt/s)
    })

    it('should not describe the subagent parameter shape {agent, task}', () => {
      expect(String(rewrite({ subagents: piCodeText }).subagents)).not.toContain('{agent, task}')
    })

    it('should keep every agent line pi-code listed, unchanged', () => {
      expect(String(rewrite({ subagents: piCodeText }).subagents)).toContain(LIST)
    })

    it('should leave other sections untouched', () => {
      expect(rewrite({ subagents: piCodeText, other: 'keep' }).other).toBe('keep')
    })

    it('should not add a subagents section when pi-code wrote none', () => {
      expect(rewrite({ other: 'keep' })).toEqual({ other: 'keep' })
    })

    it('should not throw when the event carries no sections', () => {
      expect(() => start()?.({} as BeforeAgentStartEvent)).not.toThrow()
    })
  })

  describe('requests log', () => {
    const lines = (dir: string, session: string) =>
      readFileSync(join(dir, `${session}.jsonl`), 'utf8').trim().split('\n').map((l) => JSON.parse(l))

    it('should append one nwdes request record per call, even for a failed one', async () => {
      const dir = tmpLog()
      await run(async () => childOk('ok'), { subagent_type: 'nw-x', prompt: 'go' }, dir)
      await run(async () => outcome('boom', { isError: true }), { subagent_type: 'nw-y', prompt: 'go' }, dir)
      const [a, b] = lines(dir, 'sess-1')
      expect(a).toMatchObject({ role: 'nw-x', task: null, slice: null, continuation: false, rework: false })
      expect(a.start <= a.end && /^\d{4}-\d\d-\d\dT[\d:.]+Z$/.test(a.start)).toBe(true)
      expect(b.role).toBe('nw-y')
    })

    it('should keep one file per pi session', async () => {
      const dir = tmpLog()
      await run(async () => childOk('ok'), { subagent_type: 'nw-x', prompt: 'go' }, dir, 'sess-a')
      await run(async () => childOk('ok'), { subagent_type: 'nw-y', prompt: 'go' }, dir, 'sess-b')
      expect(lines(dir, 'sess-a').map((r) => r.role)).toEqual(['nw-x'])
      expect(lines(dir, 'sess-b').map((r) => r.role)).toEqual(['nw-y'])
    })

    it('should not fail the delegation when the log cannot be written', async () => {
      const r = await run(async () => childOk('ok'), undefined, '/nonexistent-dir/x')
      expect(r.isError).toBeUndefined()
    })

    describe('observed child model', () => {
      // Dispatch logs the observed model (P3): the per-session requests record gains the
      // model pair {provider, model} derived from pi's observed child model string.
      const withModel = (model?: string) => async () => outcome('ok', { results: [{ exitCode: 0, stopReason: 'stop', ...(model !== undefined && { model }) }] })

      it('should record the observed child model as the pair {provider, model}', async () => {
        const dir = tmpLog()
        await run(withModel('z-ai/glm-5.3-flash'), { subagent_type: 'nw-x', prompt: 'go' }, dir)
        expect(lines(dir, 'sess-1')[0]).toMatchObject({ model: { provider: 'z-ai', model: 'glm-5.3-flash' } })
      })

      it('should omit the model field when pi reports no child model', async () => {
        const dir = tmpLog()
        await run(withModel(), { subagent_type: 'nw-x', prompt: 'go' }, dir)
        expect(lines(dir, 'sess-1')[0]).not.toHaveProperty('model')
      })
    })
  })
})
