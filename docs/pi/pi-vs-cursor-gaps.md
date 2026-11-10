# Pi vs Cursor: what Cursor has that pi lacks

Scope: the Cursor integration (`docs/guides/installing-cursor.md`, `nwave_ai/hooks/registration.py`,
`docs/guides/vendor-support.md`) vs `pi/main`. Source-read only; nothing was executed.

Cursor is the **floor**: hook-only, no agents, no native skills, no `/nw-*` commands. nWave does not
deliver roles there; the assistant is pointed at the `deliver-feature` guide and `nwdes` runs from the shell.

| Area | Cursor (nWave relies on) | Pi | Gap |
|---|---|---|---|
| Installed assets | `~/.cursor/hooks.json` only (`CURSOR_HOME` override) | none | No `pi` installer platform |
| Hook entry | one `preToolUse` entry: `{command, matcher: "Shell\|Write\|Edit\|Delete", timeout: 30}`, `version: 1` | extension `tool_call` event | Needs Claude-shape shim |
| Hook payload | Claude-shaped JSON on stdin, `--host cursor` | in-process | Shim translates both ways |
| Hook reply | exit 0/1/2 allow/error/block | `tool_call` block/mutate | Shim |
| Matcher tools | `Shell`, `Write`, `Edit`, `Delete` | `bash`, `write`, `edit` (no `Delete`) | Name mapping |
| Role delegation | none | none (subagent example only) | **No gap** |
| Skills | not installed; assistant cannot load `nw-nwdes` | native, `~/.agents/skills`, `~/.pi/agent/skills` | Pi exceeds Cursor |
| Commands | none | prompt templates | Pi exceeds Cursor |
| Typed reply | none | none | **No gap** |
| Project guidance | assistant told via pasted sentence | `AGENTS.md`, skills | Pi exceeds Cursor |
| Fallback | `nwdes` CLI from shell | same | No gap |
| Verification | installer self-validation only | none | No `pi` platform to validate |
| Host registration list | `HOSTS` includes `cursor` | `HOSTS` lacks `pi` (`registration.py`, `__main__.py`) | Add `pi` |

## Takeaways

- Against the Cursor bar pi already has **everything except installer wiring**: skills, commands, AGENTS.md and the `nwdes` shell fallback all exist natively.
- The only host-side work is the guard hook: `python -m nwave_ai.hooks PreToolUse --host pi`, with `bash`/`write`/`edit` mapped to `Bash`/`Write`/`Edit`.
- This is the cheapest viable pi target: guard + skills + `nwdes` CLI, no role delegation. Role delegation (see `pi-vs-codex-gaps.md`) is the step that lifts it above Cursor.
