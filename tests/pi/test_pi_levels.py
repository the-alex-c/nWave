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
from tests.pi.conftest import PiBoth as PiSkillsPlugin
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
    doc = (
        json.loads((pi_dir / "settings.json").read_text())
        if (pi_dir / "settings.json").is_file()
        else {}
    )
    return (
        bool(doc.get("hooks", {}).get("PreToolUse")) or (pi_dir / pcp.MARKER).exists()
    )


def test_default_installs_highest_level(pi_dir: Path, ctx: Any) -> None:
    _install(ctx)
    assert _skills(pi_dir) and _guard_present(pi_dir)


def test_level_1_installs_skills_only(
    pi_dir: Path, ctx: Any, pi_calls: list[list[str]]
) -> None:
    _install(ctx, 1)
    assert _skills(pi_dir)
    assert not _guard_present(pi_dir) and pi_calls == []


def test_reinstall_at_level_1_removes_guard_keeps_skills_and_user_settings(
    pi_dir: Path, ctx: Any
) -> None:
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


def test_level_1_never_removes_user_owned_pi_code(
    pi_dir: Path, ctx: Any, pi_calls: list[list[str]]
) -> None:
    pi_dir.mkdir()
    (pi_dir / "settings.json").write_text(json.dumps({"packages": ["npm:pi-code"]}))
    _install(ctx, 1)
    assert pi_calls == []
    assert json.loads((pi_dir / "settings.json").read_text())["packages"] == [
        "npm:pi-code"
    ]


def test_verify_at_level_1_does_not_demand_guard(pi_dir: Path, ctx: Any) -> None:
    _install(ctx, 1)
    assert PiSkillsPlugin().verify(ctx).success
    assert HooksPlugin().verify(ctx).success


def _fresh_verify(ctx: Any) -> list[bool]:
    """Standalone verify: no pi_level metadata, as verify_nwave.py builds it."""
    ctx.metadata.pop("pi_level", None)
    return [PiSkillsPlugin().verify(ctx).success, HooksPlugin().verify(ctx).success]


def test_level_is_recorded_and_standalone_verify_honors_it(
    pi_dir: Path, ctx: Any
) -> None:
    _install(ctx, 1)
    manifest = json.loads((pi_dir / "skills" / ".nwave-manifest.json").read_text())
    assert manifest["level"] == 1
    assert _fresh_verify(ctx) == [True, True]


def test_standalone_verify_at_recorded_level_2_still_demands_guard(
    pi_dir: Path, ctx: Any
) -> None:
    _install(ctx, 2)
    assert _fresh_verify(ctx) == [True, True]
    (pi_dir / "settings.json").write_text("{}")
    assert _fresh_verify(ctx) != [True, True]


def test_reinstall_without_flag_returns_to_highest_level(
    pi_dir: Path, ctx: Any
) -> None:
    _install(ctx, 1)
    ctx.metadata.pop("pi_level")
    _install(ctx)
    assert _guard_present(pi_dir)
    assert (
        json.loads((pi_dir / "skills" / ".nwave-manifest.json").read_text())["level"]
        == 2
    )


def test_manifest_without_level_is_trusted_as_level_2(pi_dir: Path, ctx: Any) -> None:
    _install(ctx, 2)
    path = pi_dir / "skills" / ".nwave-manifest.json"
    manifest = json.loads(path.read_text())
    del manifest["level"]
    path.write_text(json.dumps(manifest))
    assert _fresh_verify(ctx) == [True, True]
    _install(ctx, 2)
