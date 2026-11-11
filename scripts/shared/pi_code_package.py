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

_which = shutil.which


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


def _plan(entry: Any, owned: bool, pi_on_path: bool) -> str:
    """Pure decision: keep | hint | replace | install."""
    if entry is not None and (not owned or _canonical(entry)):
        return "keep"
    if not pi_on_path:
        return "hint"
    return "install" if entry is None else "replace"


def _pin(settings: Path) -> None:
    """Rewrite the installed entry to the pinned, filtered form."""
    document = _load(settings)
    document["packages"] = [
        {"source": SOURCE, "extensions": FILTER} if _source(e) == SOURCE else e
        for e in document.get("packages", [])
    ]
    settings.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def ensure(pi_dir: Path, log) -> None:
    """Install pinned, filtered pi-code unless the user already has one."""
    settings = pi_dir / "settings.json"
    entry = _find(_load(settings))
    owned = _marker(pi_dir).is_file()
    action = _plan(entry, owned, _which("pi") is not None)
    if action == "keep":
        if entry is not None and not owned and not _canonical(entry):
            log.info(f"  ⚠️ pi-code already installed, left as is: {_source(entry)}")
        return
    if action == "hint":
        log.info(f"  ⚠️ pi not on PATH: run `pi install {SOURCE}` and filter it to {FILTER}")
        return
    if action == "replace":
        remove(pi_dir, log)
    _run(["install", SOURCE])
    # Marker before the settings rewrite: a crash between them leaves an owned,
    # non-canonical entry, which the next ensure() replaces.
    pi_dir.mkdir(parents=True, exist_ok=True)
    _marker(pi_dir).write_text(json.dumps({"source": SOURCE}) + "\n", encoding="utf-8")
    _pin(settings)


def remove(pi_dir: Path, log) -> None:
    """Remove pi-code only when nWave installed it."""
    marker = _marker(pi_dir)
    if not marker.is_file():
        return
    try:
        source = json.loads(marker.read_text(encoding="utf-8"))["source"]
    except (ValueError, KeyError, TypeError):
        log.info(f"  ⚠️ unreadable {marker}: left as is")
        return
    if _which("pi") is None:
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
