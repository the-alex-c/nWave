# ADR: how the installer wires the rung 2 guard

Date: 2026-11-10. Status: accepted. Follows [adr-pi-code-for-rung-2.md](adr-pi-code-for-rung-2.md).

## Context

The guard needs three things on the user's machine: pi-code installed with the
hooks-only filter, a `PreToolUse` entry in pi's `settings.json`, and
`CLAUDE_CONFIG_DIR=~/.pi/agent` in the pi process. Without the variable the guard
fails open and pi says nothing ([falsifier #7](pi-code-falsifiers.md)).

## Decisions

### 1. nWave owns pi-code only when it installed it

Install pinned `npm:pi-code@1.7.0`, then write the filter into `packages` (`pi install`
has no filter option). Install only if `pi list` lacks pi-code. Ownership is a marker
file `<pi dir>/.nwave-pi-code.json`. Uninstall runs `pi remove` only when it exists. A
changed pin makes nWave remove and reinstall its own copy. An existing pi-code, even
unfiltered, is left alone with a warning. `verify` fails on a missing pi-code, or on a
deviation from the pin or filter in nWave's copy; a user's copy only warns.

- Rejected: record ownership in the skills manifest. Its schema is strict.
- Rejected: replace or fix a user's pi-code. It may be theirs on purpose.

### 2. `CLAUDE_CONFIG_DIR` through a shell function

`pi() { CLAUDE_CONFIG_DIR="$HOME/.pi/agent" command pi "$@"; }`. The installer prints
it, and on a TTY asks to add it to the rc file chosen from `$SHELL` (zsh `~/.zshrc`;
bash `~/.bash_profile` on macOS, `~/.bashrc` on Linux; other shells print only). Marked
block, idempotent, `--shell-rc yes|no`.

- Rejected: global export. Claude Code reads the same variable and its config would
  move.
- Rejected: alias. A function also covers `command pi` and scripts that call `pi`.
- Rejected: set it from inside pi. pi-code's `env` injection needs the variable
  already set ([falsifier #7](pi-code-falsifiers.md)).

### 3. Uninstall strips the block from all candidate rc files

The rc path is not recorded. Uninstall removes the marked block from `.zshrc`,
`.bash_profile` and `.bashrc`.

- Rejected: store the path in the pi manifest. Needs a manifest format change for
  one string.

### 4. `verify` warns about the environment, never fails

`verify` warns when the rc block is missing or `CLAUDE_CONFIG_DIR` is unset in the
current environment.

- Why warn: `--shell-rc no` is a valid choice, and `verify` often runs from a shell
  that is not the one pi starts in.
- Cost: IDE, cron or other-shell launches still fail open, and nothing fails loudly.

## Accepted risks

- Orphaned hook child after a pi-code timeout: not tested.
- Inactive-repo behaviour of the guard: not tested through pi.
- A shell function does not reach pi started by an IDE, cron or a non-interactive
  shell.
