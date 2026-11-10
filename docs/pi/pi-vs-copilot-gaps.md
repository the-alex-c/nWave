# Pi vs Copilot: what Copilot has that pi lacks

Scope: the Copilot integration (`nwave_ai/hooks/registration.py`, `nwave_ai/hooks/__main__.py`,
`docs/guides/vendor-support.md`, README) vs `pi/main`. Source-read only; nothing was executed.
There is no Copilot install guide, and no `copilot_*` plugin under `scripts/install/plugins`.

Copilot, like Cursor, is **hook-only**: no agents, no native skills, no `/nw-*` commands. The assistant is
pointed at the `deliver-feature` guide; `nwdes` from the shell is the fallback.

| Area | Copilot (nWave relies on) | Pi | Gap |
|---|---|---|---|
| Installed assets | `hooks/nwave-hooks.json` in the Copilot config dir | none | No `pi` installer platform |
| Hook file shape | top-level `preToolUse` list (no `hooks` wrapper): `{matcher: ".*", hooks: [{type: "command", bash: <cmd>, timeoutSec: 30}]}` | extension `tool_call` event | Needs Claude-shape shim |
| Matcher | `.*` (every tool); handler filters by `tool_name` | n/a | Handler already filters |
| Hook payload | Claude-shaped JSON on stdin, `--host copilot` | in-process | Shim translates both ways |
| Hook reply | exit 0/1/2 | `tool_call` block/mutate | Shim |
| Role delegation | none | none (subagent example only) | **No gap** |
| Skills | not installed | native, `~/.agents/skills`, `~/.pi/agent/skills` | Pi exceeds Copilot |
| Commands | none | prompt templates | Pi exceeds Copilot |
| Project guidance | assistant told via pasted sentence | `AGENTS.md`, skills | Pi exceeds Copilot |
| Typed reply | none | none | **No gap** |
| Fallback | `nwdes` CLI from shell | same | No gap |
| Verification | installer self-validation; no guide | none | No `pi` platform to validate |
| Host registration list | `HOSTS` includes `copilot` (both files) | `HOSTS` lacks `pi` | Add `pi` |
| Merge logic | `merge()`/removal special-case `copilot` (container is the document root, not `hooks`) | n/a | Pi needs no file merge if the shim is an extension |

## Takeaways

- Same floor as Cursor: the only host-side requirement is the guard hook, with all-tool matching filtered by the handler.
- Pi already exceeds Copilot on skills, commands and `AGENTS.md`.
- Differences from Cursor are cosmetic: hook file location and shape (`bash`/`timeoutSec` vs `command`/`timeout`), and matcher (`.*` vs `Shell|Write|Edit|Delete`). Neither applies to a pi extension.
- Remaining work is the same as for Cursor: the `pi` entry in `HOSTS`, the shim, and an installer platform. Role delegation (see `pi-vs-codex-gaps.md`) is what lifts pi above this floor.
