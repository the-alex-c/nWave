"""pi-code-nwave (the ``Agent`` wrapper and ``submit_<role>`` tools) as a pi package, installed by local path.

Like ``pi_code_package``: installed through ``pi install``, ownership recorded in a marker
file, and an entry the user added themselves is left as is and never removed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from scripts.shared import pi_code_package as pcp


if TYPE_CHECKING:
    from pathlib import Path


MARKER = ".nwave-pi-code-nwave.json"


def _present(pi_dir: Path, source: str) -> bool:
    packages = pcp.load_settings(pi_dir / "settings.json").get("packages", [])
    return any(pcp.entry_source(entry) == source for entry in packages)


def ensure(pi_dir: Path, log: Any, source: str) -> None:
    """Install the package unless it is already loaded."""
    if _present(pi_dir, source):
        return
    if not pcp.pi_available():
        log.info(f"  ⚠️ pi not on PATH: run `pi install {source}` yourself")
        return
    pcp.pi_install(source)
    pcp.write_marker(pi_dir / MARKER, source)


def remove(pi_dir: Path, log: Any) -> None:
    """Remove the package only when nWave installed it."""
    pcp.remove_marked(pi_dir / MARKER, log)


def check(pi_dir: Path, source: str) -> list[str]:
    return (
        []
        if _present(pi_dir, source)
        else [f"{source} not in {pi_dir / 'settings.json'}: Agent is not loaded"]
    )
