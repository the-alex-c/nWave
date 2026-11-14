"""Validation of generated pi role files (TODO-RUNG-3, Validation; ADR 4).

Checks run on the *generated* role text, before anything is written:
frontmatter parses, `tools:` are pi built-ins or `submit_<role>`, `skills:` exist
under the pi skills dir. Prompt size is reported, never capped. All failures are listed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.shared.pi_role_validation import validate_role, validate_roles


def _role(
    name: str = "nw-x", tools: str = "read, submit_nw_x", skills: tuple[str, ...] = ()
) -> str:
    skill_block = "".join(f"  - {s}\n" for s in skills)
    skills_yaml = f"skills:\n{skill_block}" if skills else ""
    return f"---\nname: {name}\ndescription: d\nmaxTurns: 5\ntools: {tools}\n{skills_yaml}---\nBody.\n"


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    (tmp_path / "skills" / "nw-have").mkdir(parents=True)
    (tmp_path / "skills" / "nw-have" / "SKILL.md").write_text("x")
    return tmp_path / "skills"


def test_valid_role_has_no_errors(skills_dir: Path) -> None:
    report = validate_role("nw-x", _role(skills=("nw-have",)), skills_dir)
    assert report.errors == []
    assert report.prompt_chars > 0


def test_unparseable_frontmatter_is_an_error(skills_dir: Path) -> None:
    assert validate_role("nw-x", "no frontmatter", skills_dir).errors


@pytest.mark.parametrize(
    "tool", ["SendMessage", "Task", "Skill", "WebFetch", "submit_other_role"]
)
def test_unresolved_tool_is_an_error(skills_dir: Path, tool: str) -> None:
    errors = validate_role("nw-x", _role(tools=f"read, {tool}"), skills_dir).errors
    assert any(tool in e for e in errors)


@pytest.mark.parametrize("tool", ["subagent", "web_fetch", "web_search"])
def test_accepted_adr_tools_resolve(skills_dir: Path, tool: str) -> None:
    role = _role(tools=f"read, {tool}, submit_nw_x")
    assert validate_role("nw-x", role, skills_dir).errors == []


def test_missing_skill_is_an_error(skills_dir: Path) -> None:
    errors = validate_role(
        "nw-x", _role(skills=("nw-have", "nw-gone")), skills_dir
    ).errors
    assert any("nw-gone" in e for e in errors) and not any(
        "nw-have" in e for e in errors
    )


def test_all_failures_are_listed_at_once(skills_dir: Path) -> None:
    roles = {
        "nw-a": _role("nw-a", tools="read, SendMessage"),
        "nw-b": _role("nw-b", skills=("nw-gone",)),
        "nw-ok": _role("nw-ok", tools="read, submit_nw_ok"),
    }
    failures = validate_roles(roles, skills_dir)
    assert {f.split(":")[0] for f in failures} == {"nw-a", "nw-b"}
