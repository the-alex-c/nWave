"""Plugin for installing nWave skills into pi's native SKILL.md format.

pi discovers global skills at ``<agent dir>/skills/<name>/SKILL.md`` where the
agent dir is ``~/.pi/agent`` or ``$PI_CODING_AGENT_DIR``. nWave owns that root
through its own manifest rather than the shared ``~/.agents/skills`` tree, which
only the Codex plugin may write.

Ownership is manifest-driven: only names recorded in this plugin's
``.nwave-manifest.json`` are ever replaced or pruned; a foreign or
user-created ``nw-*`` directory is refused as a collision, never adopted, and
non-``nw-`` entries (the user's own skills) are outside this plugin's glob and
untouched by construction.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path
from shutil import which as _which

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared.agent_catalog import (
    build_ownership_map,
    detect_command_skills,
    load_private_skills,
    load_public_agents,
)
from scripts.shared.install_paths import pi_config_dir, pi_skills_dir
from scripts.shared.skill_distribution import (
    enumerate_skills,
    filter_public_skills,
)
from scripts.shared import pi_code_package
from scripts.shared.pi_shell_rc import (
    FUNCTION,
    add_block,
    has_block,
    rc_path,
    remove_block,
    should_add,
)
from scripts.shared.skill_path_rewrite import rewrite_host_paths


_MANIFEST_FILENAME = ".nwave-manifest.json"

_FOREIGN_COLLISION = "foreign or untracked pi skill collision"


def _find_skills_source(context: InstallContext) -> Path | None:
    """Locate the skills source directory from dist or project layout."""
    dist_skills = context.framework_source / "skills" / "nw"
    if dist_skills.exists():
        return dist_skills

    project_skills = context.project_root / "nWave" / "skills"
    if project_skills.exists():
        return project_skills

    return None


def _read_manifest(target_dir: Path) -> dict | None:
    """Read the ownership manifest, or None when absent."""
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _read_owned_manifest_strict(target_dir: Path) -> set[str]:
    """Strictly read the ownership manifest before any mutation.

    A manifest name is an ownership claim only after its own shape is
    trusted: single known key set, version 1.0, safe basenames, unique.

    Raises:
        ValueError: The manifest exists but cannot be trusted.
    """
    manifest_path = target_dir / _MANIFEST_FILENAME
    if not (manifest_path.exists() or manifest_path.is_symlink()):
        return set()
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"unsafe pi skills manifest: {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable pi skills manifest: {manifest_path}") from exc
    names = document.get("installed_skills") if isinstance(document, dict) else None
    safe = (
        isinstance(document, dict)
        and set(document) - {"level"} == {"installed_skills", "version"}
        and document.get("level", 2) in (1, 2)
        and document.get("version") == "1.0"
        and isinstance(names, list)
        and all(_is_plain_skill_name(name) for name in names)
        and len(names) == len(set(names))
    )
    if not safe:
        raise ValueError(f"untrusted pi skills manifest: {manifest_path}")
    return set(names or [])


def _write_manifest(target_dir: Path, installed_skill_names: list[str], level: int) -> None:
    """Write the ownership manifest listing this run's installed skills."""
    manifest = {
        "installed_skills": sorted(installed_skill_names),
        "level": level,
        "version": "1.0",
    }
    manifest_path = target_dir / _MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _is_plain_skill_name(name: object) -> bool:
    """True for one path segment that names a child, never '.' or '..'."""
    return (
        isinstance(name, str)
        and name not in {"", ".", ".."}
        and Path(name).name == name
    )


def _safe_owned_skill_dir(target_dir: Path, name: str) -> Path:
    """Validate a manifest-owned skill directory before replace/remove."""
    if not _is_plain_skill_name(name):
        raise ValueError(f"unsafe pi skill name: {name!r}")
    if target_dir.is_symlink() or not target_dir.is_dir():
        raise ValueError(f"unsafe pi skills directory: {target_dir}")
    skill_dir = target_dir / name
    if skill_dir.parent != target_dir or skill_dir.is_symlink():
        raise ValueError(f"unsafe pi skill directory: {skill_dir}")
    return skill_dir


def _setup_shell_rc(context: InstallContext) -> None:
    """Print the pi() wrapper; add it to the shell rc when allowed."""
    context.logger.info(
        f"  ℹ️ Set CLAUDE_CONFIG_DIR for pi with this shell function:\n    {FUNCTION}"
    )
    rc = rc_path(os.environ.get("SHELL", ""), platform.system(), Path.home())
    if rc is None or context.dry_run:
        return
    ask = lambda: input(f"  Add it to {rc}? [y/N] ").strip().lower() == "y"  # noqa: E731
    if should_add(context.metadata.get("pi_shell_rc"), sys.stdin.isatty(), ask):
        changed = add_block(rc)
        context.logger.info(f"  ✅ {'Added to' if changed else 'Already in'} {rc}")


