/**
 * Turns what ctx.executeTool('subagent', ...) returned into a typed outcome.
 *
 * Input is a minimal structural type on purpose (ADR 6): pi's AgentToolCallOutcome is assignable
 * to it, and `details.results[0]` mirrors pi-code's SingleResult, which is not a dependency.
 */

export type FailureKind = 'exit' | 'stop' | 'subagent' | 'tool' | 'empty' | 'envelope'

export type Reply = { ok: true; text: string; partial?: true; envelope?: unknown }
export type Outcome = Reply | { ok: false; kind: FailureKind; detail: string }

export interface ToolResult {
  isError: boolean
  result: { content: { type: string; text?: string }[]; details?: { results?: object[] } }
}

export interface Child {
  exitCode?: number
  stopReason?: string
  stderr?: string
  errorMessage?: string
  partial?: boolean
  model?: string
  messages?: Message[]
}

interface Message {
  role?: string
  content?: unknown
  toolCallId?: string
  isError?: boolean
}

interface ToolCall {
  type?: string
  id?: string
  name?: string
  arguments?: unknown
}

const fail = (kind: FailureKind, detail: string): Outcome => ({ ok: false, kind, detail })

// isError is not trusted alone: pi-code reports failures such as an unknown agent with isError false.
// The last call to `submitTool` that pi accepted (its toolResult is not an error); undefined when none.
function submitted(messages: Message[], submitTool: string): { value: unknown } | undefined {
  const rejected = new Set(messages.filter((m) => m.role === 'toolResult' && m.isError).map((m) => m.toolCallId))
  const calls = messages
    .filter((m) => m.role === 'assistant' && Array.isArray(m.content))
    .flatMap((m) => m.content as ToolCall[])
    .filter((c) => c.type === 'toolCall' && c.name === submitTool && !rejected.has(c.id))
  const last = calls.at(-1)
  return last && { value: last.arguments }
}

const flagPartial = (reply: Reply, child: Child): Outcome => (child.partial ? { ...reply, partial: true } : reply)

// `submitTool`: when given, the child must have made a valid call to it; its arguments are the reply.
export function classify({ isError, result }: ToolResult, submitTool?: string): Outcome {
  const text = result.content.map((c) => c.text ?? '').join('')
  if (isError) return fail('tool', text)
  if (text.startsWith('Agent failed:')) return fail('subagent', text)
  const child = result.details?.results?.[0] as Child | undefined
  if (!child) return fail('empty', text)
  if (child.exitCode !== 0) return fail('exit', child.stderr || child.errorMessage || text)
  if (child.stopReason === 'error' || child.stopReason === 'aborted') return fail('stop', child.errorMessage || child.stopReason)
  if (submitTool) {
    const sub = submitted(child.messages ?? [], submitTool)
    if (!sub) return fail('envelope', `no valid ${submitTool} call`)
    return flagPartial({ ok: true, text: JSON.stringify(sub.value), envelope: sub.value }, child)
  }
  return flagPartial({ ok: true, text }, child)
}
