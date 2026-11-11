import json
import subprocess
import sys

from nwave_ai.hooks.registration import entries, merge, without_registrations
from scripts.install.plugins.nwave_hooks_plugin import HooksPlugin
from tests.pi.conftest import PiBoth as PiSkillsPlugin
from scripts.shared import pi_code_package as pcp


def _settings(pi_dir):
    return json.loads((pi_dir / "settings.json").read_text())


def test_hooks_plugin_writes_pi_entry_and_keeps_pi_keys(pi_dir, ctx):
    pi_dir.mkdir()
    (pi_dir / "settings.json").write_text(json.dumps({"defaultModel": "m", "packages": ["x"]}))
    plugin = HooksPlugin()
    assert plugin.install(ctx).success
    doc = _settings(pi_dir)
    assert doc["defaultModel"] == "m" and doc["packages"] == ["x"]
    [group] = doc["hooks"]["PreToolUse"]
    [handler] = group["hooks"]
    assert group["matcher"] == "Bash|Write|Edit" and handler["timeout"] == 30
    assert "--host pi; rc=$?; [ $rc -eq 0 ] || exit 2" in handler["command"]
    assert plugin.install(ctx).success and _settings(pi_dir) == doc
    assert plugin.verify(ctx).success


def test_wrapper_turns_every_failure_into_exit_2(tmp_path):
    for body, expected in (("exit 0", 0), ("exit 1", 2), ("exit 2", 2), ("exit 7", 2)):
        stub = tmp_path / "py"
        stub.write_text(f"#!/bin/sh\n{body}\n")
        stub.chmod(0o755)
        command = entries("pi", str(stub))[0][1]["hooks"][0]["command"]
        assert subprocess.run(["sh", "-c", command]).returncode == expected
    command = entries("pi", str(tmp_path / "missing"))[0][1]["hooks"][0]["command"]
    assert subprocess.run(["sh", "-c", command], capture_output=True).returncode == 2


def test_merge_and_removal_touch_only_pi_entries():
    foreign = {"matcher": "Bash", "hooks": [{"type": "command", "command": "mine"}]}
    doc = {"hooks": {"PreToolUse": [foreign]}, "k": 1}
    merged = merge(doc, "pi", sys.executable)
    assert merged["hooks"]["PreToolUse"][0] == foreign and len(merged["hooks"]["PreToolUse"]) == 2
    assert without_registrations(merged, "pi") == {"hooks": {"PreToolUse": [foreign]}, "k": 1}
    assert without_registrations(merged, "claude") == merged


def test_pi_code_installed_pinned_and_filtered_once(pi_dir, pi_calls):
    pcp.ensure(pi_dir, _Log())
    pcp.ensure(pi_dir, _Log())
    assert pi_calls == [["install", pcp.SOURCE]]
    assert _settings(pi_dir)["packages"] == [{"source": pcp.SOURCE, "extensions": pcp.FILTER}]
    assert pcp.check(pi_dir) == ([], [])
    pcp.remove(pi_dir, _Log())
    assert pi_calls[-1] == ["remove", pcp.SOURCE] and not (pi_dir / pcp.MARKER).exists()


def test_existing_user_pi_code_is_left_alone_and_never_removed(pi_dir, pi_calls):
    pi_dir.mkdir()
    (pi_dir / "settings.json").write_text(json.dumps({"packages": ["npm:pi-code"]}))
    pcp.ensure(pi_dir, _Log())
    pcp.remove(pi_dir, _Log())
    assert pi_calls == [] and not (pi_dir / pcp.MARKER).exists()
    errors, warnings = pcp.check(pi_dir)
    assert errors == [] and len(warnings) == 1


def test_owned_pi_code_with_old_pin_is_replaced(pi_dir, pi_calls):
    pi_dir.mkdir()
    (pi_dir / "settings.json").write_text(json.dumps({"packages": [{"source": "npm:pi-code@1.6.2", "extensions": pcp.FILTER}]}))
    (pi_dir / pcp.MARKER).write_text(json.dumps({"source": "npm:pi-code@1.6.2"}))
    pcp.ensure(pi_dir, _Log())
    assert pi_calls == [["remove", "npm:pi-code@1.6.2"], ["install", pcp.SOURCE]]
    assert pcp.check(pi_dir) == ([], [])


def test_skills_plugin_installs_verifies_and_uninstalls_guard_extension(pi_dir, ctx, pi_calls):
    plugin = PiSkillsPlugin()
    assert plugin.install(ctx).success and plugin.verify(ctx).success
    (pi_dir / "settings.json").write_text(json.dumps({"packages": []}))
    assert not plugin.verify(ctx).success
    (pi_dir / "settings.json").write_text(json.dumps({"packages": [pcp.SOURCE]}))
    assert not plugin.verify(ctx).success
    assert plugin.uninstall(ctx).success
    assert pi_calls[-1] == ["remove", pcp.SOURCE]


class _Log:
    def info(self, message):
        pass
