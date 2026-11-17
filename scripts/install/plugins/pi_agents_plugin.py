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
from scripts.shared import pi_nwave_package
from scripts.shared.agent_catalog import is_public_agent, load_public_agents
from scripts.shared.install_paths import pi_agents_dir, pi_config_dir, pi_skills_dir
from scripts.shared.pi_options import PiOptions
from scripts.shared.pi_role_mapping import to_pi_role
from scripts.shared.pi_role_validation import validate_roles
from scripts.shared.plain_name import is_plain_name


_MANIFEST_FILENAME = ".nwave-agents-manifest.json"


def _recorded(target: Path) -> list[str] | None:
    """Names the manifest records, or None when it is missing or unreadable."""
    try:
        return json.loads((target / _MANIFEST_FILENAME).read_text(encoding="utf-8"))[
            "installed_agents"
        ]
    except (OSError, ValueError, KeyError):
        return None


def _owned(target: Path) -> list[str]:
    """Plain names the previous install recorded; empty when no trusted manifest."""
    return [n for n in _recorded(target) or [] if is_plain_name(n)]


def _package_source(context: InstallContext) -> str:
    """The pi-code-nwave directory: bundled in the wheel, else the checkout."""
    bundled = context.framework_source / "pi-code-nwave"
    return str(bundled if bundled.is_dir() else context.project_root / "pi-code-nwave")


def _build_roles(context: InstallContext) -> dict[str, str]:
    """Pi role text for every public nWave agent, by name."""
    agents_dir = context.project_root / "nWave" / "agents"
    public = load_public_agents(context.project_root / "nWave")
    return {
        p.stem: to_pi_role(p.stem, p.read_text(encoding="utf-8"))[0]
        for p in sorted(agents_dir.glob("nw-*.md"))
        if is_public_agent(p.name, public)
    }


def _collisions(target: Path, roles: dict[str, str], owned: set[str]) -> list[str]:
    """Role files that exist in target but are not ours."""
    return [
        f"foreign pi agent file: {target / f'{n}.md'}"
        for n in roles
        if (target / f"{n}.md").exists() and n not in owned
    ]


def _write_roles(target: Path, roles: dict[str, str], owned: set[str]) -> None:
    """Prune stale owned roles, write the current ones, record the manifest."""
    for stale in owned - roles.keys():
        (target / f"{stale}.md").unlink(missing_ok=True)
    for name, text in roles.items():
        (target / f"{name}.md").write_text(text, encoding="utf-8")
    (target / _MANIFEST_FILENAME).write_text(
        json.dumps({"installed_agents": sorted(roles), "version": "1.0"}, indent=2)
        + "\n",
        encoding="utf-8",
    )


class PiAgentsPlugin(InstallationPlugin):
    def __init__(self) -> None:
        super().__init__(name="pi-agents", priority=38)

    def _refused(self, message: str, errors: list[str]) -> PluginResult:
        return PluginResult(
            success=False, plugin_name=self.name, message=message, errors=errors
        )

    def install(self, context: InstallContext) -> PluginResult:
        if not PiOptions.from_metadata(context.metadata).delegation_wanted():
            return self.uninstall(context)
        roles = _build_roles(context)
        errors = validate_roles(roles, pi_skills_dir())
        if errors:
            return self._refused("pi role validation failed", errors)
        target = pi_agents_dir()
        owned = set(_owned(target))
        foreign = _collisions(target, roles, owned)
        if foreign:
            return self._refused("pi agent collision", foreign)
        target.mkdir(parents=True, exist_ok=True)
        pi_nwave_package.ensure(pi_config_dir(), context.logger, _package_source(context))
        _write_roles(target, roles, owned)
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
        target = pi_agents_dir()
        names = _recorded(target) or []
        missing = [n for n in names if not (target / f"{n}.md").is_file()]
        errors = [f"missing: {n}" for n in missing] + pi_nwave_package.check(
            pi_config_dir(), _package_source(context)
        )
        return PluginResult(
            success=bool(names) and not errors,
            plugin_name=self.name,
            message="pi agents verified",
            errors=errors,
        )

    def uninstall(self, context: InstallContext) -> PluginResult:
        pi_nwave_package.remove(pi_config_dir(), context.logger)
        target = pi_agents_dir()
        names = _recorded(target)
        if names is None:
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="No pi agents to uninstall (no manifest found)",
            )
        for n in filter(is_plain_name, names):
            (target / f"{n}.md").unlink(missing_ok=True)
        (target / _MANIFEST_FILENAME).unlink()
        if not any(target.iterdir()):
            target.rmdir()
        return PluginResult(
            success=True,
            plugin_name=self.name,
            message=f"pi agents uninstalled ({len(names)} removed)",
        )
