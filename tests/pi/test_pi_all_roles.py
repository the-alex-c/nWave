"""Every shipped role maps to pi and validates (TODO-RUNG-3, Validation)."""

from __future__ import annotations

from pathlib import Path

from scripts.shared.pi_role_mapping import to_pi_role
from scripts.shared.pi_role_validation import validate_roles


ROOT = Path(__file__).resolve().parents[2]


def test_every_role_maps_and_validates() -> None:
    sources = sorted((ROOT / "nWave" / "agents").glob("nw-*.md"))
    assert sources
    mapped = {p.stem: to_pi_role(p.stem, p.read_text())[0] for p in sources}
    assert validate_roles(mapped, ROOT / "nWave" / "skills") == []
