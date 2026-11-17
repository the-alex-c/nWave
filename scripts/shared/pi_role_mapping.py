"""Map a Claude Code role file to a pi role file (adr-pi-role-tool-mapping.md).

Never widen: a scoped grant or a tool pi has no equivalent for is dropped and
reported, never approximated.
"""

from __future__ import annotations

import re
from typing import Any

import yaml  # type: ignore[import-untyped, unused-ignore]

from nwave_ai.platform.capability import split_declared_tools
from scripts.shared.frontmatter import parse_frontmatter
from scripts.shared.skill_path_rewrite import rewrite_host_paths


#: The delegation tool a role's `Task` becomes. `subagent` until the `Agent` wrapper
#: ships (ADR decision 1); then this one value changes.
DELEGATION_TOOL = "subagent"

_TOOL_TABLE = {
    "Read": "read",
    "Write": "write",
    "Edit": "edit",
    "Bash": "bash",
    "Grep": "grep",
    "Glob": "find",
    "Task": DELEGATION_TOOL,
    "Agent": DELEGATION_TOOL,
    "WebFetch": "web_fetch",
    "WebSearch": "web_search",
}
#: pi's own names map to themselves, so mapping a mapped role changes nothing.
_MAP = {**{pi: pi for pi in (*_TOOL_TABLE.values(), "ls")}, **_TOOL_TABLE}
_SKILL_INVOKE = re.compile(r"Invoke (?:ONE )?Skill\(([A-Za-z0-9][A-Za-z0-9._-]*)\)")


def submit_tool(role: str) -> str:
    """The typed-reply tool a role answers through."""
    return "submit_" + role.replace("-", "_")


def _entries(declared: object) -> list[str]:
    if isinstance(declared, str):
        return [e.strip() for e in split_declared_tools(declared) if e.strip()]
    if isinstance(declared, list):
        return [str(e).strip() for e in declared if str(e).strip()]
    return []


def _map_tools(name: str, declared: object) -> tuple[list[str], list[str]]:
    submit = submit_tool(name)
    mapped: list[str] = []
    reports: list[str] = []
    for entry in _entries(declared):
        bare = entry.partition("(")[0].strip()
        if bare == submit:
            continue
        if entry != bare:
            reports.append(
                f"{name}: scoped grant '{entry}' has no pi form; capability omitted, not widened"
            )
        elif bare == "Skill":
            reports.append(f"{name}: tool 'Skill' omitted; pi loads skills with read")
        elif bare not in _MAP:
            reports.append(f"{name}: tool '{bare}' has no pi equivalent; omitted")
        elif _MAP[bare] not in mapped:
            mapped.append(_MAP[bare])
    return [*mapped, submit], reports


def to_pi_role(name: str, text: str) -> tuple[str, list[str]]:
    """Return the pi role text and one report line per dropped capability."""
    meta, body = parse_frontmatter(text)
    if meta is None:
        raise ValueError(f"{name}: frontmatter does not parse")
    tools, reports = _map_tools(name, meta.get("tools"))
    projected: dict[str, Any] = {k: v for k, v in meta.items() if k != "model"}
    projected["tools"] = ", ".join(tools)
    body = _SKILL_INVOKE.sub(
        lambda m: f"Read `~/.pi/agent/skills/{m.group(1)}/SKILL.md`", body
    )
    head = yaml.dump(
        projected,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=10**6,
    )
    return f"---\n{head}---\n{rewrite_host_paths(body, 'pi')}", reports
