"""Installed skills are visible to a real pi process (no LLM, no network)."""

import json
import os
import shutil
import subprocess

import pytest

from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin


pytestmark = pytest.mark.skipif(shutil.which("pi") is None, reason="pi not on PATH")


def _pi_skill_commands(agent_dir, cwd):
    out = subprocess.run(
        ["pi", "--offline", "--no-session", "--mode", "rpc"],
        input='{"id":"1","type":"get_commands"}\n',
        capture_output=True,
        text=True,
        timeout=60,
        cwd=cwd,
        env={**os.environ, "PI_CODING_AGENT_DIR": str(agent_dir)},
    ).stdout
    reply = next(r for r in map(json.loads, out.splitlines()) if r.get("id") == "1")
    return [c for c in reply["data"]["commands"] if c["source"] == "skill"]


def test_pi_sees_no_nw_skills_before_install(pi_dir, tmp_path):
    pi_dir.mkdir()
    assert _pi_skill_commands(pi_dir, tmp_path) == []


def test_pi_sees_every_installed_nw_skill(pi_dir, ctx, tmp_path):
    assert PiSkillsPlugin().install(ctx).success
    expected = set(
        json.loads((pi_dir / "skills" / ".nwave-manifest.json").read_text())[
            "installed_skills"
        ]
    )
    found = _pi_skill_commands(pi_dir, tmp_path)
    assert {c["name"].removeprefix("skill:") for c in found} == expected
    assert all(
        c["sourceInfo"]["path"].startswith(str(pi_dir / "skills")) for c in found
    )
