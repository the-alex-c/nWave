import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import type { ExtensionAPI, ToolDefinition } from '@earendil-works/pi-coding-agent'
import { Value } from 'typebox/value'
import { describe, expect, it } from 'vitest'

import schemas from '../../nwave_ai/platform/role_envelope_schemas.json' with { type: 'json' }
import submitExtension from '../extensions/submit/index.ts'

const FLOOR = (schemas as Record<string, unknown>)['nw-acceptance-designer']

function load(roles: string[], child = true) {
  const agentsDir = mkdtempSync(join(tmpdir(), 'agents-'))
  for (const r of roles) writeFileSync(join(agentsDir, `${r}.md`), '---\nname: x\n---\n')
  writeFileSync(join(agentsDir, 'my-own.md'), '---\nname: my-own\n---\n')
  const tools: ToolDefinition[] = []
  submitExtension({ registerTool: (t: ToolDefinition) => tools.push(t) } as unknown as ExtensionAPI, { child, agentsDir })
  return tools
}

describe('submit extension', () => {
  it('should register no tool in the parent', () => {
    expect(load(['nw-software-crafter'], false)).toEqual([])
  })

  it('should register submit_<role> for every installed nw role in a child, and no other', () => {
    const names = load(['nw-software-crafter', 'nw-agent-builder']).map((t) => t.name)
    expect(names.sort()).toEqual(['submit_nw_agent_builder', 'submit_nw_software_crafter'])
  })

  it('should give a covered role its own schema', () => {
    const [tool] = load(['nw-software-crafter'])
    expect(JSON.parse(JSON.stringify(tool?.parameters))).toEqual((schemas as Record<string, unknown>)['nw-software-crafter'])
  })

  it('should give an uncovered role the floor schema', () => {
    const [tool] = load(['nw-agent-builder'])
    expect(JSON.parse(JSON.stringify(tool?.parameters))).toEqual(FLOOR)
  })

  it('should reject a rejected outcome with an empty diagnostic', () => {
    const [tool] = load(['nw-agent-builder'])
    expect(Value.Check(tool!.parameters, { outcome: 'rejected', diagnostic: '' })).toBe(false)
    expect(Value.Check(tool!.parameters, { outcome: 'accepted', diagnostic: '' })).toBe(true)
  })

  it('should record the envelope as the call details', async () => {
    const [tool] = load(['nw-agent-builder'])
    const args = { outcome: 'accepted', diagnostic: '' }
    const out = await tool!.execute('id', args as never, undefined, undefined, {} as never)
    expect(out.details).toEqual(args)
  })
})
