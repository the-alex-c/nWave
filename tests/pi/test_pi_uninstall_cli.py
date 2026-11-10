import sys

from scripts.install import uninstall_nwave
from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin


def test_cli_uninstall_removes_default_location_pi_only_install(
    ctx, tmp_path, monkeypatch
):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    monkeypatch.delenv("PI_CODING_AGENT_DIR", raising=False)
    skills = home / ".pi" / "agent" / "skills"
    assert PiSkillsPlugin().install(ctx).success
    assert (skills / ".nwave-manifest.json").is_file()
    (skills / "my-own").mkdir()
    monkeypatch.setattr(sys, "argv", ["uninstall_nwave.py", "--force"])

    assert uninstall_nwave.main() == 0

    assert [p.name for p in skills.iterdir()] == ["my-own"]
