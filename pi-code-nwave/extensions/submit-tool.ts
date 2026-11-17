/** The typed-reply tool a role answers through. */
export const submitToolName = (role: string): string => 'submit_' + role.replaceAll('-', '_')
