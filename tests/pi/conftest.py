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
