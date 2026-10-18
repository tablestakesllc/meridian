"""
tests/test_hooks.py

The public git hooks in .githooks/ behave as gates for contributors without the
maintainer submodule.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".githooks"


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    shutil.copy(HOOKS / "commit-msg", tmp_path / "commit-msg")
    return tmp_path


def run_commit_msg(repo, text):
    msg = repo / "MSG"
    msg.write_text(text)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["bash", str(repo / "commit-msg"), str(msg)], cwd=repo, env=env,
                          capture_output=True, text=True)


@pytest.mark.parametrize("marker", ["[skip ci]", "[ci skip]", "[no ci]", "[skip actions]",
                                    "[actions skip]", "skip-checks: true", "[SKIP CI]"])
def test_commit_msg_blocks_ci_skip_markers(repo, marker):
    result = run_commit_msg(repo, f"docs: update\n\n{marker}\n")
    assert result.returncode == 1
    assert "skip marker" in result.stderr


def test_commit_msg_allows_clean_message(repo):
    assert run_commit_msg(repo, "docs: update the bootstrap\n").returncode == 0


def test_commit_msg_ignores_git_comment_lines(repo):
    assert run_commit_msg(repo, "docs: update\n# [skip ci] in a comment is ignored\n").returncode == 0


def test_hooks_are_executable():
    for name in ("pre-commit", "commit-msg", "pre-push"):
        assert os.access(HOOKS / name, os.X_OK), name
