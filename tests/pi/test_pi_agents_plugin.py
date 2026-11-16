import json
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


def _snapshot(d: Path) -> dict[str, str]:
    return {p.name: p.read_text() for p in sorted(d.iterdir())}


def test_reinstall_is_idempotent(pi_dir: Path, ctx: InstallContext) -> None:
    assert PiSkillsPlugin().install(ctx).success
    assert plugin.PiAgentsPlugin().install(ctx).success
    first = _snapshot(pi_dir / "agents")
    assert plugin.PiAgentsPlugin().install(ctx).success
    assert _snapshot(pi_dir / "agents") == first


def test_reinstall_prunes_owned_role_dropped_from_source(
    pi_dir: Path, ctx: InstallContext
) -> None:
    assert PiSkillsPlugin().install(ctx).success
    assert plugin.PiAgentsPlugin().install(ctx).success
    agents = pi_dir / "agents"
    manifest = agents / ".nwave-agents-manifest.json"
    doc = json.loads(manifest.read_text())
    doc["installed_agents"].append("nw-gone")
    manifest.write_text(json.dumps(doc))
    (agents / "nw-gone.md").write_text("stale")
    assert plugin.PiAgentsPlugin().install(ctx).success
    assert not (agents / "nw-gone.md").exists()


def test_foreign_role_file_is_refused_and_untouched(
    pi_dir: Path, ctx: InstallContext
) -> None:
    assert PiSkillsPlugin().install(ctx).success
    foreign = pi_dir / "agents" / "nw-acceptance-designer.md"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("user's own")
    result = plugin.PiAgentsPlugin().install(ctx)
    assert not result.success
    assert foreign.read_text() == "user's own"
    assert [p.name for p in foreign.parent.iterdir()] == [foreign.name]


def _agents_at(ctx: InstallContext, level: int) -> None:
    ctx.metadata["pi_level"] = level
    assert PiSkillsPlugin().install(ctx).success
    assert plugin.PiAgentsPlugin().install(ctx).success


def test_below_level_3_installs_no_agents(pi_dir: Path, ctx: InstallContext) -> None:
    _agents_at(ctx, 2)
    assert not (pi_dir / "agents").exists()


def test_reinstall_at_level_2_removes_owned_agents_keeps_users(
    pi_dir: Path, ctx: InstallContext
) -> None:
    _agents_at(ctx, 3)
    (pi_dir / "agents" / "my-own.md").write_text("mine")
    _agents_at(ctx, 2)
    assert [p.name for p in (pi_dir / "agents").iterdir()] == ["my-own.md"]


def test_verify_below_level_3_does_not_demand_agents(
    pi_dir: Path, ctx: InstallContext
) -> None:
    _agents_at(ctx, 2)
    ctx.metadata.pop("pi_level")
    assert plugin.PiAgentsPlugin().verify(ctx).success


def test_verify_at_level_3_demands_agents(pi_dir: Path, ctx: InstallContext) -> None:
    _agents_at(ctx, 3)
    ctx.metadata.pop("pi_level")
    (pi_dir / "agents" / "nw-acceptance-designer.md").unlink()
    assert not plugin.PiAgentsPlugin().verify(ctx).success
