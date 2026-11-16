"""Plugin for installing nWave roles into pi's ``agents/`` dir (TODO-RUNG-3, Role registry).

Each public role is mapped by ``to_pi_role`` and checked by ``validate_roles``;
any failure writes nothing. Written names are recorded in a manifest.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.agent_catalog import is_public_agent, load_public_agents
from scripts.shared.install_paths import pi_agents_dir, pi_skills_dir
from scripts.shared.pi_options import PiOptions
from scripts.shared.pi_role_mapping import to_pi_role
from scripts.shared.pi_role_validation import validate_roles


_MANIFEST_FILENAME = ".nwave-agents-manifest.json"


def _owned(target: Path) -> list[str]:
    """Plain names the previous install recorded; empty when no trusted manifest."""
    try:
        names = json.loads((target / _MANIFEST_FILENAME).read_text(encoding="utf-8"))[
            "installed_agents"
        ]
    except (OSError, ValueError, KeyError):
        return []
    return [n for n in names if isinstance(n, str) and Path(n).name == n]


class PiAgentsPlugin(InstallationPlugin):
    def __init__(self) -> None:
        super().__init__(name="pi-agents", priority=38)

    def install(self, context: InstallContext) -> PluginResult:
        if not PiOptions.from_metadata(context.metadata).delegation_wanted():
            return self.uninstall(context)
        public = load_public_agents(context.project_root / "nWave")
        roles = {
            p.stem: to_pi_role(p.stem, p.read_text(encoding="utf-8"))[0]
            for p in sorted((context.project_root / "nWave" / "agents").glob("nw-*.md"))
            if is_public_agent(p.name, public)
        }
        errors = validate_roles(roles, pi_skills_dir())
        if errors:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message="pi role validation failed",
                errors=errors,
            )
        target = pi_agents_dir()
        owned = set(_owned(target))
        foreign = [
            f"foreign pi agent file: {target / f'{n}.md'}"
            for n in roles
            if (target / f"{n}.md").exists() and n not in owned
        ]
        if foreign:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message="pi agent collision",
                errors=foreign,
            )
        target.mkdir(parents=True, exist_ok=True)
        for stale in owned - roles.keys():
            (target / f"{stale}.md").unlink(missing_ok=True)
        for name, text in roles.items():
            (target / f"{name}.md").write_text(text, encoding="utf-8")
        (target / _MANIFEST_FILENAME).write_text(
            json.dumps({"installed_agents": sorted(roles), "version": "1.0"}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"pi agents installed ({len(roles)})",
            installed_files=[target / f"{n}.md" for n in roles],
        )

    def verify(self, context: InstallContext) -> PluginResult:
        if not PiOptions.from_metadata(context.metadata).delegation_wanted(
            verifying=True
        ):
            return PluginResult(
                success=True, plugin_name=self.name, message="pi agents not wanted"
            )
        manifest = pi_agents_dir() / _MANIFEST_FILENAME
        try:
            names = json.loads(manifest.read_text(encoding="utf-8"))["installed_agents"]
        except (OSError, ValueError, KeyError):
            names = []
        missing = [n for n in names if not (pi_agents_dir() / f"{n}.md").is_file()]
        return PluginResult(
            success=bool(names) and not missing,
            plugin_name=self.name,
            message="pi agents verified",
            errors=[f"missing: {n}" for n in missing],
        )

    def uninstall(self, context: InstallContext) -> PluginResult:
        target = pi_agents_dir()
        manifest = target / _MANIFEST_FILENAME
        try:
            names = json.loads(manifest.read_text(encoding="utf-8"))["installed_agents"]
        except (OSError, ValueError, KeyError):
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="No pi agents to uninstall (no manifest found)",
            )
        for n in names:
            if Path(n).name == n:
                (target / f"{n}.md").unlink(missing_ok=True)
        manifest.unlink()
        if not any(target.iterdir()):
            target.rmdir()
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"pi agents uninstalled ({len(names)} removed)",
        )
