from pathlib import Path

from scripts.install.plugins.base import InstallContext
from scripts.install.plugins.pi_agents_plugin import PiAgentsPlugin
from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin
from scripts.shared.frontmatter import parse_frontmatter


def test_install_writes_mapped_role(pi_dir: Path, ctx: InstallContext) -> None:
    assert PiSkillsPlugin().install(ctx).success
    result = PiAgentsPlugin().install(ctx)
    assert result.success, result.errors
    role = pi_dir / "agents" / "nw-acceptance-designer.md"
    meta, _ = parse_frontmatter(role.read_text())
    assert meta is not None
    assert meta["name"] == "nw-acceptance-designer"
    assert "model" not in meta
