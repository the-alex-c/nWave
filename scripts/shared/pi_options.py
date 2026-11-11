"""pi install choices: the level (1 = skills, 2 = skills + guard) and the shell-rc answer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from scripts.shared.install_paths import pi_skills_dir


ShellRc = Literal["yes", "no"]

MAX_LEVEL = 2
LEVELS = (1, MAX_LEVEL)

#: The skills manifest records the install level; this module owns that contract.
MANIFEST_FILENAME = ".nwave-manifest.json"


@dataclass(frozen=True)
class PiOptions:
    """pi install choices, carried through ``InstallContext.metadata``.

    ``level``: 1 = skills, 2 = skills + guard; None = not given on the command line.
    ``shell_rc``: "yes" | "no" | None (ask on a TTY, else print only).
    """

    level: int | None = None
    shell_rc: ShellRc | None = None

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> PiOptions:
        return cls(metadata.get("pi_level"), metadata.get("pi_shell_rc"))

    def to_metadata(self) -> dict[str, Any]:
        return {"pi_level": self.level, "pi_shell_rc": self.shell_rc}

    def guard_wanted(self, *, verifying: bool = False) -> bool:
        """Whether the PreToolUse guard is wanted at the level being installed or verified."""
        return (self.verify_level if verifying else self.install_level) >= MAX_LEVEL

    @property
    def install_level(self) -> int:
        """Level to install: explicit, else the highest."""
        return self.level or MAX_LEVEL

    @property
    def verify_level(self) -> int:
        """Level to verify: explicit, else the one recorded in the skills manifest, else highest."""
        if self.level:
            return self.level
        try:
            recorded = json.loads(
                (pi_skills_dir() / MANIFEST_FILENAME).read_text(encoding="utf-8")
            )["level"]
        except (OSError, ValueError, KeyError, TypeError):
            return MAX_LEVEL
        return recorded if recorded in LEVELS else MAX_LEVEL
