"""Role mapping: Claude Code role text -> pi role text.

Decisions: docs/pi/research/rung-3/adr-pi-role-tool-mapping.md (all accepted).
Pure function `to_pi_role(name, text) -> (text, reports)`; the generator writes the
text and prints the reports, the validator checks the text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.shared.frontmatter import parse_frontmatter
from scripts.shared.pi_role_mapping import to_pi_role
from scripts.shared.pi_role_validation import validate_role


def _source(
    tools: str = "Read, Write, Edit, Bash, Glob, Grep, SendMessage",
    body: str = "Read `~/.claude/skills/nw-have/SKILL.md` first.\n",
) -> str:
    return (
        "---\nname: nw-x\ndescription: Does x.\nmodel: claude-opus-5\nmaxTurns: 40\n"
        f"tools: {tools}\nskills:\n  - nw-have\n---\n{body}"
    )


def _map(text: str | None = None) -> tuple[dict[str, Any], str, list[str]]:
    out, reports = to_pi_role("nw-x", text or _source())
    meta, body = parse_frontmatter(out)
    assert meta is not None
    return meta, body, reports


def _tools(meta: dict[str, Any]) -> set[str]:
    return {t.strip() for t in str(meta["tools"]).split(",")}


# -- frontmatter ------------------------------------------------------------


def test_model_dropped_maxturns_name_description_skills_kept() -> None:
    meta, _, _ = _map()
    assert "model" not in meta
    assert (meta["maxTurns"], meta["name"], meta["description"]) == (
        40,
        "nw-x",
        "Does x.",
    )
    assert meta["skills"] == ["nw-have"]


# -- ADR 1-3: the tool table ------------------------------------------------


@pytest.mark.parametrize(
    ("claude", "pi"),
    [
        ("Read", "read"),
        ("Write", "write"),
        ("Edit", "edit"),
        ("Bash", "bash"),
        ("Grep", "grep"),
        ("Glob", "find"),
        ("Task", "subagent"),
        ("Agent", "subagent"),
        ("WebFetch", "web_fetch"),
        ("WebSearch", "web_search"),
    ],
)
def test_tool_table(claude: str, pi: str) -> None:
    meta, _, reports = _map(_source(tools=claude))
    assert _tools(meta) == {pi, "submit_nw_x"}
    assert reports == []


def test_yaml_list_tools_map_the_same() -> None:
    meta, _, _ = _map(_source(tools="[Read, Glob, Task, SendMessage]"))
    assert _tools(meta) == {"read", "find", "subagent", "submit_nw_x"}


def test_duplicates_collapse() -> None:
    meta, _, _ = _map(_source(tools="Task, Agent, Read"))
    assert str(meta["tools"]).count("subagent") == 1


# -- ADR 2: Skill ------------------------------------------------------------


def test_skill_tool_is_dropped_with_a_report() -> None:
    meta, _, reports = _map(_source(tools="Read, Skill"))
    assert _tools(meta) == {"read", "submit_nw_x"}
    assert any("Skill" in r for r in reports)


@pytest.mark.parametrize(
    "directive", ["Invoke Skill(nw-have)", "Invoke ONE Skill(nw-have)"]
)
def test_invoke_skill_becomes_a_read_of_the_pi_path(directive: str) -> None:
    _, body, _ = _map(_source(body=f"{directive} ON-TRIGGER — x\n"))
    assert "Read `~/.pi/agent/skills/nw-have/SKILL.md` ON-TRIGGER — x" in body
    assert "Invoke" not in body


def test_claude_paths_rewritten_to_pi_root() -> None:
    _, body, _ = _map()
    assert "~/.pi/agent/skills/nw-have/SKILL.md" in body
    assert "~/.claude" not in body


# -- ADR 4: never widen, report every drop -----------------------------------


def test_sendmessage_is_dropped_with_a_report() -> None:
    meta, _, reports = _map()
    assert "SendMessage" not in str(meta["tools"])
    assert any("SendMessage" in r for r in reports)


def test_scoped_grant_is_dropped_not_widened() -> None:
    meta, _, reports = _map(_source(tools="Read, Bash(git log:*)"))
    assert _tools(meta) == {"read", "submit_nw_x"}
    assert any("Bash(git log:*)" in r for r in reports)


def test_unknown_tool_is_dropped_with_a_report() -> None:
    meta, _, reports = _map(_source(tools="Read, FrobnicateTool"))
    assert _tools(meta) == {"read", "submit_nw_x"}
    assert any("FrobnicateTool" in r for r in reports)


def test_reports_name_the_role() -> None:
    _, _, reports = _map()
    assert reports and all("nw-x" in r for r in reports)


# -- composition --------------------------------------------------------------


def test_mapped_role_passes_validation(tmp_path: Path) -> None:
    (tmp_path / "nw-have").mkdir()
    (tmp_path / "nw-have" / "SKILL.md").write_text("x")
    text, _ = to_pi_role(
        "nw-x", _source(tools="Read, Task, WebFetch, WebSearch, Skill")
    )
    assert validate_role("nw-x", text, tmp_path).errors == []


def test_mapping_is_idempotent_on_its_own_output() -> None:
    once, _ = to_pi_role("nw-x", _source(tools="Read, Task, WebFetch"))
    twice, reports = to_pi_role("nw-x", once)
    assert twice == once
    assert reports == []
