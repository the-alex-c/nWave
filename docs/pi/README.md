# nWave on pi

Branch `pi-platform-skills` adds a `pi` install target for
[pi](https://github.com/earendil-works/pi). It sits on the lowest rung of the host
ladder (Devin: skills only). The gap analysis behind it is in the `pi-vs-*-gaps.md`
files next to this one; `pi-vs-devin-gaps.md` has the ladder. Progress and remaining
work per rung: [TODO.md](TODO.md).

## What it does

`nwave-ai install --platform pi` copies the public `nw-*` skills to
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

Not included: hooks, role agents, delegation, typed replies. Pi has no
equivalent of the Codex/OMP/Claude role machinery that nWave could use yet, so
skills run as methodology guidance and `nwdes` is used from the shell.

## Code map

| Change | File |
|---|---|
| Plugin (copy of the Devin plugin, pi names and paths) | `scripts/install/plugins/pi_skills_plugin.py` |
| `pi_config_dir()`, `pi_skills_dir()` | `scripts/shared/install_paths.py` |
| `PI_PATH_REWRITES` and its exception list | `scripts/shared/platform_contracts.py`, `scripts/shared/skill_path_rewrite.py` |
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
- Tool-ceiling enforcement, model inheritance and the session format for
  `nwdes measure` are unverified in pi.
- The pi plugin duplicates the Devin plugin. A shared base would shrink the diff
  if this is upstreamed.
- Next rungs: a guard extension in a separate `nwave-pi` repo (Cursor/Copilot),
  then role registry, delegation and typed reply (Codex). See `HANDOFF.md` and the
  gap files.
