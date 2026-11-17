"""PiAgentsPlugin also loads pi-code-nwave (Agent + submit_<role>) into pi, at level 3 only."""

import json
from pathlib import Path

import pytest

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.pi_agents_plugin import PiAgentsPlugin
from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin
from scripts.shared import pi_code_package as pcp


PKG = str(Path(__file__).resolve().parents[2] / "pi-code-nwave")


def _packages(pi_dir: Path) -> list[str]:
    settings = pi_dir / "settings.json"
    doc = json.loads(settings.read_text()) if settings.is_file() else {}
    sources = (pcp.entry_source(p) for p in doc.get("packages", []))
    return [s for s in sources if s is not None]


def _install(ctx: InstallContext, level: int | None = None) -> None:
    if level is not None:
        ctx.metadata["pi_level"] = level
    assert PiSkillsPlugin().install(ctx).success
    assert PiAgentsPlugin().install(ctx).success


def test_level_3_installs_the_package_by_local_path(
    pi_dir: Path, ctx: InstallContext, pi_calls: list[list[str]]
) -> None:
    _install(ctx, 3)
    assert pi_calls == [["install", PKG]]
    assert _packages(pi_dir) == [PKG]


def test_reinstall_does_not_reinstall_the_package(
    pi_dir: Path, ctx: InstallContext, pi_calls: list[list[str]]
) -> None:
    _install(ctx, 3)
    _install(ctx, 3)
    assert pi_calls == [["install", PKG]]


def test_reinstall_at_level_2_removes_it_and_keeps_other_packages(
    pi_dir: Path, ctx: InstallContext
) -> None:
    _install(ctx, 3)
    doc = json.loads((pi_dir / "settings.json").read_text())
    doc["packages"].append("npm:other")
    (pi_dir / "settings.json").write_text(json.dumps(doc))
    _install(ctx, 2)
    assert _packages(pi_dir) == ["npm:other"]


def test_uninstall_removes_it(pi_dir: Path, ctx: InstallContext) -> None:
    _install(ctx, 3)
    assert PiAgentsPlugin().uninstall(ctx).success
    assert PKG not in _packages(pi_dir)


def test_user_owned_entry_is_never_removed(pi_dir: Path, ctx: InstallContext) -> None:
    pi_dir.mkdir()
    (pi_dir / "settings.json").write_text(json.dumps({"packages": [PKG]}))
    _install(ctx, 3)
    assert PiAgentsPlugin().uninstall(ctx).success
    assert _packages(pi_dir) == [PKG]


def test_verify_at_level_3_demands_the_package(
    pi_dir: Path, ctx: InstallContext
) -> None:
    _install(ctx, 3)
    assert PiAgentsPlugin().verify(ctx).success
    (pi_dir / "settings.json").write_text("{}")
    assert not PiAgentsPlugin().verify(ctx).success


def test_without_pi_on_path_install_succeeds_with_a_hint(
    pi_dir: Path, ctx: InstallContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pcp, "_which", lambda name: None)
    _install(ctx, 3)
    assert _packages(pi_dir) == []
