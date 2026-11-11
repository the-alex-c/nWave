import pytest

from scripts.install.install_nwave import NWaveInstaller
from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin
from scripts.shared.pi_shell_rc import BEGIN, FUNCTION


@pytest.fixture
def rc(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SHELL", "/bin/zsh")
    return home / ".zshrc"


def test_default_without_tty_prints_function_and_writes_nothing(pi_dir, ctx, rc, caplog):
    caplog.set_level("INFO")
    assert PiSkillsPlugin().install(ctx).success
    assert not rc.exists()
    assert FUNCTION in caplog.text


def test_shell_rc_yes_adds_block_idempotently_and_uninstall_removes_it(pi_dir, ctx, rc):
    rc.write_text("export A=1\n")
    ctx.metadata["pi_shell_rc"] = "yes"
    plugin = PiSkillsPlugin()
    assert plugin.install(ctx).success
    assert plugin.install(ctx).success
    assert rc.read_text().count(BEGIN) == 1
    assert plugin.uninstall(ctx).success
    assert rc.read_text() == "export A=1\n"


def test_shell_rc_no_never_writes(pi_dir, ctx, rc):
    ctx.metadata["pi_shell_rc"] = "no"
    assert PiSkillsPlugin().install(ctx).success
    assert not rc.exists()


def test_unknown_shell_prints_only_even_with_yes(pi_dir, ctx, rc, monkeypatch, tmp_path):
    monkeypatch.setenv("SHELL", "/usr/bin/fish")
    ctx.metadata["pi_shell_rc"] = "yes"
    assert PiSkillsPlugin().install(ctx).success
    assert list(rc.parent.iterdir()) == []


def test_uninstall_removes_block_from_whichever_rc_holds_it(pi_dir, ctx, rc, monkeypatch):
    ctx.metadata["pi_shell_rc"] = "yes"
    PiSkillsPlugin().install(ctx)
    monkeypatch.setenv("SHELL", "/bin/bash")
    assert PiSkillsPlugin().uninstall(ctx).success
    assert BEGIN not in rc.read_text()


def test_install_cli_accepts_shell_rc_flag(monkeypatch):
    import sys

    from scripts.install import install_nwave

    seen = {}
    monkeypatch.setattr(sys, "argv", ["install_nwave.py", "--shell-rc", "yes", "--dry-run", "--platform", "pi"])
    monkeypatch.setattr(install_nwave, "_run_install", lambda args, installer: seen.update(rc=installer.shell_rc) or 0)
    assert install_nwave.main() == 0
    assert seen == {"rc": "yes"}


def test_verify_warns_without_rc_block_or_env_and_stays_green(pi_dir, ctx, rc, monkeypatch, caplog):
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    plugin = PiSkillsPlugin()
    assert plugin.install(ctx).success
    caplog.set_level("INFO")
    assert plugin.verify(ctx).success
    assert "block not in" in caplog.text
    assert "CLAUDE_CONFIG_DIR is not set" in caplog.text


def test_verify_silent_with_rc_block_and_env(pi_dir, ctx, rc, monkeypatch, caplog):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(pi_dir))
    ctx.metadata["pi_shell_rc"] = "yes"
    plugin = PiSkillsPlugin()
    assert plugin.install(ctx).success
    caplog.set_level("INFO")
    assert plugin.verify(ctx).success
    assert "block not in" not in caplog.text
    assert "CLAUDE_CONFIG_DIR is not set" not in caplog.text
