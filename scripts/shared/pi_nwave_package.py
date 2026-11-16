"""pi-code-nwave (the ``Agent`` wrapper and ``submit_<role>`` tools) as a pi package, installed by local path.

Like ``pi_code_package``: installed through ``pi install``, ownership recorded in a marker
file, and an entry the user added themselves is left as is and never removed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from scripts.shared import pi_code_package as pcp


if TYPE_CHECKING:
    from pathlib import Path


MARKER = ".nwave-pi-code-nwave.json"


def _present(pi_dir: Path, source: str) -> bool:
    packages = pcp._load(pi_dir / "settings.json").get("packages", [])
    return any(pcp._source(entry) == source for entry in packages)


def ensure(pi_dir: Path, log: Any, source: str) -> None:
    """Install the package unless it is already loaded."""
    if _present(pi_dir, source):
        return
    if pcp._which("pi") is None:
        log.info(f"  ⚠️ pi not on PATH: run `pi install {source}` yourself")
        return
    pcp._run(["install", source])
    pi_dir.mkdir(parents=True, exist_ok=True)
    (pi_dir / MARKER).write_text(
        json.dumps({"source": source}) + "\n", encoding="utf-8"
    )


def remove(pi_dir: Path, log: Any) -> None:
    """Remove the package only when nWave installed it."""
    marker = pi_dir / MARKER
    if not marker.is_file():
        return
    try:
        source = json.loads(marker.read_text(encoding="utf-8"))["source"]
    except (ValueError, KeyError, TypeError):
        log.info(f"  ⚠️ unreadable {marker}: left as is")
        return
    if pcp._which("pi") is None:
        log.info(f"  ⚠️ pi not on PATH: run `pi remove {source}` yourself")
        return
    pcp._run(["remove", source])
    marker.unlink()


def check(pi_dir: Path, source: str) -> list[str]:
    return (
        []
        if _present(pi_dir, source)
        else [f"{source} not in {pi_dir / 'settings.json'}: Agent is not loaded"]
    )
