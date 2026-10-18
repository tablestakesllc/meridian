"""
tests/test_seed_bundle.py

Tests for scripts/build_seed_bundle.py and the seed bundle it produces,
including the acceptance path: extract the bundle into an empty git repo,
run --seed and --generate-l1, and get a non-empty L1_CONTEXT.md.
"""

import hashlib
import importlib.util
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("build_seed_bundle", ROOT / "scripts" / "build_seed_bundle.py")
bsb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bsb)


@pytest.fixture
def built(tmp_path, monkeypatch):
    monkeypatch.setattr(bsb, "DIST", tmp_path / "dist")
    bundle, manifest = bsb.build()
    return bundle, manifest


def test_templates_pass_checks():
    assert bsb.check() == []


def test_version_is_three_part():
    assert bsb.VERSION_RE.match(bsb.meridian_version())


@pytest.mark.parametrize("letter", sorted(bsb.APPENDIX_SKILLS))
def test_skill_templates_match_bootstrap_appendices(letter):
    rel = bsb.APPENDIX_SKILLS[letter]
    published = bsb.extract_appendix(bsb.BOOTSTRAP.read_text(encoding="utf-8"), letter)
    assert (bsb.TEMPLATES / rel).read_text(encoding="utf-8") == published


def test_manifest_lists_every_file_with_correct_hash(built):
    bundle, manifest_path = built
    data = json.loads(manifest_path.read_text())
    assert data["meridian_version"] == bsb.meridian_version()
    assert data["contract_version"] == 1
    paths = {f["path"] for f in data["files"]}
    assert paths == set(bsb.FILES)
    assert bsb.MANIFEST_PATH not in paths  # the manifest does not list itself
    with tarfile.open(bundle) as tar:
        for entry in data["files"]:
            payload = tar.extractfile(entry["path"]).read()
            assert hashlib.sha256(payload).hexdigest() == entry["sha256"], entry["path"]
            assert entry["kind"] in {"machine", "knowledge"}


def test_bundle_manifest_identical_to_release_asset(built):
    bundle, manifest_path = built
    with tarfile.open(bundle) as tar:
        inner = tar.extractfile(bsb.MANIFEST_PATH).read()
    assert inner == manifest_path.read_bytes()


def test_bundle_is_reproducible(tmp_path, monkeypatch):
    monkeypatch.setattr(bsb, "DIST", tmp_path / "a")
    first, _ = bsb.build()
    monkeypatch.setattr(bsb, "DIST", tmp_path / "b")
    second, _ = bsb.build()
    assert first.read_bytes() == second.read_bytes()


def test_bundle_paths_are_relative_and_contain_no_local_state(built):
    bundle, _ = built
    with tarfile.open(bundle) as tar:
        names = tar.getnames()
    for name in names:
        assert not name.startswith("/") and ".." not in Path(name).parts
        assert not name.startswith(".agent/")
        assert not name.endswith(("L1_CONTEXT.md", "context_swap.json", "weights.yaml"))


def test_check_rejects_nested_fill_markers(tmp_path, monkeypatch):
    fake = tmp_path / "templates"
    for rel in bsb.FILES:
        (fake / rel).parent.mkdir(parents=True, exist_ok=True)
        (fake / rel).write_bytes((bsb.TEMPLATES / rel).read_bytes())
    (fake / "agent_docs/MEMORY.md").write_text(
        '<!-- meridian:fill id="a" -->\n<!-- meridian:fill id="b" -->\nx\n'
        "<!-- /meridian:fill -->\n<!-- /meridian:fill -->\n## §0\n"
    )
    monkeypatch.setattr(bsb, "TEMPLATES", fake)
    assert any("nested" in p for p in bsb.check())


def _copy_templates(tmp_path):
    fake = tmp_path / "templates"
    for rel in bsb.FILES:
        (fake / rel).parent.mkdir(parents=True, exist_ok=True)
        (fake / rel).write_bytes((bsb.TEMPLATES / rel).read_bytes())
    return fake


@pytest.mark.parametrize("drop", [bsb.HALT_OPEN, bsb.HALT_CLOSE])
def test_check_requires_latitude_halt_markers(tmp_path, monkeypatch, drop):
    fake = _copy_templates(tmp_path)
    path = fake / "agent_docs/SESSION_INIT.md"
    path.write_text("\n".join(ln for ln in path.read_text().splitlines() if ln.strip() != drop) + "\n")
    monkeypatch.setattr(bsb, "TEMPLATES", fake)
    assert any("latitude:halt" in p for p in bsb.check())


def test_halt_block_contains_redirect():
    lines = [ln.strip() for ln in (bsb.TEMPLATES / "agent_docs/SESSION_INIT.md").read_text().splitlines()]
    block = lines[lines.index(bsb.HALT_OPEN) + 1 : lines.index(bsb.HALT_CLOSE)]
    assert any("**HALT.**" in ln for ln in block)
    assert any("`bootstrap`" in ln for ln in block)


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_acceptance_empty_repo_seed_and_l1(built, tmp_path):
    """Contract acceptance: bundle into an empty repo, --seed, --generate-l1 -> non-empty L1."""
    bundle, _ = built
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    with tarfile.open(bundle) as tar:
        tar.extractall(repo, filter="data")
    # Install rules: the agent appends the fragments to the repo's own files.
    (repo / ".gitattributes").write_text((repo / ".gitattributes.meridian").read_text())
    (repo / ".gitignore").write_text((repo / ".gitignore.meridian").read_text())

    script = repo / ".agents/skills/meridian-v4/weight_memory.py"
    for flag in ("--seed", "--generate-l1"):
        result = subprocess.run([sys.executable, str(script), flag], cwd=repo, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr

    l1 = (repo / "agent_docs/L1_CONTEXT.md").read_text()
    assert "Current L1 blocks: 1" in l1
    assert "<!-- block: agent-operating-prefs" in l1
    assert "**Session bootstrap:**" in l1
    assert "## File → Skill Routing Table" in l1
    assert "(4.7.1)" in l1 or f"({bsb.meridian_version()})" in l1
    assert (repo / ".agent/weights.yaml").is_file()
    # The generated files stay out of git.
    status = subprocess.run(["git", "status", "--short"], cwd=repo, capture_output=True, text=True).stdout
    assert "L1_CONTEXT.md" not in status and ".agent/" not in status
