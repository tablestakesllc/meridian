"""
tests/test_workflows.py

Resource and security rules for .github/workflows. These keep outside users from
running code or consuming runner time through this repository.
"""

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = sorted((Path(__file__).resolve().parent.parent / ".github" / "workflows").glob("*.yml"))
ALLOWED_EVENTS = {"pull_request", "push"}
FORBIDDEN_EVENTS = {"pull_request_target", "issue_comment", "issues", "schedule", "workflow_run",
                    "discussion", "discussion_comment", "fork", "watch", "repository_dispatch"}
PINNED = re.compile(r"^actions/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")


def load(path):
    data = yaml.safe_load(path.read_text())
    # PyYAML parses the bare key `on` as boolean True.
    data["on"] = data.pop(True, data.get("on"))
    return data


def test_workflows_exist():
    assert {p.name for p in WORKFLOWS} >= {"ci.yml", "pr-text.yml", "release.yml"}


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_only_allowed_triggers(path):
    events = set(load(path)["on"])
    assert not events & FORBIDDEN_EVENTS, events & FORBIDDEN_EVENTS
    assert events <= ALLOWED_EVENTS, events - ALLOWED_EVENTS


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_top_level_token_is_read_only(path):
    assert load(path)["permissions"] == {"contents": "read"}


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_jobs_have_timeouts_and_hosted_runners(path):
    for name, job in load(path)["jobs"].items():
        assert 0 < job["timeout-minutes"] <= 15, name
        assert job["runs-on"] == "ubuntu-latest", f"{name}: GitHub-hosted standard runners only"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_actions_are_github_owned_and_sha_pinned(path):
    for name, job in load(path)["jobs"].items():
        for step in job["steps"]:
            if "uses" in step:
                assert PINNED.match(step["uses"]), f"{name}: {step['uses']}"
                if step["uses"].startswith("actions/checkout@"):
                    assert step["with"]["submodules"] is False
                    assert step["with"]["persist-credentials"] is False


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_write_permission_only_in_release_job(path):
    for name, job in load(path)["jobs"].items():
        perms = job.get("permissions", {})
        writes = {k for k, v in perms.items() if v == "write"}
        if path.name == "release.yml" and name == "release":
            assert writes == {"contents"}
            assert job["if"] == "github.repository == 'tablestakesllc/meridian'"
        else:
            assert not writes, f"{path.name}:{name} {writes}"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_no_untrusted_input_interpolated_into_scripts(path):
    # PR titles/bodies/branch names must reach scripts through env, never ${{ }} in run:.
    risky = re.compile(r"\$\{\{\s*github\.(event\.(pull_request|issue|comment|head_commit)|head_ref)")
    for name, job in load(path)["jobs"].items():
        for step in job["steps"]:
            assert not risky.search(step.get("run", "")), f"{path.name}:{name}"


def test_release_runs_only_on_version_tags():
    on = load(Path(WORKFLOWS[0]).parent / "release.yml")["on"]
    assert set(on) == {"push"}
    assert on["push"] == {"tags": ["v[0-9]+.[0-9]+.[0-9]+"]}
