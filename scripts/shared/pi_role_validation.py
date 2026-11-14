"""Validate a generated pi role file before it is written (TODO-RUNG-3, Validation)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from scripts.shared.frontmatter import parse_frontmatter


if TYPE_CHECKING:
    from pathlib import Path


PI_BUILTINS = frozenset({"read", "bash", "edit", "write", "grep", "find", "ls"})


@dataclass(frozen=True)
class RoleReport:
    errors: list[str] = field(default_factory=list)
    prompt_chars: int = 0


def _names(value: object) -> list[str]:
    if isinstance(value, str):
        return [t for t in re.split(r"[,\s]+", value) if t]
    return [str(t) for t in value] if isinstance(value, list) else []


def validate_role(name: str, text: str, skills_dir: Path) -> RoleReport:
    meta, body = parse_frontmatter(text)
    if meta is None:
        return RoleReport(["frontmatter does not parse"])
    submit = "submit_" + name.replace("-", "_")
    allowed = PI_BUILTINS | {submit}
    errors = [
        f"tool not resolvable: {t}"
        for t in _names(meta.get("tools"))
        if t not in allowed
    ]
    errors += [
        f"skill not found: {s}"
        for s in _names(meta.get("skills"))
        if not (skills_dir / s / "SKILL.md").is_file()
    ]
    return RoleReport(errors, len(body))


def validate_roles(roles: dict[str, str], skills_dir: Path) -> list[str]:
    """All failures across roles, as ``name: message``; empty means install may proceed."""
    return [
        f"{name}: {e}"
        for name, text in roles.items()
        for e in validate_role(name, text, skills_dir).errors
    ]
