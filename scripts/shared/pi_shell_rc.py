"""Marked shell-rc block that points pi at nWave's config dir (CLAUDE_CONFIG_DIR)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from scripts.shared.pi_options import ShellRc


BEGIN = "# >>> nwave pi >>>"
END = "# <<< nwave pi <<<"
FUNCTION = 'pi() { CLAUDE_CONFIG_DIR="$HOME/.pi/agent" command pi "$@"; }'
_BLOCK = f"{BEGIN}\n{FUNCTION}\n{END}\n"


def rc_path(shell: str, system: str, home: Path) -> Path | None:
    """rc file for a login shell path, or None for shells we only print for."""
    name = Path(shell).name
    if name == "zsh":
        return home / ".zshrc"
    if name == "bash":
        return home / (".bash_profile" if system == "Darwin" else ".bashrc")
    return None


def all_rc_paths(home: Path) -> tuple[Path, ...]:
    """Every rc file rc_path may pick, for cleanup."""
    return tuple(home / name for name in (".zshrc", ".bash_profile", ".bashrc"))


def add_block(rc: Path) -> bool:
    """Append the block once. True when the file changed."""
    text = rc.read_text(encoding="utf-8") if rc.exists() else ""
    if BEGIN in text:
        return False
    sep = "\n" if text and not text.endswith("\n") else ""
    rc.write_text(text + sep + _BLOCK, encoding="utf-8")
    return True


def has_block(rc: Path) -> bool:
    return rc.exists() and BEGIN in rc.read_text(encoding="utf-8")


def remove_block(rc: Path) -> bool:
    """Remove exactly the marked block. True when the file changed.

    An unterminated block is left alone: guessing its end could eat user text.
    """
    if not rc.exists():
        return False
    text = rc.read_text(encoding="utf-8")
    start = text.find(BEGIN)
    end = text.find(END, start) if start != -1 else -1
    if end == -1:
        return False
    stop = text.find("\n", end)
    stop = len(text) if stop == -1 else stop + 1
    rc.write_text(text[:start] + text[stop:], encoding="utf-8")
    return True


def should_add(mode: ShellRc | None, is_tty: bool, ask: Callable[[], bool]) -> bool:
    """--shell-rc yes|no wins; with no flag, ask on a TTY, else print only."""
    if mode is not None:
        return mode == "yes"
    return ask() if is_tty else False
