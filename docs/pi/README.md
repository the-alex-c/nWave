# nWave on pi

Branches `pi-platform-rung-1` and `pi-platform-rung-2` add a `pi` install target for
[pi](https://github.com/earendil-works/pi). It covers the two lowest rungs of the host
ladder: skills (Devin) and the guard hook (Cursor/Copilot). The gap analysis behind it is in the `pi-vs-*-gaps.md`
files next to this one; `pi-vs-devin-gaps.md` has the ladder. Progress and remaining
work per rung: [TODO.md](TODO.md).

## What it does

`nwave-ai install --platform pi [--pi-level 1|2]` copies the public `nw-*` skills to
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

`--pi-level 1|2` picks the rung. Rung 2 builds on rung 1.

| Level | Installs |
|---|---|
| 1 | Skills only. |
| 2 (default) | Level 1 + the guard (below). |

Re-installing at a lower level removes what the target level would not install on
its own: nWave's pi-code (only if nWave installed it), the `PreToolUse` hook entry and
the marked shell-rc block. Your other `settings.json` keys and a pi-code you installed
yourself are kept. At level 1, `verify` does not ask for the guard and fails if a hook
entry is still present. The level is not persisted yet: standalone `verify` assumes 2.
Tests: `tests/pi/test_pi_levels.py`.

## Guard (rung 2)

A level 2 install (the default) also sets up the nWave guard, so `git stash`, edits to
`execution-log.json` and similar are blocked before pi runs them.

- **pi-code:** installs pinned [pi-code](https://github.com/ilovepixelart/pi-code)
  with a hooks-only filter. nWave writes no pi extension.
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

Not included: role agents, delegation, typed replies. Pi has no equivalent of the
Codex/OMP/Claude role machinery that nWave could use yet, so skills run as
methodology guidance and `nwdes` is used from the shell.

## Code map

| Change | File |
|---|---|
| Plugin (copy of the Devin plugin, pi names and paths) | `scripts/install/plugins/pi_skills_plugin.py` |
| `pi_config_dir()`, `pi_skills_dir()` | `scripts/shared/install_paths.py` |
| `PI_PATH_REWRITES` and its exception list | `scripts/shared/platform_contracts.py`, `scripts/shared/skill_path_rewrite.py` |
| pi-code install, filter and ownership marker | `scripts/shared/pi_code_package.py` |
| `pi()` shell-rc block | `scripts/shared/pi_shell_rc.py` |
| `pi` host and `PreToolUse` entry for pi | `nwave_ai/hooks/__main__.py`, `nwave_ai/hooks/registration.py` |
| `--platform pi` registration | `scripts/install/install_nwave.py` |
| Verify / uninstall | `scripts/install/verify_nwave.py`, `scripts/install/uninstall_nwave.py` |
| `.gitignore`: `pi/` anchored to `/pi/` so `tests/pi/` is not ignored | `.gitignore` |

## Tests

```
make test                       # all of tests/
make test ARGS="-k discovers"   # filter
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
- Persist the chosen level so standalone `verify` knows it.
- Tool-ceiling enforcement, model inheritance and the session format for
  `nwdes measure` are unverified in pi.
- The pi plugin duplicates the Devin plugin. A shared base would shrink the diff
  if this is upstreamed.
- Guard: inactive-repo behaviour and an orphaned hook child after a timeout are
  untested.
- Next rungs: role registry, delegation and typed reply (Codex). See the gap files.
