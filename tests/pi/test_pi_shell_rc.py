from pathlib import Path

import pytest

from scripts.shared.pi_shell_rc import (
    BEGIN,
    END,
    FUNCTION,
    add_block,
    rc_path,
    remove_block,
    should_add,
)


HOME = Path("/h")


@pytest.mark.parametrize(
    ("shell", "system", "expected"),
    [
        ("/bin/zsh", "Darwin", HOME / ".zshrc"),
        ("/usr/bin/zsh", "Linux", HOME / ".zshrc"),
        ("/bin/bash", "Darwin", HOME / ".bash_profile"),
        ("/bin/bash", "Linux", HOME / ".bashrc"),
        ("/usr/bin/fish", "Linux", None),
        ("", "Linux", None),
    ],
)
def test_rc_path_by_shell_and_os(shell, system, expected):
    assert rc_path(shell, system, HOME) == expected


def test_function_is_the_documented_one_liner():
    assert FUNCTION == 'pi() { CLAUDE_CONFIG_DIR="$HOME/.pi/agent" command pi "$@"; }'


def test_add_creates_missing_rc_with_marked_block(tmp_path):
    rc = tmp_path / ".zshrc"
    assert add_block(rc) is True
    text = rc.read_text()
    assert text.count(BEGIN) == 1 and text.count(END) == 1
    assert FUNCTION in text.split(BEGIN)[1].split(END)[0]


def test_add_twice_is_idempotent(tmp_path):
    rc = tmp_path / ".zshrc"
    rc.write_text("alias ll='ls -l'\n")
    assert add_block(rc) is True
    once = rc.read_text()
    assert add_block(rc) is False
    assert rc.read_text() == once


def test_remove_restores_user_text_byte_for_byte(tmp_path):
    rc = tmp_path / ".zshrc"
    user = "export A=1\n\n# mine\nalias ll='ls -l'\n"
    rc.write_text(user)
    add_block(rc)
    assert remove_block(rc) is True
    assert rc.read_text() == user


def test_user_text_after_block_survives_remove(tmp_path):
    rc = tmp_path / ".zshrc"
    add_block(rc)
    rc.write_text(rc.read_text() + "export AFTER=1\n")
    remove_block(rc)
    assert rc.read_text() == "export AFTER=1\n"


def test_add_to_file_without_trailing_newline_keeps_user_line_intact(tmp_path):
    rc = tmp_path / ".zshrc"
    rc.write_text("export A=1")
    add_block(rc)
    assert rc.read_text().startswith("export A=1\n")
    remove_block(rc)
    assert rc.read_text().strip() == "export A=1"


def test_remove_without_block_or_file_changes_nothing(tmp_path):
    rc = tmp_path / ".zshrc"
    assert remove_block(rc) is False
    assert not rc.exists()
    rc.write_text("export A=1\n")
    assert remove_block(rc) is False
    assert rc.read_text() == "export A=1\n"


def test_remove_refuses_unterminated_block(tmp_path):
    rc = tmp_path / ".zshrc"
    broken = f"before\n{BEGIN}\nmy own stuff\n"
    rc.write_text(broken)
    assert remove_block(rc) is False
    assert rc.read_text() == broken


def test_should_add_matrix():
    never = lambda: pytest.fail("must not prompt")  # noqa: E731
    assert should_add("yes", False, never) is True
    assert should_add("yes", True, never) is True
    assert should_add("no", True, never) is False
    assert should_add(None, False, never) is False
    assert should_add(None, True, lambda: True) is True
    assert should_add(None, True, lambda: False) is False
