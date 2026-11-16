from pathlib import Path

import pytest

from scripts.install.plugins import pi_agents_plugin as plugin
from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin
from scripts.shared.frontmatter import parse_frontmatter
from scripts.shared.pi_role_mapping import to_pi_role


def test_install_writes_mapped_role(pi_dir: Path, ctx: InstallContext) -> None:
    assert PiSkillsPlugin().install(ctx).success
    result = plugin.PiAgentsPlugin().install(ctx)
    assert result.success, result.errors
    role = pi_dir / "agents" / "nw-acceptance-designer.md"
    meta, _ = parse_frontmatter(role.read_text())
    assert meta is not None
    assert meta["name"] == "nw-acceptance-designer"
    assert "model" not in meta


def test_invalid_role_writes_nothing_and_lists_failure(
    pi_dir: Path, ctx: InstallContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert PiSkillsPlugin().install(ctx).success
    real = to_pi_role

    def bad(name: str, text: str) -> tuple[str, list[str]]:
        out, reports = real(name, text)
        if name == "nw-acceptance-designer":
            out = out.replace("tools: ", "tools: bogus_tool, ", 1)
        return out, reports

    monkeypatch.setattr(plugin, "to_pi_role", bad)
    result = plugin.PiAgentsPlugin().install(ctx)
    assert not result.success
    assert "nw-acceptance-designer: tool not resolvable: bogus_tool" in result.errors
    assert not (pi_dir / "agents").exists()


def test_uninstall_removes_only_owned(pi_dir: Path, ctx: InstallContext) -> None:
    assert PiSkillsPlugin().install(ctx).success
    assert plugin.PiAgentsPlugin().install(ctx).success
    mine = pi_dir / "agents" / "my-own.md"
    mine.write_text("mine")
    assert plugin.PiAgentsPlugin().uninstall(ctx).success
    assert [p.name for p in (pi_dir / "agents").iterdir()] == ["my-own.md"]
