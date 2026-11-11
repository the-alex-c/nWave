"""pi's PreToolUse guard as one unit: the pi-code extension plus the CLAUDE_CONFIG_DIR shell wrapper.

PiGuardPlugin calls ``apply`` / ``remove`` / ``check``; it knows nothing of either part.
The guard's hook *registration* stays with HooksPlugin (settings.json).
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.shared import pi_code_package, pi_options
from scripts.shared.install_paths import pi_config_dir
from scripts.shared.pi_shell_rc import (
    FUNCTION,
    add_block,
    all_rc_paths,
    has_block,
    rc_path,
    remove_block,
    should_add,
)


if TYPE_CHECKING:
    from scripts.shared.pi_options import PiOptions, ShellRc


def _rc() -> Path | None:
    return rc_path(os.environ.get("SHELL", ""), platform.system(), Path.home())


def _print_wrapper_hint(logger) -> None:
    logger.info(
        f"  ℹ️ Set CLAUDE_CONFIG_DIR for pi with this shell function:\n    {FUNCTION}"
    )


def _offer_shell_rc(rc: Path, mode: ShellRc | None, is_tty: bool, logger) -> None:
    """Add the pi() wrapper to rc when the flag or the user's answer allows."""

    def ask() -> bool:
        return input(f"  Add it to {rc}? [y/N] ").strip().lower() == "y"

    if should_add(mode, is_tty, ask):
        changed = add_block(rc)
        logger.info(f"  ✅ {'Added to' if changed else 'Already in'} {rc}")


def _shell_rc_warnings(rc: Path | None, config_dir_set: bool) -> list[str]:
    """Non-fatal: --shell-rc no is valid, but the guard fails open without CLAUDE_CONFIG_DIR."""
    warnings = []
    if rc is not None and not has_block(rc):
        warnings.append(
            f"pi() wrapper block not in {rc}; the guard fails open unless CLAUDE_CONFIG_DIR is set another way"
        )
    if not config_dir_set:
        warnings.append(
            "CLAUDE_CONFIG_DIR is not set in this environment; pi started from here (IDE, cron, other shell) runs without the guard"
        )
    return warnings


def remove(logger) -> None:
    """Drop the marked block from every rc file we may have written, and nWave's pi-code."""
    for rc in all_rc_paths(Path.home()):
        remove_block(rc)
    pi_code_package.remove(pi_config_dir(), logger)


def apply(options: PiOptions, logger, dry_run: bool) -> None:
    """Level 1 removes the guard and rc block; level 2 installs them."""
    if options.install_level < pi_options.MAX_LEVEL:
        if not dry_run:
            remove(logger)
    else:
        if not dry_run:
            pi_code_package.ensure(pi_config_dir(), logger)
        _print_wrapper_hint(logger)
        rc = _rc()
        if rc is not None and not dry_run:
            _offer_shell_rc(rc, options.shell_rc, sys.stdin.isatty(), logger)


def check(options: PiOptions) -> tuple[list[str], list[str]]:
    """(errors, warnings) for the level being verified; a lowered level has nothing to check."""
    if options.verify_level < pi_options.MAX_LEVEL:
        return [], []
    errors, warnings = pi_code_package.check(pi_config_dir())
    return errors, warnings + _shell_rc_warnings(_rc(), bool(os.environ.get("CLAUDE_CONFIG_DIR")))
