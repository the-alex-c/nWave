# Pi vs Devin: what Devin has that pi lacks

Scope: the Devin integration (`scripts/install/plugins/devin_skills_plugin.py`,
`scripts/shared/platform_contracts.py` DEVIN_* tables, `docs/guides/installing-devin.md`) vs `pi/main`.
Source-read only; nothing was executed.

Devin is **skills-only**: no hooks (Devin CLI 3000.6.14 has no hook API per the guide), no agents,
no commands. Roles are not delivered; the host runs verification commands and the assistant uses
`nwdes` from the shell with the installed `nw-` skills as methodology guidance.

| Area | Devin (nWave relies on) | Pi | Gap |
|---|---|---|---|
| Skills root | `~/.config/devin/skills/<name>/SKILL.md` (`DEVIN_CONFIG_DIR` override) | `~/.pi/agent/skills`, `~/.agents/skills` (`PI_CODING_AGENT_DIR`) | Path only |
| Skill format | Claude-compatible `SKILL.md`; `name`, `description` recognised; unknown keys preserved | Agent Skills spec; unknown keys warn, not fail | None |
| Skill copy | public skills copied verbatim, no frontmatter stripping | honors `disable-model-invocation`; `user-invocable` unknown to pi | None (ignored) |
| Ownership | `.nwave-manifest.json`; foreign `nw-*` dirs refused as collisions | none | No `pi` installer plugin |
| Agent role files | folded into skills (`~/.claude/agents/` rewritten to skills root) | n/a | Same treatment viable |
| Path rewrites | `DEVIN_PATH_REWRITES` -> `~/.config/devin/skills/` | no table | Add pi table |
| Hooks | none | extension `tool_call` available | Pi exceeds Devin |
| Role delegation | none | none (subagent example only) | **No gap** |
| Commands | none | prompt templates | Pi exceeds Devin |
| Typed reply | none | none | **No gap** |
| Project guidance | assistant told via skills or pasted sentence | `AGENTS.md`, skills | Pi exceeds Devin |
| Fallback | `nwdes` CLI from shell | same | No gap |
| Verification | installer self-validation; live slash-command discovery unverified | none | No `pi` platform to validate |

## Takeaways

- Devin is the lowest rung: a pi install that only copies public skills matches it with no host-side work.
- Pi can read the Codex shared tree (`~/.agents/skills/`), so a Devin-style skills copy is unnecessary if Codex's plugin already owns that path. Otherwise a pi install needs its own manifest-owned root (`~/.pi/agent/skills/`) to avoid collision with `CodexSkillsPlugin`'s single-writer ownership.
- Remaining work for the Devin-level bar: a `pi` installer platform (skills copy, manifest, `PI_CODING_AGENT_DIR`, rewrite table). No hook, delegation, or reply mechanism is required.

## Host ladder (lowest to highest requirement)

1. **Devin**: skills only.
2. **Cursor / Copilot**: guard hook only.
3. **Codex**: skills + role registry + `spawn_agent` + typed reply + shell hook.
4. **OMP**: Codex + commands + extension + `autoloadSkills`/`skill://`.
5. **Claude Code**: full hook set, `Agent`, `SendMessage`, scoped tool grants, `StructuredOutput`.
