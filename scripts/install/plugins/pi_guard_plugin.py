"""Plugin for pi's PreToolUse guard: the pi-code extension and the shell wrapper.

Runs before the skills plugin (priority 36 < 37) so a guard failure leaves the
previous skills and manifest untouched. The hook registration stays with HooksPlugin.
"""

from __future__ import annotations

from scripts.install.plugins.base import (
    InstallationPlugin,
    InstallContext,
    PluginResult,
)
from scripts.shared import pi_guard
from scripts.shared.pi_options import PiOptions


class PiGuardPlugin(InstallationPlugin):
    """Installs, removes and verifies the guard at the requested pi level."""

    def __init__(self) -> None:
        super().__init__(name="pi-guard", priority=36)

    def _run(self, context: InstallContext, what: str, action) -> PluginResult:
        try:
            errors = action() or []
        except Exception as e:
            errors = [str(e)]
        if errors:
            context.logger.error(f"  ❌ pi guard {what} failed: {errors[0]}")
            return PluginResult(
                success=False,
                plugin_name=self.name,
                message=f"pi guard {what} failed: {errors[0]}",
                errors=errors,
            )
        return PluginResult(success=True, plugin_name=self.name, message=f"pi guard {what} ok")

    def install(self, context: InstallContext) -> PluginResult:
        options = PiOptions.from_metadata(context.metadata)
        return self._run(
            context,
            "install",
            lambda: pi_guard.apply(options, context.logger, context.dry_run),
        )

    def uninstall(self, context: InstallContext) -> PluginResult:
        return self._run(context, "uninstall", lambda: pi_guard.remove(context.logger))

    def verify(self, context: InstallContext) -> PluginResult:
        def check() -> list[str]:
            errors, warnings = pi_guard.check(PiOptions.from_metadata(context.metadata))
            for warning in warnings:
                context.logger.info(f"  ⚠️ {warning}")
            return errors

        return self._run(context, "verification", check)