def _shell_rc_warnings() -> list[str]:
    """Non-fatal: --shell-rc no is valid, but the guard fails open without CLAUDE_CONFIG_DIR."""
    warnings = []
    rc = rc_path(os.environ.get("SHELL", ""), platform.system(), Path.home())
    if rc is not None and not has_block(rc):
        warnings.append(f"pi() wrapper block not in {rc}; the guard fails open unless CLAUDE_CONFIG_DIR is set another way")
    if not os.environ.get("CLAUDE_CONFIG_DIR"):
        warnings.append("CLAUDE_CONFIG_DIR is not set in this environment; pi started from here (IDE, cron, other shell) runs without the guard")
    return warnings


def _remove_shell_rc() -> None:
    """Drop the marked block from every rc file we may have written."""
    for name in (".zshrc", ".bash_profile", ".bashrc"):
        remove_block(Path.home() / name)


class PiSkillsPlugin(InstallationPlugin):
    """Plugin for installing nWave skills into the pi native format."""

    def __init__(self) -> None:
        super().__init__(name="pi-skills", priority=37)

    def validate_prerequisites(self, context: InstallContext) -> PluginResult:
        """Check whether pi is present; skip gracefully if not.

        Detection: the pi agent directory exists OR ``pi`` binary in PATH.
        If neither is found, the plugin returns success with a skip message —
        the absence of pi is not an error.
        """
        pi_dir = pi_config_dir()
        pi_binary = _which("pi") is not None
        if (
            "pi" not in context.target_platforms
            and not pi_dir.exists()
            and not pi_binary
        ):
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message="pi not detected, skipping skills installation",
            )

        return PluginResult(
            success=True,
            plugin_name=self.name,
            message="pi prerequisites validated",
        )

    def install(self, context: InstallContext) -> PluginResult:
        """Install public skills from nWave/skills/ into pi's global tree.

        Copies each public skill directory verbatim (pi preserves unknown
        frontmatter keys), rewriting host paths in SKILL.md bodies. A manifest
        tracks installed names; previous manifest names are replaced
        clean-then-write, foreign ``nw-*`` directories are refused, and
        symlinks are never traversed or replaced.
        """
        try:
            prereq = self.validate_prerequisites(context)
            if "skip" in prereq.message.lower():
                return prereq

            context.logger.info("  📦 Installing pi skills...")

            skills_source = _find_skills_source(context)
            if skills_source is None:
                context.logger.info("  ⏭️ No skills directory found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No skills to install (source directory not found)",
                )

            public_agents = (
                set()
                if context.dev_mode
                else load_public_agents(context.project_root / "nWave")
            )
            agents_dir = context.project_root / "nWave" / "agents"
            ownership_map = (
                build_ownership_map(agents_dir) if agents_dir.exists() else {}
            )
            entries = enumerate_skills(skills_source)
            command_skills = (
                set() if context.dev_mode else detect_command_skills(skills_source)
            )
            private_skills = (
                set()
                if context.dev_mode
                else load_private_skills(context.project_root / "nWave")
            )
            entries = filter_public_skills(
                entries,
                public_agents,
                ownership_map,
                command_skills,
                private_skills,
            )

            desired_names = {entry.name for entry in entries}
            target_dir = pi_skills_dir()

            previous_owned = (
                _read_owned_manifest_strict(target_dir)
                if (target_dir.exists() or target_dir.is_symlink())
                else set()
            )

            # Foreign-collision preflight: an nw-* directory this install
            # does not own and will not write is refused, never adopted.
            if target_dir.exists() or target_dir.is_symlink():
                if target_dir.is_symlink() or not target_dir.is_dir():
                    raise ValueError(f"unsafe pi skills directory: {target_dir}")
                for existing in sorted(target_dir.glob("nw-*")):
                    if (
                        existing.name in desired_names
                        or existing.name in previous_owned
                    ):
                        continue
                    raise ValueError(f"{_FOREIGN_COLLISION}: {existing}")

            stale_names = previous_owned - desired_names
            target_dir.mkdir(parents=True, exist_ok=True)

            # Stage every replacement outside the discovery root before any
            # target mutation: a copy/rewrite failure leaves the previous
            # install fully intact.
            staging_root = pi_skills_dir().parent / ".nwave-skills-staging"
            if staging_root.is_symlink() or (
                staging_root.exists() and not staging_root.is_dir()
            ):
                raise ValueError(f"unsafe pi staging directory: {staging_root}")
            shutil.rmtree(staging_root, ignore_errors=True)
            staging_root.mkdir(parents=True)
            try:
                for entry in entries:
                    staged = staging_root / entry.name
                    if entry.source_path.is_dir():
                        shutil.copytree(entry.source_path, staged, symlinks=False)
                        target_file = staged / "SKILL.md"
                    else:
                        staged.mkdir(parents=True)
                        target_file = staged / "SKILL.md"
                        shutil.copy2(entry.source_path, target_file)

                    content = target_file.read_text(encoding="utf-8")
                    rewritten = rewrite_host_paths(content, "pi")
                    if rewritten != content:
                        target_file.write_text(rewritten, encoding="utf-8")

                # Swap phase: replace manifest-owned desired names, then
                # prune stale owned names.
                installed_names: list[str] = []
                installed_files: list[Path] = []
                for entry in entries:
                    skill_dir = _safe_owned_skill_dir(target_dir, entry.name)
                    if skill_dir.exists():
                        if entry.name not in previous_owned:
                            raise ValueError(f"{_FOREIGN_COLLISION}: {skill_dir}")
                        shutil.rmtree(skill_dir)
                    staged = staging_root / entry.name
                    staged.rename(skill_dir)
                    installed_names.append(entry.name)
                    installed_files.append(skill_dir / "SKILL.md")

                for name in sorted(stale_names):
                    shutil.rmtree(_safe_owned_skill_dir(target_dir, name))

                _write_manifest(target_dir, installed_names, pi_code_package.level(context.metadata))
            finally:
                shutil.rmtree(staging_root, ignore_errors=True)

            context.logger.info(
                f"  ✅ pi skills installed ({len(installed_names)} skills)"
            )
            if pi_code_package.level(context.metadata) < 2:
                if not context.dry_run:
                    _remove_shell_rc()
                    pi_code_package.remove(pi_config_dir(), context.logger)
            else:
                if not context.dry_run:
                    pi_code_package.ensure(pi_config_dir(), context.logger)
                _setup_shell_rc(context)
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=(
                    f"pi skills installed successfully ({len(installed_names)} skills)"
                ),
                installed_files=installed_files,
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to install pi skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"pi skills installation failed: {e!s}",
                errors=[str(e)],
            )

    def uninstall(self, context: InstallContext) -> PluginResult:
        """Uninstall only manifest-owned pi skills; everything else stays."""
        try:
            context.logger.info("  🗑️ Uninstalling pi skills...")
            _remove_shell_rc()
            pi_code_package.remove(pi_config_dir(), context.logger)
            target_dir = pi_skills_dir()
            manifest_path = target_dir / _MANIFEST_FILENAME
            if not (manifest_path.exists() or manifest_path.is_symlink()):
                context.logger.info("  ⏭️ No pi skills manifest found, skipping")
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No pi skills to uninstall (no manifest found)",
                )

            names = _read_owned_manifest_strict(target_dir)
            removed = 0
            for name in sorted(names):
                skill_dir = _safe_owned_skill_dir(target_dir, name)
                if not skill_dir.is_dir():
                    continue
                shutil.rmtree(skill_dir)
                removed += 1

            if manifest_path.exists():
                manifest_path.unlink()

            context.logger.info(f"  🗑️ Removed {removed} pi skills")
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"pi skills uninstalled ({removed} removed)",
            )
        except Exception as e:
            context.logger.error(f"  ❌ Failed to uninstall pi skills: {e}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"pi skills uninstallation failed: {e!s}",
                errors=[str(e)],
            )

    def verify(self, context: InstallContext) -> PluginResult:
        """Verify manifest-listed pi skill trees exist and are not symlinks."""
        try:
            context.logger.info("  🔍 Verifying pi skills...")
            target_dir = pi_skills_dir()
            manifest = _read_manifest(target_dir)
            source = _find_skills_source(context)
            if manifest is None and source is None:
                return PluginResult(
                    success=True,
                    plugin_name=self.name,
                    message="No pi skills configured (nothing to verify)",
                )
            if manifest is None:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="pi skills manifest missing after install",
                    errors=[f"No {_MANIFEST_FILENAME} under {target_dir}"],
                )
            missing = []
            for name in manifest.get("installed_skills", []):
                skill_dir = target_dir / str(name)
                skill_file = skill_dir / "SKILL.md"
                if skill_dir.is_symlink() or skill_file.is_symlink():
                    missing.append(f"{name} (symlink)")
                elif not skill_file.is_file():
                    missing.append(name)
            if missing:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message=f"pi skills verification failed ({len(missing)} missing)",
                    errors=[f"missing or invalid: {', '.join(missing)}"],
                )
            lowered = pi_code_package.verify_level(context.metadata) < 2
            errors, warnings = (
                ([], []) if lowered else pi_code_package.check(pi_config_dir())
            )
            for warning in warnings + ([] if lowered else _shell_rc_warnings()):
                context.logger.info(f"  ⚠️ {warning}")
            if errors:
                return PluginResult(
                    success=False,
                    plugin_name=self.name,
                    message="pi guard extension verification failed",
                    errors=errors,
                )
            count = len(manifest.get("installed_skills", []))
            context.logger.info(f"  ✅ Verified {count} pi skills")
            return PluginResult(
                success=True,
                plugin_name=self.name,
                message=f"pi skills verified ({count} present)",
            )
        except Exception as e:
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"pi skills verification failed: {e!s}",
                errors=[str(e)],
            )
