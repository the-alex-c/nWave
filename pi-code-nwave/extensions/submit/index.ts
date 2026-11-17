/** nWave's per-role `submit_<role>` tools: the typed reply a child role answers through. */

import { readdirSync } from 'node:fs'
import { join } from 'node:path'

import type { ExtensionAPI } from '@earendil-works/pi-coding-agent'

import { piAgentDir } from '../agent-dir.ts'
import { submitToolName } from '../submit-tool.ts'
import schemas from '../../role_envelope_schemas.json' with { type: 'json' }

export type SubmitOptions = { child?: boolean; agentsDir?: string }

const FLOOR_ROLE = 'nw-acceptance-designer'
const byRole = schemas as Record<string, object>

const defaultAgentsDir = () => join(piAgentDir(), 'agents')

export default function submitExtension(
  pi: ExtensionAPI,
  { child = !!process.env.PI_CODE_SUBAGENT, agentsDir = defaultAgentsDir() }: SubmitOptions = {},
): void {
  if (!child) return
  for (const file of readdirSync(agentsDir)) {
    const role = /^(nw-.+)\.md$/.exec(file)?.[1]
    if (!role) continue
    pi.registerTool({
      name: submitToolName(role),
      label: 'Submit',
      description: 'Submit your final result. Call exactly once when done.',
      parameters: (byRole[role] ?? byRole[FLOOR_ROLE]) as never,
      async execute(_id, params) {
        return { content: [{ type: 'text', text: 'recorded' }], details: params }
      },
    })
  }
}
