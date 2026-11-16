"""PiAgentsPlugin is wired into install, verify and uninstall."""

import sys
from pathlib import Path

import pytest

from scripts.install import uninstall_nwave
from scripts.install.install_nwave import NWaveInstaller
from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.pi_agents_plugin import PiAgentsPlugin
from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin
from scripts.install.verify_nwave import verify_native_platform


def test_installer_registers_pi_agents_for_pi() -> None:
    registry = NWaveInstaller()._create_plugin_registry(
        silent=True, target_platforms={"pi"}
    )
    assert "pi-agents" in registry.plugins


def test_verify_native_platform_checks_pi_agents(
    pi_dir: Path, ctx: InstallContext
) -> None:
    assert PiSkillsPlugin().install(ctx).success
    assert PiAgentsPlugin().install(ctx).success
    (pi_dir / "agents" / "nw-acceptance-designer.md").unlink()
    results = verify_native_platform("pi", ctx.claude_dir, ctx.logger)
    assert any(not r.success and r.plugin_name == "pi-agents" for r in results)


def test_cli_uninstall_removes_pi_agents(
    ctx: InstallContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    monkeypatch.delenv("PI_CODING_AGENT_DIR", raising=False)
    assert PiSkillsPlugin().install(ctx).success
    assert PiAgentsPlugin().install(ctx).success
    agents = home / ".pi" / "agent" / "agents"
    (agents / "my-own.md").write_text("mine")
    monkeypatch.setattr(sys, "argv", ["uninstall_nwave.py", "--force"])

    assert uninstall_nwave.main() == 0  # type: ignore[no-untyped-call]

    assert [p.name for p in agents.iterdir()] == ["my-own.md"]
