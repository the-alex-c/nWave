import subprocess
import sys


def test_hooks_cli_accepts_host_pi():
    r = subprocess.run(
        [sys.executable, "-m", "nwave_ai.hooks", "PreToolUse", "--host", "pi"],
        input='{"tool_name":"Bash","tool_input":{"command":"echo hi"}}',
        capture_output=True,
        text=True,
    )
    assert "invalid choice" not in r.stderr, r.stderr
