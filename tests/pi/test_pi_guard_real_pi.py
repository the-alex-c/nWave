"""Real pi + real npm install + real LLM turn: the installed guard blocks and allows.

Opt-in (network, a pi login, a few cents): NWAVE_PI_E2E=1.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.install.plugins.nwave_hooks_plugin import HooksPlugin
from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin


AUTH = Path.home() / ".pi" / "agent" / "auth.json"
pytestmark = pytest.mark.skipif(
    not (os.environ.get("NWAVE_PI_E2E") and shutil.which("pi") and AUTH.is_file()),
    reason="set NWAVE_PI_E2E=1 with pi on PATH and a pi login",
)

PROMPT = (
    "Do these three steps in order, even if one fails, then stop. "
    "1) bash: git stash. 2) bash: touch ok.txt. "
    "3) write tool: write the text b to execution-log.json."
)


@pytest.fixture
def pi_calls():
    """Override the autouse stub: this test runs the real pi CLI."""


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def test_installed_guard_governs_a_real_pi_session(pi_dir, ctx, tmp_path):
    assert PiSkillsPlugin().install(ctx).success
    assert HooksPlugin().install(ctx).success
    (pi_dir / "auth.json").symlink_to(AUTH)

    repo = tmp_path / "repo"
    (repo / ".nwave").mkdir(parents=True)
    (repo / ".nwave" / "config.json").write_text('{"enabled": true}')
    (repo / "execution-log.json").write_text("a")
    (repo / "t.txt").write_text("1")
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "t.txt", "execution-log.json")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    (repo / "t.txt").write_text("dirty")

    env = {
        **os.environ,
        "HOME": str(tmp_path / "home"),
        "PI_CODING_AGENT_DIR": str(pi_dir),
        "CLAUDE_CONFIG_DIR": str(pi_dir),
        "NWAVE_AGENTS_HOME": str(tmp_path / "agents"),
    }
    subprocess.run(
        ["pi", "-p", "--no-session", "--offline", "--model", "anthropic/claude-haiku-4-5", PROMPT],
        cwd=repo, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300,
    )

    assert (repo / "ok.txt").is_file(), "allowed call did not run"
    assert (repo / "t.txt").read_text() == "dirty" and _git(repo, "stash", "list") == ""
    assert (repo / "execution-log.json").read_text() == "a"
