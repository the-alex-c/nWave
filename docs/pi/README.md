# nWave on pi

Branches `pi-platform-rung-1` to `pi-platform-rung-3` add a `pi` install target for
[pi](https://github.com/earendil-works/pi). It covers three rungs of the host
ladder: skills (Devin), the guard hook (Cursor/Copilot) and delegation with typed
replies (Codex). The gap analysis behind it is in the `pi-vs-*-gaps.md`
files next to this one; `pi-vs-devin-gaps.md` has the ladder. Progress and remaining
work per rung: [TODO-PARITY.md](TODO-PARITY.md), [TODO-RUNG-3.md](TODO-RUNG-3.md).

## What it does

`nwave-ai install --platform pi [--pi-level 1|2|3]` copies the public `nw-*` skills to
`~/.pi/agent/skills/<name>/SKILL.md` (or `$PI_CODING_AGENT_DIR/skills/`) and
writes `.nwave-manifest.json` there.

- **Ownership:** only names in the manifest are replaced, pruned or removed on
  uninstall. A foreign `nw-*` directory aborts the install. Your own non-`nw-`
  skills are never touched.
- **Own root, not `~/.agents/skills/`:** that tree belongs to the Codex plugin, the
  only writer allowed there.
- **Path rewrites:** `~/.claude/...` references in skill bodies become
  `~/.pi/agent/...` (`PI_PATH_REWRITES`).
- **Explicit only:** `--platform pi` must be passed. `auto` does not detect pi.

## Levels

`--pi-level 1|2|3` picks the rung. Each level builds on the one below. You can move
between levels by re-installing.

| Level | Installs | Does not install |
|---|---|---|
| 1 | Skills only. | The guard (pi-code, `PreToolUse` entry, shell-rc block), role agents, delegation, typed replies. |
| 2 | Level 1 + the guard (below). | Role agents, delegation, typed replies. |
| 3 (default) | Level 2 + delegation (below). | |

Re-installing at a lower level removes what the target level would not install on
its own:

- from 3: the role agents (`~/.pi/agent/agents/nw-*.md`), the `pi-code-nwave` package
  entry, and the `subagent` and web extensions from the pi-code filter;
- from 2: nWave's pi-code (only if nWave installed it), the `PreToolUse` hook entry and
  the marked shell-rc block.

Your other `settings.json` keys and a pi-code you installed yourself are kept. At level
1, `verify` does not ask for the guard and fails if a hook entry is still present. The
level is recorded in the skills manifest; standalone `verify` reads it (a manifest
without a level counts as 2, a missing one as 3). Tests: `tests/pi/test_pi_levels.py`.

## Guard (rung 2)

A level 2 install (the default) also sets up the nWave guard, so `git stash`, edits to
`execution-log.json` and similar are blocked before pi runs them.

- **pi-code:** installs pinned [pi-code](https://github.com/ilovepixelart/pi-code)
  with a hooks-only filter at level 2. Level 3 widens the filter (below).
- **Hook entry:** a `PreToolUse` entry in `~/.pi/agent/settings.json` runs
  `python -m nwave_ai.hooks PreToolUse --host pi`. Any failure of the hook blocks
  the call.
- **`CLAUDE_CONFIG_DIR`:** pi-code reads hooks from `$CLAUDE_CONFIG_DIR`. Without it
  the guard fails open and pi says nothing. The installer prints a `pi()` shell
  function that sets it for pi only; on a TTY it offers to add it to your shell rc
  (`--shell-rc yes|no`). `verify` warns when the block or the variable is missing.
- **Uninstall:** removes nWave's pi-code (only if nWave installed it), the hook
  entry, and the marked rc block. pi's other settings are kept.

Decisions: [ADR](research/rung-2/adr-pi-installer-for-rung-2.md) and
[ADR](research/rung-2/adr-pi-code-for-rung-2.md).

## Delegation (rung 3)

Level 3 adds role agents, an `Agent` tool and typed replies.

- **Role agents:** every public role in `nWave/agents/` becomes
  `~/.pi/agent/agents/nw-*.md`. `pi_role_mapping.py` translates Claude tools to pi
  tools (`Task`/`Agent` to `Agent`, `WebFetch`/`WebSearch` to `web_fetch`/`web_search`,
  skill invocations to a `Read` of the pi skill path) and drops what has no pi
  equivalent (`SendMessage`, `model`, scoped grants), never widening a grant.
  `pi_role_validation.py` checks every role (frontmatter, `tools:`, `skills:`) and
  lists all failures at once. If any role fails, the target is left untouched.
  The plugin owns its files through the manifest and refuses a foreign `nw-*.md`.
- **`pi-code-nwave`:** a small pi package in this repo, loaded by local path. It
  registers `Agent(subagent_type, prompt)`, which delegates to pi-code's `subagent` and
  hides `subagent` from the model. The roster text is rewritten to match. A child
  failure comes back as a typed `Agent failed (<kind>): <detail>` with `isError:true`.
- **Typed replies:** one `submit_<role>` tool per installed `nw-*` agent, generated from
  `role_envelope_schemas.json` (roles without their own schema get the floor schema).
  A child with no valid submit is a typed failure (`envelope`); there is no prose
  parsing and no nudge. A child stopped at `maxTurns` is ok with `partial: true`.
- **Models:** children are not pinned to the parent's model. `model: inherit` runs on
  pi's default model (or `CLAUDE_CODE_SUBAGENT_MODEL`). A bad default fails typed.

Decisions: [delegation ADR](research/rung-3/adr-pi-delegation-for-rung-3.md),
[role-tool mapping ADR](research/rung-3/adr-pi-role-tool-mapping.md),
[session format ADR](research/rung-3/adr-pi-session-format.md).
Evidence: `research/rung-3/`.

At levels 1 and 2 there are no role agents or delegation: skills run as methodology
guidance and `nwdes` is used from the shell.

## Code map

| Change | File |
|---|---|
| Plugin (copy of the Devin plugin, pi names and paths) | `scripts/install/plugins/pi_skills_plugin.py` |
| `pi_config_dir()`, `pi_skills_dir()` | `scripts/shared/install_paths.py` |
| `PI_PATH_REWRITES` and its exception list | `scripts/shared/platform_contracts.py`, `scripts/shared/skill_path_rewrite.py` |
| pi-code install, per-level filter and ownership marker | `scripts/shared/pi_code_package.py` |
| Levels (`--pi-level`), recorded level | `scripts/shared/pi_options.py` |
| Role agents plugin (level 3) | `scripts/install/plugins/pi_agents_plugin.py` |
| Claude role to pi role mapping and validation | `scripts/shared/pi_role_mapping.py`, `scripts/shared/pi_role_validation.py` |
| `pi-code-nwave` package entry (ownership marker) | `scripts/shared/pi_nwave_package.py` |
| `Agent` wrapper, `submit_<role>` tools, failure classifier | `pi-code-nwave/extensions/` |
| Committed copy of the role envelope schemas | `pi-code-nwave/role_envelope_schemas.json` |
| `pi()` shell-rc block | `scripts/shared/pi_shell_rc.py` |
| `pi` host and `PreToolUse` entry for pi | `nwave_ai/hooks/__main__.py`, `nwave_ai/hooks/registration.py` |
| `--platform pi` registration | `scripts/install/install_nwave.py` |
| Verify / uninstall | `scripts/install/verify_nwave.py`, `scripts/install/uninstall_nwave.py` |
| `.gitignore`: `pi/` anchored to `/pi/` so `tests/pi/` is not ignored | `.gitignore` |

## Tests

```
make test-py                    # all of tests/
make test-py ARGS="-k discovers"   # filter
make test-js                    # pi-code-nwave (vitest)
```

- `tests/pi/test_pi_skills_plugin.py` checks the installer: skills and manifest
  written, verify passes, foreign `nw-*` refused, uninstall removes only owned
  skills, path rewrite, `pi` offered as a platform choice.
- `tests/pi/test_pi_discovers_skills.py` checks the installed skills against a real
  `pi` process. It runs `pi --offline --no-session --mode rpc`, sends
  `get_commands`, and compares the `skill:*` entries to the manifest. No LLM or
  network. It is skipped when `pi` is not on PATH.

- `tests/pi/test_pi_guard_install.py`, `test_pi_shell_rc*.py` and
  `test_pi_hook_host.py` check the guard install, the rc block and the `pi` host.
- `tests/pi/test_pi_guard_round_trip.py` runs the installed hook command with
  pi-shaped payloads against the real `nwave_ai.hooks`.
- `tests/pi/test_pi_guard_real_pi.py` runs a real pi turn and checks the guard
  blocks. Opt-in: `NWAVE_PI_E2E=1` (needs network, a pi login and an LLM).
- `tests/pi/test_pi_levels.py` covers moving between levels 1, 2 and 3.
- `tests/pi/test_pi_role_mapping.py`, `test_pi_role_validation.py` and
  `test_pi_all_roles.py` check the role mapping and validate every shipped role.
- `tests/pi/test_pi_agents_plugin.py`, `test_pi_agents_wiring.py`,
  `test_pi_nwave_package.py` and `test_pi_nwave_ext_install.py` check the agents
  plugin, its wiring and the `pi-code-nwave` package entry.
- `pi-code-nwave/tests/` (`make test-js`) checks `Agent`, `classify` and `submit`.
- `tests/pi/test_pi_delegation_real_pi.py` runs `Agent` to an installed role against a
  real pi and checks the envelope and uninstall. Opt-in: `NWAVE_PI_E2E=1`. Re-run it
  when `pi_code_package.SOURCE` changes.

`uv run` creates an untracked `uv.lock`; delete it, it is not part of the change.

## Installing your build

```
make install                    # pipx install --force .   (the nwave-ai CLI from this repo)
make upgrade                    # install, then nwave-ai install --platform pi
make upgrade PLATFORM=claude-code
```

When running the installer scripts straight from a checkout, set `PYTHONPATH=.`.
Otherwise they import the copy in the venv's `site-packages` and can fail on
version resolution.

## Open

- Whether `auto` should detect pi.
- The session format for `nwdes measure` is decided but not verified live in pi.
- The pi plugin duplicates the Devin plugin. A shared base would shrink the diff
  if this is upstreamed.
- Guard: inactive-repo behaviour and an orphaned hook child after a timeout are
  untested.
- Delegation: no nudge or re-spawn when a child gives no valid `submit`; wall-clock
  cap is unmeasured; the roster rewrite depends on pi-code's intro wording and is not
  asserted live.
- Next rungs: see the gap files and [TODO-PARITY.md](TODO-PARITY.md).
