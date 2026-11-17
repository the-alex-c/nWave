"""One path-segment check shared by the pi plugins' ownership manifests."""

from __future__ import annotations

from pathlib import Path


def is_plain_name(name: object) -> bool:
    """True for one path segment that names a child, never '.' or '..'."""
    return (
        isinstance(name, str)
        and name not in {"", ".", ".."}
        and Path(name).name == name
    )
