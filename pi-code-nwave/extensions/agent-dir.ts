import { homedir } from 'node:os'
import { join } from 'node:path'

/** pi's agent directory, honouring PI_CODING_AGENT_DIR. */
export const piAgentDir = (): string => process.env.PI_CODING_AGENT_DIR || join(homedir(), '.pi', 'agent')
