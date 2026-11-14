import type { BeforeAgentStartEvent, ExtensionAPI, ExtensionToolContext, ToolDefinition } from '@earendil-works/pi-coding-agent'
import { Value } from 'typebox/value'
import { describe, expect, it, vi } from 'vitest'

import agentExtension from '../extensions/agent/index.ts'

type StartHandler = (event: BeforeAgentStartEvent) => unknown
type ExecuteTool = ExtensionToolContext['executeTool']

function load() {
  const tools: ToolDefinition[] = []
  const handlers: StartHandler[] = []
  const pi = {
    registerTool: (t: ToolDefinition) => tools.push(t),
    on: (event: string, h: StartHandler) => {
      if (event === 'before_agent_start') handlers.push(h)
    },
  }
  agentExtension(pi as unknown as ExtensionAPI)
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

const toolCtx = (executeTool: ExecuteTool) => ({ executeTool }) as unknown as ExtensionToolContext

function run(executeTool: ExecuteTool, params = { subagent_type: 'nw-x', prompt: 'go' }) {
  const { agent } = load()
  if (!agent) throw new Error('Agent tool not registered')
  return agent.execute('id1', params, undefined, undefined, toolCtx(executeTool))
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
      expect(executeTool).toHaveBeenCalledWith('subagent', { agent: 'nw-x', task: 'go' }, expect.anything())
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
})
