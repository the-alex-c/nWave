# Pi vs Codex: what Codex has that pi lacks

Scope: the Codex integration (`scripts/install/plugins/codex_*.py`, `scripts/shared/platform_contracts.py`
CODEX_* tables, `nwave_ai/hooks/registration.py`, `nWave/skills/nw-role-invocation`) vs `pi/main`.
Source-read only; nothing was executed. Codex is the **minimum bar**: it needs fewer host features
than Claude Code, and nWave ships with Codex's workarounds (prompt-only tool ceiling, inlined skills).

| Area | Codex (nWave relies on) | Pi | Gap |
|---|---|---|---|
| Role registry | `~/.codex/agents/<name>.toml` (`name`, `description`, `developer_instructions`, optional `model`); unknown fields drop the agent | none native; subagent example reads `~/.pi/agent/agents/*.md` | Hard gap |
| Delegation | `spawn_agent(agent_type="nw-<role>", message=...)` | no equivalent tool | Hard gap |
| Typed reply | `--output-schema` enforces the role envelope regardless of declared tools | none | Needs extension or `pi` flag |
| Tool ceiling | not enforced: `tools` -> prompt preamble (grant/deny lines), sandbox/approval at config level | `pi.setActiveTools()` in-process; no per-role ceiling | Codex tolerates prompt-only (`INSTRUCTED`); pi can match this |
| Skill preload | inlined into `developer_instructions` (self-contained snapshot via `render_installed_role`) | none | Installer can inline; no host feature needed |
| Skills location | `~/.agents/skills/` (shared, manifest-owned by `CodexSkillsPlugin`) | **also scans `~/.agents/skills/`** | None: pi can read the Codex tree |
| Skill frontmatter | strips `user-invocable`, `disable-model-invocation` | honors `disable-model-invocation` | None |
| Skill invocation | `$nw-buddy` | `/skill:nw-buddy` | Docs/commands only |
| Commands | none (skills invoked with `$`) | prompt templates | Optional |
| Hook file | `~/.codex/hooks.json` or `[hooks]` in `config.toml`; matcher `^exec_command$\|^Bash$`; one `PreToolUse` entry | extension events; `@hsingjui/pi-hooks` (installed, coverage unchecked) | Needs Claude-shape shim |
| Hook payload | Claude-shaped JSON on stdin; `exec_command` normalised to `Bash` (`cmd` -> `command`) | in-process `tool_call` | Shim translates both ways |
| Hook set | `PreToolUse` only (no `Agent`, `Write`, `Edit`, `SubagentStop`, `SessionStart`) | n/a | Pi needs only `bash` guard to match Codex |
| Hook reply | exit 0/1/2, `permissionDecision` | `tool_call` returns block/mutate | Shim |
| Peer messaging | `SendMessage` not projected; root-mediated fallback | none | None: same fallback |
| Project guidance | `AGENTS.md` managed section | pi reads `AGENTS.md` | None |
| Path rewrites | `CODEX_PATH_REWRITES` -> `~/.agents/skills`, `~/.codex/agents`, `~/.codex/hooks` | no table | Add pi table |
| Home override | `CODEX_HOME` | `PI_CODING_AGENT_DIR` | Env var differs |
| Model per role | optional `model` in TOML; Claude aliases dropped with notice | none native | Needs agent layer |
| Installer + verification | `codex_agents_plugin`, `codex_skills_plugin`; container e2e install tests | none | No `pi` platform |
| Fresh-context runs | `spawn_agent` isolated | subprocess example only | Needs agent layer |

## Why Codex is the closest template for pi

- Shared skills tree already works for pi (`~/.agents/skills/`).
- Only one hook is required (`PreToolUse` on shell) and no `SubagentStop`/`SessionStart`.
- Tool ceiling is prompt-only, so pi's lack of per-role tool withholding is acceptable (reported as `INSTRUCTED`).
- Skills are inlined into the role text, so `autoloadSkills` / `skill://` are not needed.
- Peer messaging falls back to the root.

## Remaining pi gaps against the Codex bar

1. Named role registry + `spawn_agent`-style delegation (the only real missing host feature).
2. Typed-reply enforcement (Codex `--output-schema` equivalent).
3. Hook shim: `python -m nwave_ai.hooks PreToolUse --host pi`, mapping pi `bash` to `Bash`; add `pi` to `HOSTS` in `registration.py` and `__main__.py`.
4. Installer: `pi` platform plugin (agents + shared skills reuse + path-rewrite table + `PI_CODING_AGENT_DIR`), with a manifest so it does not collide with `CodexSkillsPlugin`'s single-writer ownership of `~/.agents/skills/`.
5. Optional per-role `model`.
