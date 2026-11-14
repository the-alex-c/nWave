/**
 * Turns what ctx.executeTool('subagent', ...) returned into a typed outcome.
 *
 * Input is a minimal structural type on purpose (ADR 6): pi's AgentToolCallOutcome is assignable
 * to it, and `details.results[0]` mirrors pi-code's SingleResult, which is not a dependency.
 */

export type FailureKind = 'exit' | 'stop' | 'subagent' | 'tool' | 'empty'

export type Outcome = { ok: true; text: string; partial?: true } | { ok: false; kind: FailureKind; detail: string }

export interface ToolResult {
  isError: boolean
  result: { content: { type: string; text?: string }[]; details?: { results?: object[] } }
}

interface Child {
  exitCode?: number
  stopReason?: string
  stderr?: string
  errorMessage?: string
  partial?: boolean
}

const fail = (kind: FailureKind, detail: string): Outcome => ({ ok: false, kind, detail })

// isError is not trusted alone: pi-code reports failures such as an unknown agent with isError false.
export function classify({ isError, result }: ToolResult): Outcome {
  const text = result.content.map((c) => c.text ?? '').join('')
  if (isError) return fail('tool', text)
  if (text.startsWith('Agent failed:')) return fail('subagent', text)
  const child = result.details?.results?.[0] as Child | undefined
  if (!child) return fail('empty', text)
  if (child.exitCode !== 0) return fail('exit', child.stderr || child.errorMessage || text)
  if (child.stopReason === 'error' || child.stopReason === 'aborted') return fail('stop', child.errorMessage || child.stopReason)
  return child.partial ? { ok: true, text, partial: true } : { ok: true, text }
}
