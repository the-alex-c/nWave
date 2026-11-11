"""pi-code, hooks module only: the pi extension that runs nWave's PreToolUse guard.

nWave installs it through ``pi install`` and records ownership in a marker file. An
existing pi-code the user installed is left as is, and never removed.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


SOURCE = "npm:pi-code@1.7.0"
FILTER = ["extensions/hooks/index.ts"]
MARKER = ".nwave-pi-code.json"
_NAME = re.compile(r"^npm:pi-code(@.+)?$")

which = shutil.which

MAX_LEVEL = 2


def level(metadata: dict[str, Any]) -> int:
    """Install rung: 1 = skills, 2 = skills + guard (default: highest)."""
    return int(metadata.get("pi_level") or MAX_LEVEL)


def verify_level(metadata: dict[str, Any]) -> int:
    """Level to verify: explicit, else the one recorded in the skills manifest, else highest."""
    from scripts.shared.install_paths import pi_skills_dir

    if metadata.get("pi_level"):
        return level(metadata)
    try:
        recorded = json.loads((pi_skills_dir() / ".nwave-manifest.json").read_text(encoding="utf-8"))["level"]
    except (OSError, ValueError, KeyError, TypeError):
        return MAX_LEVEL
    return recorded if recorded in (1, MAX_LEVEL) else MAX_LEVEL


def _run(args: list[str]) -> None:
    subprocess.run(["pi", *args], check=True, timeout=300)


def _load(settings: Path) -> dict[str, Any]:
    return json.loads(settings.read_text(encoding="utf-8")) if settings.is_file() else {}


def _source(entry: Any) -> str | None:
    return entry.get("source") if isinstance(entry, dict) else entry


def _find(document: dict[str, Any]) -> Any:
    for entry in document.get("packages", []):
        source = _source(entry)
        if isinstance(source, str) and _NAME.match(source):
            return entry
    return None


def _canonical(entry: Any) -> bool:
    return isinstance(entry, dict) and entry == {"source": SOURCE, "extensions": FILTER}


def _marker(pi_dir: Path) -> Path:
    return pi_dir / MARKER


def ensure(pi_dir: Path, log) -> None:
    """Install pinned, filtered pi-code unless the user already has one."""
    settings = pi_dir / "settings.json"
    entry = _find(_load(settings))
    owned = _marker(pi_dir).is_file()
    if entry is not None and not owned:
        if not _canonical(entry):
            log.info(f"  ⚠️ pi-code already installed, left as is: {_source(entry)}")
        return
    if entry is not None and _canonical(entry):
        return
    if which("pi") is None:
        log.info(f"  ⚠️ pi not on PATH: run `pi install {SOURCE}` and filter it to {FILTER}")
        return
    if entry is not None:
        remove(pi_dir, log)
    _run(["install", SOURCE])
    _marker(pi_dir).write_text(json.dumps({"source": SOURCE}) + "\n", encoding="utf-8")
    document = _load(settings)
    document["packages"] = [
        {"source": SOURCE, "extensions": FILTER} if _source(e) == SOURCE else e
        for e in document.get("packages", [])
    ]
    settings.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def remove(pi_dir: Path, log) -> None:
    """Remove pi-code only when nWave installed it."""
    marker = _marker(pi_dir)
    if not marker.is_file():
        return
    source = json.loads(marker.read_text(encoding="utf-8"))["source"]
    if which("pi") is None:
        log.info(f"  ⚠️ pi not on PATH: run `pi remove {source}` yourself")
        return
    _run(["remove", source])
    marker.unlink()


def check(pi_dir: Path) -> tuple[list[str], list[str]]:
    """(errors, warnings): a deviating pi-code is an error only when nWave owns it."""
    entry = _find(_load(pi_dir / "settings.json"))
    if entry is None:
        return [f"pi-code not in {pi_dir / 'settings.json'}: the guard is not loaded"], []
    if _canonical(entry):
        return [], []
    problem = f"pi-code is {_source(entry)}, nWave expects {SOURCE} filtered to {FILTER}"
    return ([problem], []) if _marker(pi_dir).is_file() else ([], [problem])
