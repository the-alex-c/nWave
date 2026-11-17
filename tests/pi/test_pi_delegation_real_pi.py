"""Real pi + real pi-code + real model: install at level 3, drive `Agent`, uninstall.

Opt-in (network, a pi login, a few cents): NWAVE_PI_E2E=1. Re-run whenever
``pi_code_package.SOURCE`` changes: renamed pi-code fields fail silently in unit tests.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts.install.plugins import pi_agents_plugin
from scripts.install.plugins.pi_agents_plugin import PiAgentsPlugin
from scripts.install.plugins.pi_guard_plugin import PiGuardPlugin
from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin


ROOT = Path(__file__).resolve().parents[2]
AUTH = Path.home() / ".pi" / "agent" / "auth.json"
pytestmark = pytest.mark.skipif(
    not (os.environ.get("NWAVE_PI_E2E") and shutil.which("pi") and AUTH.is_file()),
    reason="set NWAVE_PI_E2E=1 with pi on PATH and a pi login",
)

MODEL = "anthropic/claude-haiku-4-5"


@pytest.fixture
def pi_calls() -> None:
    """Override the autouse stub: this test runs the real pi CLI."""


@pytest.fixture
def live(
    pi_dir: Path, ctx: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, str], Path]:
    home = tmp_path / "home"
    home.mkdir()
    env = {
        **os.environ,
        "HOME": str(home),
        "PI_CODING_AGENT_DIR": str(pi_dir),
        "CLAUDE_CONFIG_DIR": str(pi_dir),
        "NWAVE_AGENTS_HOME": str(tmp_path / "agents"),
        "CLAUDE_CODE_SUBAGENT_MODEL": MODEL,  # `model: inherit` otherwise resolves to pi's default, not --model
    }
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(pi_dir))
    monkeypatch.setenv("NWAVE_AGENTS_HOME", str(tmp_path / "agents"))
    pi_dir.mkdir(parents=True, exist_ok=True)
    (pi_dir / "auth.json").symlink_to(AUTH)
    # As shipped: no node_modules, so typebox and pi's packages must come from pi itself.
    package = tmp_path / "pkg" / "pi-code-nwave"
    shutil.copytree(
        ROOT / "pi-code-nwave",
        package,
        ignore=shutil.ignore_patterns("node_modules", "tests"),
    )
    monkeypatch.setattr(pi_agents_plugin, "_package_source", lambda _ctx: str(package))
    for plugin in (PiGuardPlugin(), PiSkillsPlugin(), PiAgentsPlugin()):
        assert plugin.install(ctx).success
    work = tmp_path / "work"
    work.mkdir()
    return env, work


def run_agent(
    live: tuple[dict[str, str], Path],
    agent: str,
    prompt: str = "Reply with the word done.",
) -> dict[str, Any]:
    """Ask the parent model to call `Agent` once; return the Agent tool's result."""
    env, work = live
    ask = f"Call the Agent tool once with subagent_type {agent} and prompt {prompt!r}. Then stop."
    out = subprocess.run(
        [
            "pi",
            "--mode",
            "json",
            "-p",
            "--no-session",
            "--offline",
            "--model",
            MODEL,
            ask,
        ],
        cwd=work,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=300,
    ).stdout
    events = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    ends = [
        e
        for e in events
        if e["type"] == "tool_execution_end" and e.get("toolName") == "Agent"
    ]
    assert len(ends) == 1, out[-2000:]
    result: dict[str, Any] = ends[0]["result"]
    return result


def write_agent(
    live: tuple[dict[str, str], Path], name: str, front: str, body: str
) -> None:
    agents = Path(live[0]["PI_CODING_AGENT_DIR"]) / "agents"
    (agents / f"{name}.md").write_text(
        f"---\nname: {name}\ndescription: probe\n{front}---\n{body}\n", encoding="utf-8"
    )


def text(result: dict[str, Any]) -> str:
    return "".join(c.get("text", "") for c in result["content"])


def test_unknown_agent_is_a_typed_failure(live: tuple[dict[str, str], Path]) -> None:
    result = run_agent(live, "nw-nonexistent")
    assert result.get("isError") and text(result).startswith(
        "Agent failed (subagent): "
    )


def test_unlaunchable_model_is_a_typed_failure(
    live: tuple[dict[str, str], Path],
) -> None:
    write_agent(
        live, "probe-badmodel", "model: nosuch/model\ntools: read\n", "Say done."
    )
    result = run_agent(live, "probe-badmodel")
    assert result.get("isError") and text(result).startswith(
        "Agent failed (subagent): "
    ), text(result)


def test_child_stopping_on_an_api_error_is_a_typed_failure(
    live: tuple[dict[str, str], Path],
) -> None:
    # A registered model the API answers 404 to (true when written; swap if it becomes available).
    write_agent(
        live,
        "probe-apierror",
        "model: anthropic/claude-opus-4-8\ntools: read\n",
        "Say done.",
    )
    result = run_agent(live, "probe-apierror")
    assert result.get("isError") and text(result).startswith(
        ("Agent failed (stop): ", "Agent failed (exit): ")
    ), text(result)


def test_maxturns_capped_child_is_ok_and_partial(
    live: tuple[dict[str, str], Path],
) -> None:
    write_agent(
        live,
        "probe-capped",
        "maxTurns: 1\ntools: bash\n",
        "Run these bash commands one per call: echo a, echo b, echo c.",
    )
    result = run_agent(live, "probe-capped", "Go.")
    assert not result.get("isError"), text(result)
    assert result["details"]["partial"] is True


def test_role_without_a_valid_submit_is_an_envelope_failure(
    live: tuple[dict[str, str], Path],
) -> None:
    write_agent(
        live,
        "nw-probe-nosubmit",
        "tools: read\n",
        "Reply in plain text with the word done. Never call a tool.",
    )
    result = run_agent(live, "nw-probe-nosubmit")
    assert result.get("isError") and text(result).startswith(
        "Agent failed (envelope): "
    ), text(result)


def test_role_returns_a_valid_envelope_then_uninstalls_cleanly(
    live: tuple[dict[str, str], Path], ctx: Any, pi_dir: Path
) -> None:
    result = run_agent(
        live,
        "nw-troubleshooter",
        "Do not use other tools. Submit outcome accepted and diagnostic ok.",
    )
    assert not result.get("isError"), text(result)
    envelope = result["details"]["envelope"]
    assert (
        envelope["outcome"] in {"accepted", "rejected", "indeterminate"}
        and "diagnostic" in envelope
    )

    for plugin in (PiAgentsPlugin(), PiSkillsPlugin(), PiGuardPlugin()):
        assert plugin.uninstall(ctx).success
    assert not list((pi_dir / "agents").glob("nw-*.md"))
    assert "pi-code-nwave" not in (pi_dir / "settings.json").read_text()


def test_tool_ceiling_withholds_unlisted_tools(
    live: tuple[dict[str, str], Path],
) -> None:
    """`tools:` is a host-enforced allowlist: bash works only for the role that lists it."""
    work = live[1]
    task = "Run the bash command `touch {m}` and then say done. If you have no bash tool, say nobash."
    write_agent(live, "probe-bash", "tools: bash\n", "Follow the task exactly.")
    write_agent(live, "probe-readonly", "tools: read\n", "Follow the task exactly.")
    run_agent(live, "probe-bash", task.format(m="allowed"))
    assert (work / "allowed").exists(), (
        "control: a role listing bash must be able to run it"
    )
    result = run_agent(live, "probe-readonly", task.format(m="denied"))
    assert not (work / "denied").exists(), text(result)
