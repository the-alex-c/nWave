import json
import logging
from pathlib import Path
from typing import Any

import pytest

from scripts.install.plugins.base import InstallContext


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def pi_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "agent"
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(d))
    return d


@pytest.fixture
def ctx(tmp_path: Path) -> InstallContext:
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
def pi_calls(pi_dir: Path, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Stand in for the pi CLI: record `pi install|remove` and edit settings.json."""
    from scripts.shared import pi_code_package as pcp

    calls: list[list[str]] = []

    def run(args: list[str]) -> None:
        calls.append(args)
        settings = pi_dir / "settings.json"
        doc = json.loads(settings.read_text()) if settings.is_file() else {}
        packages = [p for p in doc.get("packages", []) if pcp.entry_source(p) != args[1]]
        doc["packages"] = packages + ([args[1]] if args[0] == "install" else [])
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(json.dumps(doc))

    monkeypatch.setattr(pcp, "_run", run)
    monkeypatch.setattr(pcp, "_which", lambda _name: "/fake/pi")
    return calls


class PiBoth:
    """Guard plugin then skills plugin, as the registry orders them."""

    def _each(self, method: str, ctx: Any) -> Any:
        from scripts.install.plugins.pi_guard_plugin import PiGuardPlugin
        from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin

        results = [getattr(p, method)(ctx) for p in (PiGuardPlugin(), PiSkillsPlugin())]
        return next((r for r in results if not r.success), results[-1])

    def install(self, ctx: Any) -> Any:
        return self._each("install", ctx)

    def uninstall(self, ctx: Any) -> Any:
        return self._each("uninstall", ctx)

    def verify(self, ctx: Any) -> Any:
        return self._each("verify", ctx)
