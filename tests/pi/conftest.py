import json
import logging
from pathlib import Path

import pytest

from scripts.install.plugins.base import InstallContext


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def pi_dir(tmp_path, monkeypatch):
    d = tmp_path / "agent"
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(d))
    return d


@pytest.fixture
def ctx(tmp_path):
    return InstallContext(
        claude_dir=tmp_path / "claude",
        scripts_dir=ROOT / "scripts" / "install",
        templates_dir=ROOT / "nWave" / "templates",
        logger=logging.getLogger("pi-test"),
        project_root=ROOT,
        framework_source=ROOT / "nWave",
        target_platforms={"pi"},
    )


@pytest.fixture(autouse=True)
def pi_calls(pi_dir, monkeypatch):
    """Stand in for the pi CLI: record `pi install|remove` and edit settings.json."""
    from scripts.shared import pi_code_package as pcp

    calls = []

    def run(args):
        calls.append(args)
        settings = pi_dir / "settings.json"
        doc = json.loads(settings.read_text()) if settings.is_file() else {}
        packages = [p for p in doc.get("packages", []) if pcp._source(p) != args[1]]
        doc["packages"] = packages + ([args[1]] if args[0] == "install" else [])
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps(doc))

    monkeypatch.setattr(pcp, "_run", run)
    monkeypatch.setattr(pcp, "which", lambda name: "/fake/pi")
    return calls
