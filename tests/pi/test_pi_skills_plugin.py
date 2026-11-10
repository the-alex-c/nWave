import json

from scripts.install.install_nwave import _PLATFORM_CHOICES
from scripts.install.plugins.pi_skills_plugin import PiSkillsPlugin
from scripts.shared.skill_path_rewrite import rewrite_host_paths


def test_pi_is_a_platform_choice():
    assert ("pi", frozenset({"pi"})) in [(f, t) for f, t, _ in _PLATFORM_CHOICES]


def test_install_copies_skills_and_writes_manifest(pi_dir, ctx):
    result = PiSkillsPlugin().install(ctx)
    assert result.success, result.errors
    skills = pi_dir / "skills"
    names = json.loads((skills / ".nwave-manifest.json").read_text())[
        "installed_skills"
    ]
    assert names and all(n.startswith("nw-") for n in names)
    assert all((skills / n / "SKILL.md").is_file() for n in names)
    assert PiSkillsPlugin().verify(ctx).success


def test_foreign_nw_dir_is_refused(pi_dir, ctx):
    (pi_dir / "skills" / "nw-foreign").mkdir(parents=True)
    result = PiSkillsPlugin().install(ctx)
    assert not result.success
    assert (pi_dir / "skills" / "nw-foreign").is_dir()


def test_uninstall_removes_only_owned(pi_dir, ctx):
    PiSkillsPlugin().install(ctx)
    mine = pi_dir / "skills" / "my-own"
    mine.mkdir()
    assert PiSkillsPlugin().uninstall(ctx).success
    assert [p.name for p in (pi_dir / "skills").iterdir()] == ["my-own"]


def test_paths_rewritten_to_pi_root():
    assert (
        rewrite_host_paths("see ~/.claude/skills/nw-x/SKILL.md", "pi")
        == "see ~/.pi/agent/skills/nw-x/SKILL.md"
    )
