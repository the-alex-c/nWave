# Pi vs Claude Code: gaps for nWave / nwdes

Scope: what nWave expects from Claude Code (`nwave_ai/hooks/*`, `nWave/agents/*`,
`nWave/skills/nw-role-invocation`, `nwave_ai/platform/capability.py`) vs `pi/main`
(upstream earendil-works/pi). Source-read only; nothing was executed.

| Area | Claude Code (nWave expects) | Pi | Gap |
|---|---|---|---|
| Role delegation | `Agent(subagent_type="nw-<role>", prompt=...)`, exact installed role with declared tool ceiling | no `Agent`/`Task` tool or named-agent registry; `examples/extensions/subagent` spawns a `pi` subprocess | Hard gap |
| Agent files | `~/.claude/agents/nw/*.md`: `model`, `maxTurns`, `tools` (scoped `Bash(...)`), `skills:` preload, `StructuredOutput` | example ext reads `~/.pi/agent/agents/*.md`: `name`, `description`, `tools`, `model` | No `maxTurns`, scoped grants, preload, reply channel |
| Structured reply | `StructuredOutput` channel; `role_envelope_schemas.json` | none | Roles can't return the envelope |
| Tool ceiling | omitted `tools:` = inherit all (`INSTRUCTED`); listed tools truly withheld (`ENFORCED`) | `pi.setActiveTools()` in-process; per-subagent withholding only via subprocess flags | Verify before claiming `ENFORCED` |
| Role tools | `Agent`, `SendMessage`, `TaskCreate`, `TaskUpdate`, `Skill`, `WebFetch`, `WebSearch`, `Glob` | `read bash edit write grep find ls` | `Glob`->`find`; rest missing (`SendMessage` soft: root-mediated fallback) |
| Skills | `~/.claude/skills/<name>/SKILL.md`; `Skill` tool; `user-invocable: false` | `~/.pi/agent/skills`, `~/.agents/skills`; read by path; `/skill:name`; honors `disable-model-invocation` only | Path rewrite; no `Skill` tool |
| Commands | `~/.claude/commands/nw/*.md` (`/nw-*`) | prompt templates `~/.pi/agent/prompts/*.md` | Emit as templates |
| Config root / paths | `~/.claude/...` hard-coded in roles and skills | `~/.pi/agent` (`PI_CODING_AGENT_DIR`) | No pi rewrite table or installer platform (`HOSTS` lacks `pi`) |
| Hooks registry | `settings.json` `hooks` block, registered by installer (`registration.py`) | extension events (`pi.on(...)`); `@hsingjui/pi-hooks` (installed) adapts Claude command hooks, coverage unchecked | Registration path differs |
| `PreToolUse` `Agent` (pre-task) | guards each role dispatch | no `Agent` tool | Missing |
| `PreToolUse` `Write`/`Edit` | guard (`pre-write`/`pre-edit`) | `tool_call` can block; payload shape differs | Adapter needed |
| `PreToolUse` `Bash` | git-stash guard, attribution rewrite via `updatedInput` | `tool_call` can mutate input | Adapter needed |
| `PreToolUse` `SendMessage`, `TaskCreate\|TaskUpdate` | guard | tools absent | Missing |
| `SubagentStop` | subagent completion handling | no subagents, no event | Missing |
| `SessionStart` | `additionalContext` injection (notices) | `session_start`; no `additionalContext` contract | Adapter or `before_agent_start` |
| `SessionEnd` | cleanup | `session_shutdown` | Near match |
| Hook protocol | Claude JSON on stdin (`hook_event_name`, `tool_name`, `tool_input`, `cwd`, `session_id`, `agent_type`); exit 0/1/2; `hookSpecificOutput.permissionDecision`/`updatedInput` | extension API in-process | Shim must translate both ways |
| Model per role | agent frontmatter `model:` | none native | Needs agent layer |
| Fresh-context runs (review, EXAMINE) | isolated subagent context | subprocess example only | Needs agent layer |
| Session record (`nwdes measure`) | Claude transcripts | `docs/session-format.md` | Native measure unqualified; use `--requests` |
| Doctor/install verification | `nwave-ai doctor` checks Claude install; container e2e tests | none | Nothing to run on pi |

## Host-neutral (works as-is)

- `nwdes` CLI, handoff JSON, briefs/prompts/packets.
- Skill content (from `~/.agents/skills` or `~/.pi/agent/skills`).
- Workflow: host runs roles, picks models, observes RED/GREEN; `nwdes` never launches a model.

## Smallest path to viable

1. Subagent extension: `Agent(subagent_type=...)`, named role files, tool allowlist, skill preload, model, `maxTurns`, structured output, `SubagentStop`.
2. Hook shim running `python -m nwave_ai.hooks <Event> --host pi` (reuse `pi-hooks` if coverage suffices); add `pi` to `HOSTS`.
3. Installer `pi` platform: skills, agents, prompt templates, path-rewrite table, `PI_CODING_AGENT_DIR`.
4. Verify tool-ceiling enforcement, model inheritance, and session format.
