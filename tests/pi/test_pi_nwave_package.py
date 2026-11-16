"""pi-code-nwave is a self-contained pi package that the wheel bundles."""

import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "pi-code-nwave"
EXTENSIONS = ["./extensions/agent/index.ts", "./extensions/submit/index.ts"]


def test_schemas_inside_package_match_the_installer_source() -> None:
    source = ROOT / "nwave_ai" / "platform" / "role_envelope_schemas.json"
    assert (PKG / "role_envelope_schemas.json").read_bytes() == source.read_bytes()


def test_manifest_declares_both_extensions_that_exist() -> None:
    manifest = json.loads((PKG / "package.json").read_text())
    assert manifest["pi"]["extensions"] == EXTENSIONS
    assert all((PKG / e).is_file() for e in EXTENSIONS)


def test_wheel_bundles_the_package_without_dev_files() -> None:
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text())
    force = cfg["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    bundled = {dest for src, dest in force.items() if src.startswith("pi-code-nwave")}
    assert "nWave/pi-code-nwave/package.json" in bundled
    assert "nWave/pi-code-nwave/extensions" in bundled
    assert "nWave/pi-code-nwave/role_envelope_schemas.json" in bundled
    assert not any("node_modules" in d or "tests" in d for d in bundled)
