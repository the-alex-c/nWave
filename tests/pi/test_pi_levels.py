"""Rung selection: level 1 = skills; level 2 (default) = level 1 + guard.

Re-installing at a lower level removes everything the target level would not install.
Level reaches the plugins as ``context.metadata["pi_level"]`` (absent = highest).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.install.plugins.nwave_hooks_plugin import HooksPlugin
from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin
from scripts.shared import pi_code_package as pcp


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()


def _install(ctx: Any, level: int | None = None) -> None:
    if level is not None:
        ctx.metadata["pi_level"] = level
    for plugin in (PiSkillsPlugin(), HooksPlugin()):
        assert plugin.install(ctx).success


def _skills(pi_dir: Path) -> set[str]:
    return {p.name for p in (pi_dir / "skills").glob("nw-*")}


def _guard_present(pi_dir: Path) -> bool:
    doc = json.loads((pi_dir / "settings.json").read_text()) if (pi_dir / "settings.json").is_file() else {}
    return bool(doc.get("hooks", {}).get("PreToolUse")) or (pi_dir / pcp.MARKER).exists()


def test_default_installs_highest_level(pi_dir: Path, ctx: Any) -> None:
    _install(ctx)
    assert _skills(pi_dir) and _guard_present(pi_dir)


def test_level_1_installs_skills_only(pi_dir: Path, ctx: Any, pi_calls: list[list[str]]) -> None:
    _install(ctx, 1)
    assert _skills(pi_dir)
    assert not _guard_present(pi_dir) and pi_calls == []


def test_reinstall_at_level_1_removes_guard_keeps_skills_and_user_settings(pi_dir: Path, ctx: Any) -> None:
    _install(ctx, 2)
    doc = json.loads((pi_dir / "settings.json").read_text())
    doc["defaultModel"] = "mine"
    (pi_dir / "settings.json").write_text(json.dumps(doc))
    skills = _skills(pi_dir)

    _install(ctx, 1)

    assert _skills(pi_dir) == skills
    assert not _guard_present(pi_dir)
    assert json.loads((pi_dir / "settings.json").read_text())["defaultModel"] == "mine"


def test_reinstall_at_level_2_restores_guard(pi_dir: Path, ctx: Any) -> None:
    _install(ctx, 1)
    _install(ctx, 2)
    assert _guard_present(pi_dir)


def test_level_1_never_removes_user_owned_pi_code(pi_dir: Path, ctx: Any, pi_calls: list[list[str]]) -> None:
    pi_dir.mkdir()
    (pi_dir / "settings.json").write_text(json.dumps({"packages": ["npm:pi-code"]}))
    _install(ctx, 1)
    assert pi_calls == []
    assert json.loads((pi_dir / "settings.json").read_text())["packages"] == ["npm:pi-code"]


def test_verify_at_level_1_does_not_demand_guard(pi_dir: Path, ctx: Any) -> None:
    _install(ctx, 1)
    assert PiSkillsPlugin().verify(ctx).success
    assert HooksPlugin().verify(ctx).success
