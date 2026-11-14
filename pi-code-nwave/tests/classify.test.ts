import { describe, expect, it } from 'vitest'

import { classify } from '../extensions/agent/classify.ts'

// What ctx.executeTool('subagent', ...) returns (agent-wrapper-mechanics.md, run results 3-4).
const wrap = (text: string, results: object[] = [], isError = false) => ({
    isError,
    result: { content: [{ type: 'text', text }], details: { mode: 'single', results } },
})
const child = (over: object = {}) => ({ agent: 'nw-x', exitCode: 0, messages: [], stderr: '', ...over })

describe('classify(subagent result)', () => {
    it('should return ok with the child text when it exits 0 and stops normally', () => {
        expect(classify(wrap('PONG', [child({ stopReason: 'stop' })]))).toEqual({ ok: true, text: 'PONG' })
    })

    it('should return an exit failure with stderr when the child exits nonzero', () => {
        const r = classify(wrap('boom', [child({ exitCode: 1, stderr: 'crash' })]))
        expect(r).toMatchObject({ ok: false, kind: 'exit', detail: expect.stringContaining('crash') })
    })

    it.each(['error', 'aborted'])('should return a stop failure when the child stopReason is %s', (stopReason) => {
        expect(classify(wrap('x', [child({ stopReason })]))).toMatchObject({ ok: false, kind: 'stop' })
    })

    it('should return a subagent failure when the text starts with "Agent failed:" even though isError is false', () => {
        const r = classify(wrap('Agent failed: Unknown agent "nope". Available agents: a.'))
        expect(r).toMatchObject({ ok: false, kind: 'subagent', detail: expect.stringContaining('Unknown agent') })
    })

    it('should return a tool failure when the tool call reports isError', () => {
        expect(classify(wrap('blocked', [], true))).toMatchObject({ ok: false, kind: 'tool' })
    })

    it('should return an empty failure when the result has no child result', () => {
        expect(classify(wrap('hm'))).toMatchObject({ ok: false, kind: 'empty' })
    })

    it('should return ok flagged partial when the child stopped at its maxTurns limit', () => {
        expect(classify(wrap('x', [child({ partial: true })]))).toEqual({ ok: true, text: 'x', partial: true })
    })

    it('should not flag partial when the child ran to completion', () => {
        expect(classify(wrap('x', [child({ stopReason: 'stop' })]))).not.toHaveProperty('partial')
    })
})
