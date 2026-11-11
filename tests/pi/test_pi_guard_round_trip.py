import json
import os
import subprocess

import pytest

from scripts.install.plugins.nwave_hooks_plugin import HooksPlugin


@pytest.fixture
def run_guard(pi_dir, ctx, tmp_path):
    assert HooksPlugin().install(ctx).success
    settings = json.loads((pi_dir / "settings.json").read_text())
    command = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    repo = tmp_path / "repo"
    (repo / ".nwave").mkdir(parents=True)
    (repo / ".nwave" / "config.json").write_text('{"enabled": true}')
    (repo / "execution-log.json").write_text("a")
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=repo, check=True)
    env = {
        **os.environ,
        "HOME": str(tmp_path / "home"),
        "NWAVE_AGENTS_HOME": str(tmp_path / "agents"),
        "CLAUDE_CONFIG_DIR": str(pi_dir),
    }

    def run(tool_name, tool_input):
        payload = {
            "session_id": "s",
            "cwd": str(repo),
            "permission_mode": "default",
            "tool_use_id": "t",
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": tool_input,
        }
        return subprocess.run(
            ["sh", "-c", command], input=json.dumps(payload), capture_output=True, text=True, env=env, cwd=repo
        )

    run.repo = repo
    return run


def test_registered_command_blocks_allows_and_rewrites_pi_payloads(run_guard):
    stash = run_guard("Bash", {"command": "git stash"})
    assert stash.returncode == 2 and '"block"' in stash.stdout

    assert run_guard("Bash", {"command": "echo hi"}).returncode == 0

    commit = run_guard("Bash", {"command": "git commit --allow-empty -m hello"})
    assert commit.returncode == 0
    rewritten = json.loads(commit.stdout.strip().splitlines()[-1])["hookSpecificOutput"]
    assert rewritten["permissionDecision"] == "allow" and "hello" in rewritten["updatedInput"]["command"]

    log = str(run_guard.repo / "execution-log.json")
    for tool, args in (("Write", {"file_path": log, "content": "b"}), ("Edit", {"file_path": log, "old_string": "a", "new_string": "b"})):
        assert run_guard(tool, args).returncode == 2

    ok = run_guard("Write", {"file_path": str(run_guard.repo / "ok.txt"), "content": "fine"})
    assert ok.returncode == 0
