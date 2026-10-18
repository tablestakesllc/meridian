"""
tests/test_weight_memory.py

Unit tests for templates/.agents/skills/meridian-v4/weight_memory.py, the
engine shipped in the seed bundle.

Each test is isolated: a minimal MEMORY_INDEX.yaml is written to a tmp_path,
INDEX_PATH and REPO_ROOT are monkeypatched, and main() is called via sys.argv.
No live repo files are read or written.
"""

import sys
from pathlib import Path

import pytest
import yaml

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "templates" / ".agents" / "skills" / "meridian-v4"))
import weight_memory  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

_META = {
    "format_version": 4,
    "thresholds": {"l1": 8.0, "archive": 2.0},
    "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
    "updated": "2026-01-01",
}


def _block(
    block_id: str,
    weight: float = 5.0,
    tier: str = "L2",
    skill: str | None = "demo-test",
    status: str = "active",
    last_used: str = "2026-01-01",
) -> dict:
    return {
        "id": block_id,
        "tier": tier,
        "weight": weight,
        "status": status,
        "skill": skill,
        "last_used": last_used,
        "mem": "§1",
        "domain": "test",
        "depends": [],
        "tags": [],
        "summary": f"Test block {block_id}",
    }


def _write_index(path: Path, blocks: list[dict]) -> None:
    data = {"meta": dict(_META), "blocks": blocks}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _write_weights(path: Path, blocks: list[dict]) -> None:
    """Write a minimal .agent/weights.yaml from test blocks."""
    weights_blocks = [
        {
            "id": b["id"],
            "weight": b.get("weight", 5.0),
            "tier": b.get("tier", "L2"),
            "last_used": b.get("last_used"),
        }
        for b in blocks
    ]
    data = {
        "meta": {
            "schema_version": 1,
            "thresholds": {"l1": 8.0, "archive": 2.0},
            "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
            "last_updated": "2026-01-01",
            "last_updated_by": "test",
        },
        "blocks": weights_blocks,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _run(
    monkeypatch,
    tmp_path: Path,
    blocks: list[dict],
    used: str = "",
    loaded: str = "",
    date: str = "2026-05-16",
    dry_run: bool = False,
    skill_dirs: list[str] | None = None,
) -> tuple[dict, str]:
    """Write index + weights, patch paths, run main(), return (weights_data, stdout).

    The MEMORY_INDEX.yaml is used by the script for integrity/deprecated/status
    lookups. The .agent/weights.yaml is the actual weight store — read and
    written by cmd_update. Both are isolated to tmp_path so tests never touch
    the live developer files.
    """
    # Write MEMORY_INDEX.yaml for integrity/deprecated checks
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    _write_index(index_path, blocks)

    # Write .agent/weights.yaml — the actual weight store
    weights_path = tmp_path / ".agent" / "weights.yaml"
    _write_weights(weights_path, blocks)

    # Ensure L1_CONTEXT.md parent dir exists so the script can write there
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)

    # Create fake skill files so integrity checks have something to validate against
    if skill_dirs is not None:
        for skill_name in skill_dirs:
            skill_file = tmp_path / ".agents" / "skills" / skill_name / "SKILL.md"
            skill_file.parent.mkdir(parents=True, exist_ok=True)
            skill_file.write_text(f"# {skill_name} skill\n")

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)

    # Always pass --used and --loaded so main() routes to cmd_update (not print_help)
    argv = ["weight_memory.py", "--date", date, "--used", used, "--loaded", loaded]
    if dry_run:
        argv += ["--dry-run"]
    monkeypatch.setattr(sys, "argv", argv)

    weight_memory.main()

    if not dry_run:
        with weights_path.open() as f:
            result_data = yaml.safe_load(f)
    else:
        # Dry-run: return the original blocks unchanged (no writes occurred)
        result_data = {
            "meta": {},
            "blocks": [
                {"id": b["id"], "weight": b.get("weight", 5.0),
                 "tier": b.get("tier", "L2"), "last_used": b.get("last_used")}
                for b in blocks
            ],
        }

    return result_data, ""  # stdout captured via capsys by caller


# ── Delta logic ───────────────────────────────────────────────────────────────

def test_loaded_and_used_increases_weight(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", weight=5.0, last_used="2026-01-01")]
    data, _ = _run(monkeypatch, tmp_path, blocks,
                   used="block-a", loaded="block-a", date="2026-05-16",
                   skill_dirs=["demo-test"])
    b = data["blocks"][0]
    assert b["weight"] == pytest.approx(5.10)
    assert b["last_used"] == "2026-05-16"


def test_loaded_only_no_delta_but_updates_last_used(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", weight=5.0, last_used="2026-01-01")]
    data, _ = _run(monkeypatch, tmp_path, blocks,
                   loaded="block-a", date="2026-05-16",
                   skill_dirs=["demo-test"])
    b = data["blocks"][0]
    assert b["weight"] == pytest.approx(5.00)
    assert b["last_used"] == "2026-05-16"


def test_not_loaded_decays_weight_and_does_not_touch_last_used(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", weight=5.0, last_used="2026-01-01")]
    data, _ = _run(monkeypatch, tmp_path, blocks,
                   date="2026-05-16",
                   skill_dirs=["demo-test"])
    b = data["blocks"][0]
    assert b["weight"] == pytest.approx(4.95)
    assert b["last_used"] == "2026-01-01"  # unchanged


def test_weight_floor_clamp(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", weight=0.05)]
    data, _ = _run(monkeypatch, tmp_path, blocks,
                   date="2026-05-16",
                   skill_dirs=["demo-test"])
    assert data["blocks"][0]["weight"] == pytest.approx(0.0)


def test_weight_ceiling_clamp(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", weight=9.95)]
    data, _ = _run(monkeypatch, tmp_path, blocks,
                   used="block-a", loaded="block-a", date="2026-05-16",
                   skill_dirs=["demo-test"])
    assert data["blocks"][0]["weight"] == pytest.approx(10.0)


# ── Tier transitions ──────────────────────────────────────────────────────────

def test_l2_promoted_to_l1(monkeypatch, tmp_path, capsys):
    # weight 7.95 + 0.10 = 8.05 → L1
    blocks = [_block("block-a", weight=7.95, tier="L2")]
    data, _ = _run(monkeypatch, tmp_path, blocks,
                   used="block-a", loaded="block-a", date="2026-05-16",
                   skill_dirs=["demo-test"])
    assert data["blocks"][0]["tier"] == "L1"
    out = capsys.readouterr().out
    assert "PROMOTED" in out


def test_l1_demoted_to_l2(monkeypatch, tmp_path, capsys):
    # weight 8.05 − 0.05 = 8.00 — still L1 (threshold is >=8.0)
    # weight 8.00 − 0.05 = 7.95 → L2
    blocks = [_block("block-a", weight=8.00, tier="L1", skill=None)]
    data, _ = _run(monkeypatch, tmp_path, blocks,
                   date="2026-05-16")
    assert data["blocks"][0]["tier"] == "L2"
    out = capsys.readouterr().out
    assert "DEMOTED" in out


# ── Input validation ──────────────────────────────────────────────────────────

def test_used_not_in_loaded_auto_adds_with_warning(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a")]
    # --used contains block-a but --loaded does not
    _run(monkeypatch, tmp_path, blocks,
         used="block-a", loaded="",
         date="2026-05-16", skill_dirs=["demo-test"])
    # Should not raise; stderr should contain a warning
    capsys.readouterr()
    # The warning goes to stderr via sys.stderr in the script
    # We verify the run completes without error and weight still applied
    weights_path = tmp_path / ".agent" / "weights.yaml"
    with weights_path.open() as f:
        result = yaml.safe_load(f)
    assert result["blocks"][0]["weight"] == pytest.approx(5.10)


# ── Integrity checks ──────────────────────────────────────────────────────────

def test_integrity_orphaned_l2_block_flagged(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", skill=None, tier="L2")]
    _run(monkeypatch, tmp_path, blocks, date="2026-05-16")
    out = capsys.readouterr().out
    assert "INTEGRITY ISSUES" in out
    assert "block-a" in out
    assert "Orphaned" in out


def test_integrity_l1_block_with_null_skill_not_flagged(monkeypatch, tmp_path, capsys):
    # L1 blocks auto-load via L1_CONTEXT.md — skill: null is fine
    blocks = [_block("block-a", skill=None, tier="L1", weight=9.0)]
    _run(monkeypatch, tmp_path, blocks, date="2026-05-16")
    out = capsys.readouterr().out
    assert "INTEGRITY ISSUES" not in out
    assert "Integrity: OK" in out


def test_integrity_missing_skill_file_flagged(monkeypatch, tmp_path, capsys):
    # block points to demo-missing but that skill directory doesn't exist
    blocks = [_block("block-a", skill="demo-missing", tier="L2")]
    # Note: skill_dirs not passed → no skill files created
    _run(monkeypatch, tmp_path, blocks, date="2026-05-16")
    out = capsys.readouterr().out
    assert "INTEGRITY ISSUES" in out
    assert "demo-missing" in out


def test_integrity_ok_when_all_l2_blocks_have_valid_skills(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", skill="demo-test", tier="L2")]
    _run(monkeypatch, tmp_path, blocks, date="2026-05-16", skill_dirs=["demo-test"])
    out = capsys.readouterr().out
    assert "Integrity: OK" in out


# ── Health check ──────────────────────────────────────────────────────────────

def test_health_check_no_warning_when_fresh(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", last_used="2026-05-16")]
    _run(monkeypatch, tmp_path, blocks, date="2026-05-16", skill_dirs=["demo-test"])
    out = capsys.readouterr().out
    assert "MEMORY HEALTH" not in out


def test_health_check_warning_fires_at_40_percent(monkeypatch, tmp_path, capsys):
    # All blocks stale (last_used 200 days before session date) → 100% → warning
    old_date = "2025-11-02"  # ~200 days before 2026-05-16
    blocks = [
        _block("block-a", last_used=old_date),
        _block("block-b", last_used=old_date),
    ]
    _run(monkeypatch, tmp_path, blocks, date="2026-05-16", skill_dirs=["demo-test"])
    out = capsys.readouterr().out
    assert "MEMORY HEALTH" in out
    assert "HUMAN ACTION RECOMMENDED" in out


def test_health_check_archive_blocks_excluded(monkeypatch, tmp_path, capsys):
    # ARCHIVE blocks should not count toward stale percentage
    old_date = "2025-11-02"
    blocks = [
        _block("block-a", last_used=old_date, tier="ARCHIVE", weight=1.5),
    ]
    _run(monkeypatch, tmp_path, blocks, date="2026-05-16", skill_dirs=["demo-test"])
    out = capsys.readouterr().out
    assert "MEMORY HEALTH" not in out


# ── Deprecated block warning ──────────────────────────────────────────────────

def test_deprecated_high_weight_warning(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", weight=4.5, status="deprecated")]
    _run(monkeypatch, tmp_path, blocks, date="2026-05-16")
    out = capsys.readouterr().out
    assert "DEPRECATED BLOCKS WITH HIGH WEIGHT" in out
    assert "block-a" in out


def test_deprecated_block_below_threshold_no_warning(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", weight=3.9, status="deprecated")]
    _run(monkeypatch, tmp_path, blocks, date="2026-05-16")
    out = capsys.readouterr().out
    assert "DEPRECATED BLOCKS WITH HIGH WEIGHT" not in out


# ── Dry-run guard ─────────────────────────────────────────────────────────────

def test_dry_run_does_not_write_index(monkeypatch, tmp_path, capsys):
    blocks = [_block("block-a", weight=5.0)]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    _write_index(index_path, blocks)
    _write_weights(weights_path, blocks)
    l1_path.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "weight_memory.py", "--date", "2026-05-16",
        "--used", "block-a", "--loaded", "block-a", "--dry-run",
    ])

    mtime_before = weights_path.stat().st_mtime
    weight_memory.main()
    mtime_after = weights_path.stat().st_mtime

    assert mtime_before == mtime_after, "Weights file should not be modified in dry-run mode"
    out = capsys.readouterr().out
    assert "dry-run" in out.lower()


# ── extract_block_content — split marker ─────────────────────────────────────

def _make_source(tmp_path: Path, content: str) -> Path:
    """Write content to a temp MEMORY.md and patch BLOCK_SOURCES to use it."""
    p = tmp_path / "MEMORY.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_extract_no_marker_returns_full_content(monkeypatch, tmp_path):
    """Block without <!-- /l1-summary --> returns full content unchanged."""
    src = _make_source(tmp_path, """\
<!-- block: my-block | domain: test | mem: §1 -->
Line A
Line B
<!-- /block -->
""")
    monkeypatch.setattr(weight_memory, "BLOCK_SOURCES", [src])
    result = weight_memory.extract_block_content("my-block")
    assert result is not None
    assert "Line A" in result
    assert "Line B" in result
    assert result.endswith("<!-- /block -->")


def test_extract_with_marker_returns_only_summary(monkeypatch, tmp_path):
    """Block with <!-- /l1-summary --> returns only content above the marker."""
    src = _make_source(tmp_path, """\
<!-- block: my-block | domain: test | mem: §1 -->
Summary line
<!-- /l1-summary -->
Reference content that must NOT appear in L1
<!-- /block -->
""")
    monkeypatch.setattr(weight_memory, "BLOCK_SOURCES", [src])
    result = weight_memory.extract_block_content("my-block")
    assert result is not None
    assert "Summary line" in result
    assert "Reference content" not in result
    assert result.endswith("<!-- /block -->")


def test_extract_with_marker_marker_line_itself_excluded(monkeypatch, tmp_path):
    """The <!-- /l1-summary --> marker line is not included in the returned content."""
    src = _make_source(tmp_path, """\
<!-- block: my-block | domain: test | mem: §1 -->
Summary
<!-- /l1-summary -->
Reference
<!-- /block -->
""")
    monkeypatch.setattr(weight_memory, "BLOCK_SOURCES", [src])
    result = weight_memory.extract_block_content("my-block")
    assert "/l1-summary" not in result


def test_extract_missing_block_returns_none(monkeypatch, tmp_path):
    """A block ID that does not exist in any source returns None."""
    src = _make_source(tmp_path, """\
<!-- block: other-block | domain: test | mem: §1 -->
Content
<!-- /block -->
""")
    monkeypatch.setattr(weight_memory, "BLOCK_SOURCES", [src])
    result = weight_memory.extract_block_content("nonexistent-block")
    assert result is None


def test_extract_header_line_always_included(monkeypatch, tmp_path):
    """The opening <!-- block: ... --> comment is always the first line returned."""
    src = _make_source(tmp_path, """\
<!-- block: my-block | domain: test | mem: §1 -->
Content
<!-- /l1-summary -->
Reference
<!-- /block -->
""")
    monkeypatch.setattr(weight_memory, "BLOCK_SOURCES", [src])
    result = weight_memory.extract_block_content("my-block")
    assert result.startswith("<!-- block: my-block")


def test_extract_split_preserves_multiline_summary(monkeypatch, tmp_path):
    """All lines above the marker (not just the first) are returned."""
    src = _make_source(tmp_path, """\
<!-- block: my-block | domain: test | mem: §1 -->
Line 1
Line 2
Line 3
<!-- /l1-summary -->
Reference
<!-- /block -->
""")
    monkeypatch.setattr(weight_memory, "BLOCK_SOURCES", [src])
    result = weight_memory.extract_block_content("my-block")
    assert "Line 1" in result
    assert "Line 2" in result
    assert "Line 3" in result
    assert "Reference" not in result


# ═════════════════════════════════════════════════════════════════════════════
# Item 1 — Maintenance counter
# ═════════════════════════════════════════════════════════════════════════════

def test_maintenance_counter_increments(monkeypatch, tmp_path, capsys):
    """sessions_since_maintenance increments by 1 on every --used/--loaded run."""
    blocks = [_block("alpha", weight=5.0, tier="L2")]
    # Seed with counter already at 3
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, blocks)
    _write_weights(weights_path, blocks)
    with weights_path.open() as f:
        data = yaml.safe_load(f)
    data["meta"]["sessions_since_maintenance"] = 3
    data["meta"]["maintenance_interval"] = 10
    data["meta"]["maintenance_deferred"] = None
    with weights_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "alpha", "--loaded", "alpha", "--date", "2026-06-01"])
    weight_memory.main()

    with weights_path.open() as f:
        result = yaml.safe_load(f)
    assert result["meta"]["sessions_since_maintenance"] == 4


def test_maintenance_due_message_printed(monkeypatch, tmp_path, capsys):
    """AGENT MAINTENANCE DUE message appears when counter >= maintenance_interval."""
    blocks = [_block("alpha", weight=5.0, tier="L2")]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, blocks)
    _write_weights(weights_path, blocks)
    with weights_path.open() as f:
        data = yaml.safe_load(f)
    data["meta"]["sessions_since_maintenance"] = 29
    data["meta"]["maintenance_interval"] = 30
    data["meta"]["maintenance_deferred"] = None
    with weights_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "alpha", "--loaded", "alpha", "--date", "2026-06-01"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "AGENT MAINTENANCE DUE" in out


def test_maintenance_not_due_below_threshold(monkeypatch, tmp_path, capsys):
    """No maintenance message when counter < maintenance_interval."""
    blocks = [_block("alpha", weight=5.0, tier="L2")]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, blocks)
    _write_weights(weights_path, blocks)
    with weights_path.open() as f:
        data = yaml.safe_load(f)
    data["meta"]["sessions_since_maintenance"] = 5
    data["meta"]["maintenance_interval"] = 30
    with weights_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "alpha", "--loaded", "alpha", "--date", "2026-06-01"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "AGENT MAINTENANCE DUE" not in out


def test_maintenance_reset(monkeypatch, tmp_path):
    """--maintenance-reset sets sessions_since_maintenance to 0."""
    weights_path = tmp_path / ".agent" / "weights.yaml"
    weights_path.parent.mkdir(parents=True)
    data = {
        "meta": {"schema_version": 1, "sessions_since_maintenance": 25, "maintenance_deferred": "next-start"},
        "blocks": [],
    }
    with weights_path.open("w") as f:
        yaml.dump(data, f)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--maintenance-reset"])
    weight_memory.main()
    with weights_path.open() as f:
        result = yaml.safe_load(f)
    assert result["meta"]["sessions_since_maintenance"] == 0
    assert result["meta"]["maintenance_deferred"] is None


def test_maintenance_defer_next_start(monkeypatch, tmp_path):
    """--maintenance-defer next-start writes maintenance_deferred=next-start."""
    weights_path = tmp_path / ".agent" / "weights.yaml"
    weights_path.parent.mkdir(parents=True)
    data = {"meta": {"schema_version": 1, "sessions_since_maintenance": 30}, "blocks": []}
    with weights_path.open("w") as f:
        yaml.dump(data, f)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--maintenance-defer", "next-start"])
    weight_memory.main()
    with weights_path.open() as f:
        result = yaml.safe_load(f)
    assert result["meta"]["maintenance_deferred"] == "next-start"


def test_maintenance_defer_skip_n(monkeypatch, tmp_path):
    """--maintenance-defer 5 sets counter to interval-5 so prompt fires in 5 sessions."""
    weights_path = tmp_path / ".agent" / "weights.yaml"
    weights_path.parent.mkdir(parents=True)
    defaults_path = tmp_path / "agent_docs" / "weights.default.yaml"
    defaults_path.parent.mkdir(parents=True, exist_ok=True)
    defaults_data = {"meta": {"maintenance_interval": 30, "delta": {}, "thresholds": {}}, "blocks": []}
    with defaults_path.open("w") as f:
        yaml.dump(defaults_data, f)
    with weights_path.open("w") as f:
        yaml.dump({"meta": {"schema_version": 1, "sessions_since_maintenance": 30}, "blocks": []}, f)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--maintenance-defer", "5"])
    weight_memory.main()
    with weights_path.open() as f:
        result = yaml.safe_load(f)
    assert result["meta"]["sessions_since_maintenance"] == 25  # 30 - 5


# ═════════════════════════════════════════════════════════════════════════════
# Item 2 — File-glob auto-load
# ═════════════════════════════════════════════════════════════════════════════

def _index_blocks_with_files():
    """Return index block dicts with files: globs pre-populated."""
    return [
        {
            "id": "api-models",
            "tier": "L2",
            "weight": 5.0,
            "status": "active",
            "skill": "demo-db",
            "files": ["apps/api/src/**/*.py"],
            "depends": [],
            "tags": [],
            "summary": "API SQLAlchemy models",
        },
        {
            "id": "frontend-ux",
            "tier": "L2",
            "weight": 5.0,
            "status": "active",
            "skill": "demo-frontend",
            "files": ["apps/web/src/**/*.tsx"],
            "depends": [],
            "tags": [],
            "summary": "Frontend UX blocks",
        },
        {
            "id": "no-files-block",
            "tier": "L2",
            "weight": 5.0,
            "status": "active",
            "skill": "demo-test",
            "files": [],
            "depends": [],
            "tags": [],
            "summary": "No file globs",
        },
    ]


def test_match_files_from_git_matches_glob(tmp_path, monkeypatch):
    """match_files_from_git returns block IDs when modified files match a glob."""
    # Simulate git diff returning one API file
    def fake_run(cmd, **kwargs):
        class R:
            stdout = "apps/api/src/models/order.py\n"
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_run)

    blocks = _index_blocks_with_files()
    result = weight_memory.match_files_from_git(blocks, tmp_path)
    assert "api-models" in result
    assert "frontend-ux" not in result
    assert "no-files-block" not in result


def test_match_files_from_git_no_changes(tmp_path, monkeypatch):
    """match_files_from_git returns empty set when git diff is empty."""
    def fake_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_run)
    result = weight_memory.match_files_from_git(_index_blocks_with_files(), tmp_path)
    assert result == set()


def test_match_files_from_git_subprocess_error(tmp_path, monkeypatch):
    """match_files_from_git returns empty set on subprocess failure."""
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("git not found")
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_run)
    result = weight_memory.match_files_from_git(_index_blocks_with_files(), tmp_path)
    assert result == set()


def test_file_glob_auto_adds_to_loaded(monkeypatch, tmp_path, capsys):
    """cmd_update auto-adds glob-matched block IDs to loaded and applies loaded delta."""
    blocks = [
        _block("api-models", weight=5.0),
        _block("other-block", weight=5.0),
    ]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    # Write index with files: globs
    idx_data = {
        "meta": dict(_META),
        "blocks": [
            {"id": "api-models", "weight": 5.0, "tier": "L2", "status": "active", "skill": "demo-db",
             "files": ["apps/api/**/*.py"], "depends": [], "tags": [], "summary": "API models",
             "last_used": "2026-01-01", "mem": "§1", "domain": "test"},
            {"id": "other-block", "weight": 5.0, "tier": "L2", "status": "active", "skill": "demo-test",
             "files": [], "depends": [], "tags": [], "summary": "other",
             "last_used": "2026-01-01", "mem": "§1", "domain": "test"},
        ],
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w") as f:
        yaml.dump(idx_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    _write_weights(weights_path, blocks)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = "apps/api/src/models.py\n"
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    # Note: loaded does NOT include "api-models" — file-glob should add it
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "", "--loaded", "other-block", "--date", "2026-06-01"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "FILE-GLOB MATCHES" in out
    assert "api-models" in out


# ═════════════════════════════════════════════════════════════════════════════
# Item 3 — --check-defaults threshold diff
# ═════════════════════════════════════════════════════════════════════════════

def test_check_defaults_threshold_mismatch(monkeypatch, tmp_path, capsys):
    """--check-defaults reports THRESHOLD MISMATCH when local differs from defaults."""
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    defaults_path = tmp_path / "agent_docs" / "weights.default.yaml"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    weights_path.parent.mkdir(parents=True, exist_ok=True)

    defaults_data = {
        "meta": {
            "thresholds": {"l1": 8.0, "archive": 2.0},
            "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
            "maintenance_interval": 30,
        },
        "blocks": [],
    }
    with defaults_path.open("w") as f:
        yaml.dump(defaults_data, f)

    # Local weights have different l1 threshold
    local_data = {
        "meta": {
            "schema_version": 1,
            "thresholds": {"l1": 6.0, "archive": 2.0},  # l1 differs
            "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
        },
        "blocks": [],
    }
    with index_path.open("w") as f:
        yaml.dump({"meta": dict(_META), "blocks": []}, f)
    with weights_path.open("w") as f:
        yaml.dump(local_data, f)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--check-defaults"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "THRESHOLD MISMATCH" in out
    assert "thresholds.l1" in out


def test_check_defaults_no_mismatch(monkeypatch, tmp_path, capsys):
    """--check-defaults is silent about thresholds when local matches defaults."""
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    defaults_path = tmp_path / "agent_docs" / "weights.default.yaml"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    weights_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = {
        "meta": {
            "thresholds": {"l1": 8.0, "archive": 2.0},
            "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
            "maintenance_interval": 30,
        },
        "blocks": [],
    }
    with defaults_path.open("w") as f:
        yaml.dump(cfg, f)
    with index_path.open("w") as f:
        yaml.dump({"meta": dict(_META), "blocks": []}, f)
    local_data = {"meta": {"schema_version": 1, **cfg["meta"]}, "blocks": []}
    with weights_path.open("w") as f:
        yaml.dump(local_data, f)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--check-defaults"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "THRESHOLD MISMATCH" not in out


# ═════════════════════════════════════════════════════════════════════════════
# Item 4 — --dry-run L1 preview
# ═════════════════════════════════════════════════════════════════════════════

def test_dry_run_l1_preview_shown(monkeypatch, tmp_path, capsys):
    """--dry-run prints the DRY-RUN L1 PREVIEW block instead of writing files."""
    l1_block = _block("l1-alpha", weight=9.0, tier="L1")
    l2_block = _block("l2-beta", weight=5.0, tier="L2")
    blocks = [l1_block, l2_block]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, blocks)

    # Write weights with one block above l1_thresh
    data = {
        "meta": {
            "schema_version": 1,
            "thresholds": {"l1": 8.0, "archive": 2.0},
            "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
            "sessions_since_maintenance": 0,
            "maintenance_interval": 30,
        },
        "blocks": [
            {"id": "l1-alpha", "weight": 9.0, "tier": "L1", "last_used": "2026-06-01"},
            {"id": "l2-beta", "weight": 5.0, "tier": "L2", "last_used": "2026-06-01"},
        ],
    }
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    with weights_path.open("w") as f:
        yaml.dump(data, f)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "", "--loaded", "", "--date", "2026-06-01", "--dry-run"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "DRY-RUN L1 PREVIEW" in out
    assert "l1-alpha" in out
    # l2-beta must not appear inside the preview block (it may appear in weight-changes above)
    preview_section = out[out.index("DRY-RUN L1 PREVIEW"):]
    assert "l2-beta" not in preview_section
    # Files must NOT be written
    assert not l1_path.exists()


def test_dry_run_l1_preview_null_skill_does_not_crash(monkeypatch, tmp_path, capsys):
    """--dry-run must not crash when a block has skill: null in MEMORY_INDEX.

    Regression test for TypeError: unsupported format string passed to NoneType.__format__
    when _preview_l1_blocks tries to format a None skill with {skill:25s}.
    """
    # Block with skill=None (maps to MEMORY_INDEX skill: null)
    null_skill_block = _block("no-skill-block", weight=9.0, tier="L1", skill=None)
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, [null_skill_block])

    data = {
        "meta": {
            "schema_version": 1,
            "thresholds": {"l1": 8.0, "archive": 2.0},
            "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
            "sessions_since_maintenance": 0,
            "maintenance_interval": 30,
        },
        "blocks": [{"id": "no-skill-block", "weight": 9.0, "tier": "L1", "last_used": "2026-06-01"}],
    }
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    with weights_path.open("w") as f:
        yaml.dump(data, f)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "", "--loaded", "", "--date", "2026-06-01", "--dry-run"])
    weight_memory.main()  # must not raise TypeError

    out = capsys.readouterr().out
    assert "DRY-RUN L1 PREVIEW" in out
    assert "no-skill-block" in out
    # Null skill must display as "?" not crash
    assert "skill: ?" in out


def test_dry_run_hint_after_tier_change(monkeypatch, tmp_path, capsys):
    """Non-dry-run mode prints the --dry-run hint after a tier change."""
    blocks = [_block("rising-star", weight=7.95, tier="L2")]  # will promote on +0.10 → 8.05
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, blocks)
    _write_weights(weights_path, blocks)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "rising-star", "--loaded", "rising-star", "--date", "2026-06-01"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "--dry-run" in out


# ═════════════════════════════════════════════════════════════════════════════
# Item 5 — depends: enforcement
# ═════════════════════════════════════════════════════════════════════════════

def test_resolve_deps_adds_dep():
    """resolve_deps expands loaded_ids to include direct depends: blocks."""
    index_blocks = [
        {"id": "alpha", "depends": ["beta"]},
        {"id": "beta", "depends": []},
        {"id": "gamma", "depends": []},
    ]
    expanded, auto = weight_memory.resolve_deps({"alpha"}, index_blocks)
    assert "beta" in expanded
    assert "alpha" in expanded
    assert "gamma" not in expanded
    assert any(dep_id == "beta" and parent_id == "alpha" for dep_id, parent_id in auto)


def test_resolve_deps_transitive():
    """resolve_deps follows chains: A→B→C all end up in expanded."""
    index_blocks = [
        {"id": "A", "depends": ["B"]},
        {"id": "B", "depends": ["C"]},
        {"id": "C", "depends": []},
    ]
    expanded, auto = weight_memory.resolve_deps({"A"}, index_blocks)
    assert expanded == {"A", "B", "C"}


def test_resolve_deps_cycle_safe():
    """resolve_deps handles cycles without infinite loop."""
    index_blocks = [
        {"id": "A", "depends": ["B"]},
        {"id": "B", "depends": ["A"]},  # cycle
    ]
    expanded, _ = weight_memory.resolve_deps({"A"}, index_blocks)
    assert "A" in expanded
    assert "B" in expanded


def test_resolve_deps_missing_block():
    """resolve_deps ignores depends: entries that don't exist in the index."""
    index_blocks = [{"id": "A", "depends": ["nonexistent"]}]
    expanded, auto = weight_memory.resolve_deps({"A"}, index_blocks)
    assert expanded == {"A"}  # nonexistent not added (no block to recurse into)


def test_dep_auto_included_in_output(monkeypatch, tmp_path, capsys):
    """cmd_update prints DEP AUTO-INCLUDED when a depends: block is expanded."""
    blocks_meta = [_block("alpha"), _block("dep-of-alpha")]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)

    idx_data = {
        "meta": dict(_META),
        "blocks": [
            {"id": "alpha", "weight": 5.0, "tier": "L2", "status": "active", "skill": "demo-test",
             "files": [], "depends": ["dep-of-alpha"], "tags": [], "summary": "alpha block",
             "last_used": "2026-01-01", "mem": "§1", "domain": "test"},
            {"id": "dep-of-alpha", "weight": 5.0, "tier": "L2", "status": "active", "skill": "demo-test",
             "files": [], "depends": [], "tags": [], "summary": "dep block",
             "last_used": "2026-01-01", "mem": "§1", "domain": "test"},
        ],
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w") as f:
        yaml.dump(idx_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    _write_weights(weights_path, blocks_meta)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "alpha", "--loaded", "alpha", "--date", "2026-06-01"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "DEP AUTO-INCLUDED" in out
    assert "dep-of-alpha" in out


def test_dep_gets_loaded_not_used_delta(monkeypatch, tmp_path):
    """Transitively-added dep block gets loaded_skipped delta (0.0), not loaded_used (+0.10)."""
    blocks_meta = [_block("alpha", weight=5.0), _block("dep-block", weight=5.0)]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)

    idx_data = {
        "meta": dict(_META),
        "blocks": [
            {"id": "alpha", "weight": 5.0, "tier": "L2", "status": "active", "skill": "demo-test",
             "files": [], "depends": ["dep-block"], "tags": [], "summary": "alpha",
             "last_used": "2026-01-01", "mem": "§1", "domain": "test"},
            {"id": "dep-block", "weight": 5.0, "tier": "L2", "status": "active", "skill": "demo-test",
             "files": [], "depends": [], "tags": [], "summary": "dep",
             "last_used": "2026-01-01", "mem": "§1", "domain": "test"},
        ],
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w") as f:
        yaml.dump(idx_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    _write_weights(weights_path, blocks_meta)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    # alpha is used, dep-block NOT in --loaded — it gets auto-included by deps
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "alpha", "--loaded", "alpha", "--date", "2026-06-01"])
    weight_memory.main()

    with weights_path.open() as f:
        result = yaml.safe_load(f)
    dep_block = next(b for b in result["blocks"] if b["id"] == "dep-block")
    alpha_block = next(b for b in result["blocks"] if b["id"] == "alpha")
    # dep-block should have loaded_skipped delta (0.0) → still 5.0
    assert abs(dep_block["weight"] - 5.0) < 0.01
    # alpha should have loaded_used delta (+0.10) → 5.10
    assert abs(alpha_block["weight"] - 5.10) < 0.01


# ═════════════════════════════════════════════════════════════════════════════
# Item 6 — --export-defaults and --calibrate
# ═════════════════════════════════════════════════════════════════════════════

def _write_export_fixtures(tmp_path, weights_blocks, defaults_blocks, meta_overrides=None):
    """Write minimal fixtures for export-defaults / calibrate tests."""
    defaults_path = tmp_path / "agent_docs" / "weights.default.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    defaults_path.parent.mkdir(parents=True, exist_ok=True)
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "thresholds": {"l1": 8.0, "archive": 2.0},
        "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
        "maintenance_interval": 30,
        "export_promote_threshold": 1.5,
        "export_demote_threshold": 3.0,
        "calibration_baseline_rate": 0.5,
        "calibration_window_days": 90,
    }
    if meta_overrides:
        meta.update(meta_overrides)
    with defaults_path.open("w") as f:
        yaml.dump({"meta": meta, "blocks": defaults_blocks}, f)
    with weights_path.open("w") as f:
        yaml.dump({"meta": {"schema_version": 1}, "blocks": weights_blocks}, f)
    return defaults_path, weights_path


def test_export_defaults_promote_candidate(monkeypatch, tmp_path, capsys):
    """--export-defaults reports PROMOTE CANDIDATES when local >> seed."""
    def_block = {"id": "hot-block", "seed_weight": 5.0, "skill": "demo-test", "category": "test"}
    w_block = {"id": "hot-block", "weight": 7.0, "tier": "L2", "last_used": "2026-06-01"}  # +2.0 >= 1.5 threshold
    defaults_path, weights_path = _write_export_fixtures(tmp_path, [w_block], [def_block])
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--export-defaults"])
    weight_memory.main()
    out = capsys.readouterr().out
    assert "PROMOTE CANDIDATES" in out
    assert "hot-block" in out


def test_export_defaults_seed_too_high(monkeypatch, tmp_path, capsys):
    """--export-defaults reports SEED TOO HIGH when local << seed."""
    def_block = {"id": "stale-block", "seed_weight": 8.0, "skill": "demo-test", "category": "test"}
    w_block = {"id": "stale-block", "weight": 4.5, "tier": "L2", "last_used": "2025-01-01"}  # -3.5 <= -3.0 threshold
    defaults_path, weights_path = _write_export_fixtures(tmp_path, [w_block], [def_block])
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--export-defaults"])
    weight_memory.main()
    out = capsys.readouterr().out
    assert "SEED TOO HIGH" in out
    assert "stale-block" in out


def test_export_defaults_no_action_within_threshold(monkeypatch, tmp_path, capsys):
    """--export-defaults reports no blocks outside thresholds when within bounds."""
    def_block = {"id": "steady-block", "seed_weight": 5.0, "skill": "demo-test", "category": "test"}
    w_block = {"id": "steady-block", "weight": 5.8, "tier": "L2", "last_used": "2026-06-01"}  # +0.8 < 1.5
    defaults_path, weights_path = _write_export_fixtures(tmp_path, [w_block], [def_block])
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--export-defaults"])
    weight_memory.main()
    out = capsys.readouterr().out
    assert "PROMOTE CANDIDATES" not in out
    assert "SEED TOO HIGH" not in out
    assert "No blocks outside thresholds" in out


def test_calibrate_dry_run(monkeypatch, tmp_path, capsys):
    """--calibrate --dry-run prints calibrated thresholds without writing defaults."""
    defaults_path, _ = _write_export_fixtures(tmp_path, [], [])
    # Simulate 30 merges / 2 authors over 90 days → rate = 30/2/90 ≈ 0.167/day
    call_count = [0]
    def fake_git_run(cmd, **kwargs):
        class R:
            returncode = 0
        call_count[0] += 1
        # First call: hashes; second call: author emails
        R.stdout = "\n".join(["abc123"] * 30) + "\n" if "--format=%H" in cmd else "\n".join(["a@x.com", "b@x.com"] * 15) + "\n"
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--calibrate", "--dry-run"])
    weight_memory.main()
    out = capsys.readouterr().out
    assert "calibrate" in out.lower()
    assert "dry-run: no files written" in out.lower()
    # Defaults file must NOT be modified
    with defaults_path.open() as f:
        d = yaml.safe_load(f)
    assert d["meta"]["export_promote_threshold"] == 1.5  # unchanged
    assert d["meta"]["export_demote_threshold"] == 3.0   # unchanged


def test_calibrate_writes_scaled_thresholds(monkeypatch, tmp_path, capsys):
    """--calibrate writes scaled thresholds when rate > baseline."""
    defaults_path, _ = _write_export_fixtures(tmp_path, [], [])
    def fake_git_run(cmd, **kwargs):
        class R:
            returncode = 0
        # 90 merges / 1 author over 90 days → rate = 1.0/day, baseline=0.5 → scale=2.0
        R.stdout = "\n".join(["abc123"] * 90) + "\n" if "--format=%H" in cmd else "\n".join(["solo@x.com"] * 90) + "\n"
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--calibrate"])
    weight_memory.main()
    with defaults_path.open() as f:
        d = yaml.safe_load(f)
    # scale=2.0 → promote=1.5*2=3.0, demote=3.0*2=6.0
    assert abs(d["meta"]["export_promote_threshold"] - 3.0) < 0.05
    assert abs(d["meta"]["export_demote_threshold"] - 6.0) < 0.05


def test_calibrate_scale_floor_applied(monkeypatch, tmp_path, capsys):
    """--calibrate applies SCALE_FLOOR (0.6) when merge rate is very low."""
    defaults_path, _ = _write_export_fixtures(tmp_path, [], [])
    def fake_git_run(cmd, **kwargs):
        class R:
            returncode = 0
        # 1 merge / 5 authors over 90 days → very low rate → scale should floor at 0.6
        R.stdout = "abc123\n" if "--format=%H" in cmd else "\n".join([f"u{i}@x.com" for i in range(5)]) + "\n"
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--calibrate"])
    weight_memory.main()
    with defaults_path.open() as f:
        d = yaml.safe_load(f)
    # floor=0.6 → promote=1.5*0.6=0.9, demote=3.0*0.6=1.8
    assert abs(d["meta"]["export_promote_threshold"] - 0.9) < 0.05
    assert abs(d["meta"]["export_demote_threshold"] - 1.8) < 0.05


def test_calibrate_scale_ceiling_applied(monkeypatch, tmp_path, capsys):
    """--calibrate applies SCALE_CEILING (3.0) when merge rate is very high."""
    defaults_path, _ = _write_export_fixtures(tmp_path, [], [])
    def fake_git_run(cmd, **kwargs):
        class R:
            returncode = 0
        # 270 merges / 1 author over 90 days → rate=3.0/day → scale=6.0 → clamped to 3.0
        R.stdout = "\n".join(["abc"] * 270) + "\n" if "--format=%H" in cmd else "\n".join(["a@x.com"] * 270) + "\n"
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--calibrate"])
    weight_memory.main()
    with defaults_path.open() as f:
        d = yaml.safe_load(f)
    # ceiling=3.0 → promote=1.5*3.0=4.5, demote=3.0*3.0=9.0
    assert abs(d["meta"]["export_promote_threshold"] - 4.5) < 0.05
    assert abs(d["meta"]["export_demote_threshold"] - 9.0) < 0.05


# ═════════════════════════════════════════════════════════════════════════════
# Additional missing tests — audit pass (Items 1, 2, 3, 4, 5, 6)
# ═════════════════════════════════════════════════════════════════════════════

# ── Item 1 additions ──────────────────────────────────────────────────────────

def test_maintenance_defer_next_end(monkeypatch, tmp_path):
    """--maintenance-defer next-end writes maintenance_deferred=next-end."""
    weights_path = tmp_path / ".agent" / "weights.yaml"
    weights_path.parent.mkdir(parents=True)
    data = {"meta": {"schema_version": 1, "sessions_since_maintenance": 30}, "blocks": []}
    with weights_path.open("w") as f:
        yaml.dump(data, f)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--maintenance-defer", "next-end"])
    weight_memory.main()
    with weights_path.open() as f:
        result = yaml.safe_load(f)
    assert result["meta"]["maintenance_deferred"] == "next-end"


def test_maintenance_interval_configurable(monkeypatch, tmp_path, capsys):
    """maintenance_interval=10 fires the MAINTENANCE DUE notice at session 10, not 30."""
    blocks = [_block("alpha", weight=5.0)]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    defaults_path = tmp_path / "agent_docs" / "weights.default.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, blocks)
    _write_weights(weights_path, blocks)

    # Custom defaults with interval=10
    defaults_data = {
        "meta": {
            "thresholds": {"l1": 8.0, "archive": 2.0},
            "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
            "maintenance_interval": 10,
        },
        "blocks": [{"id": "alpha", "seed_weight": 5.0, "tier": "L2", "skill": "demo-test",
                     "status": "active", "category": "test", "reason": ""}],
    }
    with defaults_path.open("w") as f:
        yaml.dump(defaults_data, f)

    with weights_path.open() as f:
        data = yaml.safe_load(f)
    # Counter at 9; interval is 10 → fires on this run (counter becomes 10)
    data["meta"]["sessions_since_maintenance"] = 9
    data["meta"]["maintenance_deferred"] = None
    with weights_path.open("w") as f:
        yaml.dump(data, f)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "alpha", "--loaded", "alpha", "--date", "2026-06-01"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "AGENT MAINTENANCE DUE" in out
    with weights_path.open() as f:
        result = yaml.safe_load(f)
    assert result["meta"]["sessions_since_maintenance"] == 10


# ── Item 2 additions ──────────────────────────────────────────────────────────

def test_file_glob_does_not_elevate_to_used(monkeypatch, tmp_path):
    """Glob-matched block is added to loaded, not used — gets loaded_skipped delta (0.0)."""
    blocks = [_block("api-models", weight=5.0), _block("other-block", weight=5.0)]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)

    idx_data = {
        "meta": dict(_META),
        "blocks": [
            {"id": "api-models", "weight": 5.0, "tier": "L2", "status": "active", "skill": "demo-db",
             "files": ["apps/api/**/*.py"], "depends": [], "tags": [], "summary": "API models",
             "last_used": "2026-01-01", "mem": "§1", "domain": "test"},
            {"id": "other-block", "weight": 5.0, "tier": "L2", "status": "active", "skill": "demo-test",
             "files": [], "depends": [], "tags": [], "summary": "other",
             "last_used": "2026-01-01", "mem": "§1", "domain": "test"},
        ],
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w") as f:
        yaml.dump(idx_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    _write_weights(weights_path, blocks)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = "apps/api/src/models.py\n"
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    # api-models is NOT in --used or --loaded — glob auto-adds it to loaded only
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "", "--loaded", "", "--date", "2026-06-01"])
    weight_memory.main()

    with weights_path.open() as f:
        result = yaml.safe_load(f)
    api_block = next(b for b in result["blocks"] if b["id"] == "api-models")
    # loaded_skipped delta = 0.0 → weight stays 5.0 (not 5.10 which would indicate used delta)
    assert abs(api_block["weight"] - 5.0) < 0.01, f"Expected 5.0, got {api_block['weight']}"


# ── Item 3 additions ──────────────────────────────────────────────────────────

def test_check_defaults_delta_mismatch_reported(monkeypatch, tmp_path, capsys):
    """--check-defaults reports THRESHOLD MISMATCH when a delta key (loaded_used) differs."""
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    defaults_path = tmp_path / "agent_docs" / "weights.default.yaml"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    weights_path.parent.mkdir(parents=True, exist_ok=True)

    defaults_data = {
        "meta": {
            "thresholds": {"l1": 8.0, "archive": 2.0},
            "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
            "maintenance_interval": 30,
        },
        "blocks": [],
    }
    with defaults_path.open("w") as f:
        yaml.dump(defaults_data, f)
    with index_path.open("w") as f:
        yaml.dump({"meta": dict(_META), "blocks": []}, f)

    # Local weights have different loaded_used delta
    local_data = {
        "meta": {
            "schema_version": 1,
            "thresholds": {"l1": 8.0, "archive": 2.0},
            "delta": {"loaded_used": 0.20, "loaded_skipped": 0.00, "not_loaded": -0.05},  # loaded_used differs
        },
        "blocks": [],
    }
    with weights_path.open("w") as f:
        yaml.dump(local_data, f)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--check-defaults"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "THRESHOLD MISMATCH" in out
    assert "delta.loaded_used" in out


# ── Item 4 additions ──────────────────────────────────────────────────────────

def _make_dry_run_preview_fixtures(tmp_path):
    """Return (index_path, weights_path, l1_path) for dry-run L1 preview tests."""
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    weights_path.parent.mkdir(parents=True, exist_ok=True)

    idx_data = {
        "meta": dict(_META),
        "blocks": [
            {"id": "high-block", "weight": 9.5, "tier": "L1", "status": "active",
             "skill": "demo-db", "files": [], "depends": [], "summary": "DB summary text",
             "tags": ["database", "migration", "alembic", "asyncpg"],
             "last_used": "2026-06-01", "mem": "§1", "domain": "test"},
            {"id": "mid-block", "weight": 8.2, "tier": "L1", "status": "active",
             "skill": "demo-api", "files": [], "depends": [], "summary": "API summary text",
             "tags": ["endpoint", "fastapi"],
             "last_used": "2026-06-01", "mem": "§1", "domain": "test"},
            {"id": "low-block", "weight": 3.0, "tier": "L2", "status": "active",
             "skill": "demo-test", "files": [], "depends": [], "summary": "Low block",
             "tags": ["test"],
             "last_used": "2026-06-01", "mem": "§1", "domain": "test"},
        ],
    }
    with index_path.open("w") as f:
        yaml.dump(idx_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    w_data = {
        "meta": {
            "schema_version": 1,
            "thresholds": {"l1": 8.0, "archive": 2.0},
            "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
            "sessions_since_maintenance": 0,
            "maintenance_interval": 30,
        },
        "blocks": [
            {"id": "high-block", "weight": 9.5, "tier": "L1", "last_used": "2026-06-01"},
            {"id": "mid-block", "weight": 8.2, "tier": "L1", "last_used": "2026-06-01"},
            {"id": "low-block", "weight": 3.0, "tier": "L2", "last_used": "2026-06-01"},
        ],
    }
    with weights_path.open("w") as f:
        yaml.dump(w_data, f)

    return index_path, weights_path, l1_path


def test_dry_run_l1_preview_shows_skill_and_summary(monkeypatch, tmp_path, capsys):
    """Each L1 block in the dry-run preview shows its skill name and summary."""
    index_path, weights_path, l1_path = _make_dry_run_preview_fixtures(tmp_path)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "", "--loaded", "", "--date", "2026-06-01", "--dry-run"])
    weight_memory.main()

    out = capsys.readouterr().out
    preview = out[out.index("DRY-RUN L1 PREVIEW"):]
    assert "demo-db" in preview
    assert "DB summary text" in preview
    assert "demo-api" in preview
    assert "API summary text" in preview


def test_dry_run_l1_preview_sorted_by_weight_descending(monkeypatch, tmp_path, capsys):
    """Blocks in the dry-run L1 preview appear highest weight first."""
    index_path, weights_path, l1_path = _make_dry_run_preview_fixtures(tmp_path)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "", "--loaded", "", "--date", "2026-06-01", "--dry-run"])
    weight_memory.main()

    out = capsys.readouterr().out
    preview = out[out.index("DRY-RUN L1 PREVIEW"):]
    pos_high = preview.index("high-block")
    pos_mid = preview.index("mid-block")
    assert pos_high < pos_mid, "high-block (9.5) should appear before mid-block (8.2)"


def test_no_tier_change_no_dry_run_hint(monkeypatch, tmp_path, capsys):
    """No --dry-run hint is printed when there are no tier changes."""
    blocks = [_block("stable", weight=5.0, tier="L2")]  # weight stays at 5.0 (not_loaded: -0.05 → 4.95)
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, blocks)
    _write_weights(weights_path, blocks)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    # stable is not loaded — decays slightly but stays L2 → no tier change
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "", "--loaded", "", "--date", "2026-06-01"])
    weight_memory.main()

    out = capsys.readouterr().out
    # Should NOT contain the dry-run hint since no tier changes occurred
    assert "Run with --dry-run to preview" not in out


# ── Item 5 additions ──────────────────────────────────────────────────────────

def test_dep_not_added_when_parent_not_loaded(monkeypatch, tmp_path):
    """A dep block is NOT auto-included when its parent is not in --loaded."""
    blocks_meta = [_block("parent", weight=5.0), _block("child", weight=5.0)]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)

    idx_data = {
        "meta": dict(_META),
        "blocks": [
            {"id": "parent", "weight": 5.0, "tier": "L2", "status": "active", "skill": "demo-test",
             "files": [], "depends": ["child"], "tags": [], "summary": "parent block",
             "last_used": "2026-01-01", "mem": "§1", "domain": "test"},
            {"id": "child", "weight": 5.0, "tier": "L2", "status": "active", "skill": "demo-test",
             "files": [], "depends": [], "tags": [], "summary": "child block",
             "last_used": "2026-01-01", "mem": "§1", "domain": "test"},
        ],
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w") as f:
        yaml.dump(idx_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    _write_weights(weights_path, blocks_meta)

    def fake_git_run(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    # parent NOT in --loaded → child should NOT be auto-included
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "", "--loaded", "", "--date", "2026-06-01"])
    weight_memory.main()

    with weights_path.open() as f:
        result = yaml.safe_load(f)
    child_block = next(b for b in result["blocks"] if b["id"] == "child")
    # child should have NOT been promoted to loaded; gets not_loaded delta → 5.0 - 0.05 = 4.95
    assert abs(child_block["weight"] - 4.95) < 0.01, f"Expected 4.95 (decay), got {child_block['weight']}"


# ── Item 6 export additions ───────────────────────────────────────────────────

def test_export_defaults_seed_too_high_recent(monkeypatch, tmp_path, capsys):
    """SEED TOO HIGH with recent last_used gets 'review content' sub-label."""
    import datetime
    recent_date = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    def_block = {"id": "recent-block", "seed_weight": 8.0, "skill": "demo-test", "category": "test"}
    w_block = {"id": "recent-block", "weight": 4.0, "tier": "L2", "last_used": recent_date}  # -4.0 below seed
    defaults_path, weights_path = _write_export_fixtures(tmp_path, [w_block], [def_block])
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--export-defaults"])
    weight_memory.main()
    out = capsys.readouterr().out
    assert "SEED TOO HIGH" in out
    assert "review content" in out


def test_export_defaults_suggested_seed_conservative(monkeypatch, tmp_path, capsys):
    """Suggested seed = round(local - 0.5, 1), not the local weight itself."""
    def_block = {"id": "growing-block", "seed_weight": 5.0, "skill": "demo-test", "category": "test"}
    w_block = {"id": "growing-block", "weight": 7.4, "tier": "L1", "last_used": "2026-06-01"}  # +2.4 >= 1.5
    defaults_path, weights_path = _write_export_fixtures(tmp_path, [w_block], [def_block])
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--export-defaults"])
    weight_memory.main()
    out = capsys.readouterr().out
    # suggested = round(7.4 - 0.5, 1) = 6.9 — must appear in the promote section
    assert "6.9" in out
    # The exact local weight (7.4) should NOT appear in the suggested-seed column
    # (it appears in the local-weight column, but that's separate from the suggested column)
    # Verify by parsing: the row format is "local  seed  suggested  ..."
    # We check the suggested column entry (6.9) differs from the local weight (7.4)
    assert "7.4" in out  # local weight column — expected
    # confirmed: suggested is 6.9, not 7.4 (which would mean no discounting was applied)
    promote_section = out[out.index("PROMOTE CANDIDATES"):]
    row_line = next(ln for ln in promote_section.splitlines() if "growing-block" in ln)
    # columns: block_id, skill, local, seed, suggested, last_used
    parts = row_line.split()
    # last three numeric fields are local, seed, suggested
    local_val = float(parts[-4])
    seed_val = float(parts[-3])
    suggested_val = float(parts[-2])
    assert abs(local_val - 7.4) < 0.05
    assert abs(seed_val - 5.0) < 0.05
    assert abs(suggested_val - 6.9) < 0.05
    assert suggested_val < local_val  # conservative: suggested < local


# ── Item 6 calibrate additions ────────────────────────────────────────────────

def test_calibrate_moderate_cadence(monkeypatch, tmp_path, capsys):
    """--calibrate with moderate rate (1.5 merges/dev/week) produces scale between floor/ceiling."""
    defaults_path, _ = _write_export_fixtures(tmp_path, [], [])
    def fake_git_run(cmd, **kwargs):
        class R:
            returncode = 0
        # 27 merges / 2 authors / 90 days → rate=0.15/day per dev → scale=0.15/0.5=0.30 → floored to 0.6
        # Let's use 45 merges / 2 authors / 90 days → rate=0.25/dev/day → scale=0.5 → floored at 0.6
        # Use 90 merges / 2 authors / 90 days → rate=0.5/dev/day → scale=1.0 (between floor 0.6 and ceil 3.0)
        R.stdout = "\n".join(["abc123"] * 90) + "\n" if "--format=%H" in cmd else "\n".join(["a@x.com", "b@x.com"] * 45) + "\n"
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--calibrate"])
    weight_memory.main()
    with defaults_path.open() as f:
        d = yaml.safe_load(f)
    # 90 merges / 2 authors / 90 days → per_dev_rate=0.5 → scale=1.0 → promote=1.5, demote=3.0
    promote = d["meta"]["export_promote_threshold"]
    demote = d["meta"]["export_demote_threshold"]
    assert weight_memory._CALIBRATE_SCALE_FLOOR <= promote / 1.5 <= weight_memory._CALIBRATE_SCALE_CEILING
    assert weight_memory._CALIBRATE_SCALE_FLOOR <= demote / 3.0 <= weight_memory._CALIBRATE_SCALE_CEILING


def test_calibrate_multi_author_normalizes_per_dev(monkeypatch, tmp_path, capsys):
    """--calibrate divides total merges by distinct author count for per-dev rate."""
    defaults_path, _ = _write_export_fixtures(tmp_path, [], [])
    # 5 authors × 90 merges → ~0.2/dev/day → scale = 0.4 → floored to 0.6
    def fake_git_run(cmd, **kwargs):
        class R:
            returncode = 0
        if "--format=%H" in cmd:
            R.stdout = "\n".join(["abc"] * 90) + "\n"
        else:
            R.stdout = "\n".join([f"user{i % 5}@x.com" for i in range(90)]) + "\n"
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_git_run)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--calibrate"])
    weight_memory.main()
    with defaults_path.open() as f:
        d = yaml.safe_load(f)
    # 90 merges / 5 authors / 90 days = 0.2/dev/day → scale=0.4 → clamped to floor 0.6
    # promote = 1.5 * 0.6 = 0.9
    assert abs(d["meta"]["export_promote_threshold"] - 0.9) < 0.05


def test_seed_calls_calibrate_internally(monkeypatch, tmp_path, capsys):
    """--seed triggers calibration automatically, writing thresholds to defaults."""
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    defaults_path = tmp_path / "agent_docs" / "weights.default.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)

    blocks = [_block("alpha", weight=5.0)]
    _write_index(index_path, blocks)
    seed_meta = {
        "thresholds": {"l1": 8.0, "archive": 2.0},
        "delta": {"loaded_used": 0.10, "loaded_skipped": 0.00, "not_loaded": -0.05},
        "maintenance_interval": 30,
        "export_promote_threshold": 1.5,
        "export_demote_threshold": 3.0,
        "calibration_baseline_rate": 0.5,
        "calibration_window_days": 90,
    }
    with defaults_path.open("w") as f:
        yaml.dump({"meta": seed_meta, "blocks": [
            {"id": "alpha", "seed_weight": 5.0, "tier": "L2", "skill": "demo-test",
             "status": "active", "category": "test", "reason": ""}
        ]}, f)

    calibrate_called = [False]
    def fake_calibrate(dry_run):
        calibrate_called[0] = True
        # don't actually run git commands in test
    monkeypatch.setattr(weight_memory, "cmd_calibrate", fake_calibrate)
    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    # Patch _bootstrap_merge_driver to avoid git config side effects
    monkeypatch.setattr(weight_memory, "_bootstrap_merge_driver", lambda: None)
    monkeypatch.setattr(sys, "argv", ["wm", "--seed"])
    weight_memory.main()

    assert calibrate_called[0], "--seed must call cmd_calibrate internally"


# ═════════════════════════════════════════════════════════════════════════════
# Item 9 — _bootstrap_merge_driver
# ═════════════════════════════════════════════════════════════════════════════

def test_bootstrap_merge_driver_creates_files_when_absent(monkeypatch, tmp_path, capsys):
    """.gitconfig and .gitattributes are created when absent; git config is wired."""
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)

    git_config_calls = []
    def fake_run(cmd, **kwargs):
        git_config_calls.append(cmd)
        class R:
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_run)

    weight_memory._bootstrap_merge_driver()

    gitconfig = tmp_path / ".gitconfig"
    gitattributes = tmp_path / ".gitattributes"
    assert gitconfig.exists(), ".gitconfig must be created"
    assert gitattributes.exists(), ".gitattributes must be created"
    assert '[merge "union"]' in gitconfig.read_text()
    assert "merge=union" in gitattributes.read_text()
    assert "agent_docs/**/*.yaml" in gitattributes.read_text()

    # git config --local include.path must have been called
    assert any("include.path" in " ".join(c) for c in git_config_calls), \
        "git config --local include.path must be wired"

    out = capsys.readouterr().out
    assert "Created" in out


def test_bootstrap_merge_driver_skips_existing_files(monkeypatch, tmp_path, capsys):
    """Idempotent: existing .gitconfig and .gitattributes are not overwritten."""
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)

    original_gitconfig = "# my custom content\n"
    original_gitattributes = "# my custom attributes\n"
    (tmp_path / ".gitconfig").write_text(original_gitconfig)
    (tmp_path / ".gitattributes").write_text(original_gitattributes)

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 0
        return R()
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_run)

    weight_memory._bootstrap_merge_driver()

    assert (tmp_path / ".gitconfig").read_text() == original_gitconfig, \
        "Existing .gitconfig must not be overwritten"
    assert (tmp_path / ".gitattributes").read_text() == original_gitattributes, \
        "Existing .gitattributes must not be overwritten"

    out = capsys.readouterr().out
    assert "already exists" in out


def test_bootstrap_merge_driver_git_config_failure_is_handled(monkeypatch, tmp_path, capsys):
    """git config failure prints a warning and does not propagate an exception."""
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)

    def fake_run(cmd, **kwargs):
        raise weight_memory.subprocess.CalledProcessError(1, cmd)
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_run)

    # Must not raise
    weight_memory._bootstrap_merge_driver()

    # Files are created before the git config call, so they must exist
    assert (tmp_path / ".gitconfig").exists(), ".gitconfig should still be written even if git config fails"


def test_bootstrap_merge_driver_no_git_binary(monkeypatch, tmp_path, capsys):
    """git not installed: FileNotFoundError is caught; warning printed; no exception raised."""
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("git not found")
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_run)

    weight_memory._bootstrap_merge_driver()  # must not raise

    assert (tmp_path / ".gitconfig").exists()
    assert (tmp_path / ".gitattributes").exists()


# ═════════════════════════════════════════════════════════════════════════════
# Item 6 addition — --calibrate git failure fallback
# ═════════════════════════════════════════════════════════════════════════════

def test_calibrate_git_failure_falls_back_to_baseline(monkeypatch, tmp_path, capsys):
    """When git is unavailable, --calibrate falls back to baseline_rate (scale=1.0) and still writes."""
    defaults_path, _ = _write_export_fixtures(tmp_path, [], [])

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("git not found")
    monkeypatch.setattr(weight_memory.subprocess, "run", fake_run)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--calibrate"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "WARNING" in out
    assert "git command failed" in out

    # scale_factor = baseline_rate / baseline_rate = 1.0 → thresholds unchanged from defaults
    with defaults_path.open() as f:
        d = yaml.safe_load(f)
    assert abs(d["meta"]["export_promote_threshold"] - 1.5) < 0.05, \
        "Fallback scale=1.0 should leave promote threshold at default (1.5)"
    assert abs(d["meta"]["export_demote_threshold"] - 3.0) < 0.05, \
        "Fallback scale=1.0 should leave demote threshold at default (3.0)"


# ═════════════════════════════════════════════════════════════════════════════
# Item 7 — auto-generated File → Skill routing table
# ═════════════════════════════════════════════════════════════════════════════

def _index_with_file_globs(tmp_path: Path) -> Path:
    """Write a minimal MEMORY_INDEX.yaml with files: globs to tmp_path."""
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "meta": {"format_version": 4.1, "updated": "2026-01-01"},
        "blocks": [
            {
                "id": "db-models",
                "skill": "demo-db",
                "files": ["apps/api/src/models/**", "apps/api/alembic/**"],
                "depends": [], "tags": [], "summary": "DB models", "status": "active",
                "mem": "§1", "domain": "db",
            },
            {
                "id": "frontend-ux",
                "skill": "demo-frontend",
                "files": ["apps/web/src/**/*.tsx", "apps/web/src/**/*.ts"],
                "depends": [], "tags": [], "summary": "Frontend UX", "status": "active",
                "mem": "§2", "domain": "web",
            },
            {
                "id": "background-worker",
                "skill": "demo-worker",
                "files": ["apps/web/src/**/*.tsx"],   # shares a glob with frontend-ux
                "depends": [], "tags": [], "summary": "Background worker", "status": "active",
                "mem": "§3", "domain": "worker",
            },
            {
                "id": "l1-block-no-skill",
                "skill": None,  # L1 blocks have no skill — must be excluded
                "files": ["agent_docs/**"],
                "depends": [], "tags": [], "summary": "L1 block", "status": "active",
                "mem": "§0", "domain": "cicd",
            },
            {
                "id": "no-files-block",
                "skill": "demo-test",
                "files": [],   # empty files — must be excluded
                "depends": [], "tags": [], "summary": "No globs", "status": "active",
                "mem": "§4", "domain": "test",
            },
        ],
    }
    with index_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return index_path


def test_generate_routing_table_basic(tmp_path):
    """_generate_routing_table returns a markdown table with correct rows."""
    index_path = _index_with_file_globs(tmp_path)
    with index_path.open() as f:
        index_blocks = yaml.safe_load(f)["blocks"]
    result = weight_memory._generate_routing_table(index_blocks)
    assert "File → Skill Routing Table" in result
    assert "`apps/api/src/models/**`" in result
    assert "`demo-db`" in result
    assert "`apps/web/src/**/*.tsx`" in result
    assert "`demo-frontend`" in result


def test_generate_routing_table_skips_null_skill(tmp_path):
    """Blocks with skill=None are excluded from the routing table."""
    index_path = _index_with_file_globs(tmp_path)
    with index_path.open() as f:
        index_blocks = yaml.safe_load(f)["blocks"]
    result = weight_memory._generate_routing_table(index_blocks)
    assert "agent_docs/**" not in result, "L1 block with skill=None must not appear"


def test_generate_routing_table_skips_empty_files(tmp_path):
    """Blocks with files=[] produce no rows in the routing table."""
    index_path = _index_with_file_globs(tmp_path)
    with index_path.open() as f:
        index_blocks = yaml.safe_load(f)["blocks"]
    result = weight_memory._generate_routing_table(index_blocks)
    assert "`demo-test`" not in result, "Block with empty files: must not appear"


def test_generate_routing_table_merges_skills_for_shared_glob(tmp_path):
    """A glob shared by two blocks with different skills lists both skills on one row."""
    index_path = _index_with_file_globs(tmp_path)
    with index_path.open() as f:
        index_blocks = yaml.safe_load(f)["blocks"]
    result = weight_memory._generate_routing_table(index_blocks)
    # apps/web/src/**/*.tsx is in both frontend-ux (demo-frontend) and background-worker (demo-worker)
    tsx_row = next(ln for ln in result.splitlines() if "apps/web/src/**/*.tsx" in ln)
    assert "`demo-frontend`" in tsx_row
    assert "`demo-worker`" in tsx_row


def test_generate_routing_table_empty_when_no_globs():
    """_generate_routing_table returns empty string when no blocks have file globs."""
    blocks = [
        {"id": "a", "skill": "demo-db", "files": []},
        {"id": "b", "skill": None, "files": ["some/**"]},
    ]
    result = weight_memory._generate_routing_table(blocks)
    assert result == ""


def test_generate_routing_table_sorted_by_pattern(tmp_path):
    """Rows in the routing table are sorted by file pattern (alphabetically)."""
    index_path = _index_with_file_globs(tmp_path)
    with index_path.open() as f:
        index_blocks = yaml.safe_load(f)["blocks"]
    result = weight_memory._generate_routing_table(index_blocks)
    # Extract pattern column from data rows (skip header rows)
    table_lines = [ln for ln in result.splitlines() if ln.startswith("| `")]
    patterns = [ln.split("|")[1].strip().strip("`") for ln in table_lines]
    assert patterns == sorted(patterns), "Routing table must be sorted by file pattern"


def test_generate_l1_context_includes_routing_table(monkeypatch, tmp_path):
    """generate_l1_context writes the routing table section into L1_CONTEXT.md."""
    index_path = _index_with_file_globs(tmp_path)
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)

    # Write a minimal defaults file
    defaults_path = tmp_path / "agent_docs" / "weights.default.yaml"
    with defaults_path.open("w") as f:
        yaml.dump({"meta": {"meridian_version": "v4.6", "thresholds": {"l1": 8.0, "archive": 2.0},
                             "delta": {}}, "blocks": []}, f)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "BLOCK_SOURCES", [])  # no block content needed

    weights_data = {"blocks": []}  # no L1 blocks — just test routing table emission
    weight_memory.generate_l1_context(weights_data, l1_thresh=8.0, dry_run=False)

    content = l1_path.read_text()
    assert "File → Skill Routing Table" in content
    assert "`demo-db`" in content
    assert "`demo-frontend`" in content
    # null-skill block must not appear
    assert "agent_docs/**" not in content


def test_generate_l1_context_routing_table_absent_when_no_globs(monkeypatch, tmp_path):
    """If no MEMORY_INDEX blocks have file globs, no routing table section is emitted."""
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    defaults_path = tmp_path / "agent_docs" / "weights.default.yaml"
    with index_path.open("w") as f:
        yaml.dump({"meta": {}, "blocks": [
            {"id": "x", "skill": "demo-db", "files": [], "depends": [],
             "tags": [], "summary": "x", "status": "active", "mem": "§1", "domain": "db"},
        ]}, f)
    with defaults_path.open("w") as f:
        yaml.dump({"meta": {"meridian_version": "v4.6", "thresholds": {"l1": 8.0,
                             "archive": 2.0}, "delta": {}}, "blocks": []}, f)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(weight_memory, "BLOCK_SOURCES", [])

    weight_memory.generate_l1_context({"blocks": []}, l1_thresh=8.0, dry_run=False)
    content = l1_path.read_text()
    assert "Routing Table" not in content


# ── match_files_from_git — git ref tests ──────────────────────────────────────

def test_match_files_from_git_uses_upstream_ref(tmp_path, monkeypatch):
    """match_files_from_git calls git diff with @{u}..HEAD as the primary ref."""
    calls: list[list] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        class R:
            stdout = "apps/api/src/models/order.py\n"
            returncode = 0
        return R()

    monkeypatch.setattr(weight_memory.subprocess, "run", fake_run)
    weight_memory.match_files_from_git(_index_blocks_with_files(), tmp_path)

    assert len(calls) == 1
    assert calls[0] == ["git", "diff", "--name-only", "@{u}..HEAD"]


def test_match_files_from_git_falls_back_to_head_when_no_upstream(tmp_path, monkeypatch):
    """match_files_from_git falls back to HEAD diff when upstream is unavailable."""
    calls: list[list] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        class R:
            # First call (@{u}..HEAD) fails — no upstream configured
            returncode = 1 if "@{u}..HEAD" in cmd else 0
            stdout = "apps/api/src/models/order.py\n" if returncode == 0 else ""
        return R()

    monkeypatch.setattr(weight_memory.subprocess, "run", fake_run)
    result = weight_memory.match_files_from_git(_index_blocks_with_files(), tmp_path)

    assert len(calls) == 2
    assert calls[0] == ["git", "diff", "--name-only", "@{u}..HEAD"]
    assert calls[1] == ["git", "diff", "--name-only", "HEAD"]
    assert "api-models" in result


# ── maintenance_deferred — one-time suppression tests ─────────────────────────

def test_maintenance_deferred_suppresses_notice_and_clears(monkeypatch, tmp_path, capsys):
    """When maintenance_deferred is set, notice is suppressed and flag is cleared."""
    blocks = [_block("alpha", weight=5.0, tier="L2")]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, blocks)
    _write_weights(weights_path, blocks)
    with weights_path.open() as f:
        data = yaml.safe_load(f)
    data["meta"]["sessions_since_maintenance"] = 29  # reaches 30 after increment
    data["meta"]["maintenance_interval"] = 30
    data["meta"]["maintenance_deferred"] = "next-end"
    with weights_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "alpha", "--loaded", "alpha", "--date", "2026-06-01"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "AGENT MAINTENANCE DUE" not in out
    assert "deferred" in out.lower()

    # Flag should be cleared in the written file
    with weights_path.open() as f:
        saved = yaml.safe_load(f)
    assert saved["meta"]["maintenance_deferred"] is None


def test_maintenance_deferred_dry_run_does_not_clear_flag(monkeypatch, tmp_path, capsys):
    """In dry-run mode, maintenance_deferred suppresses the notice but the flag is NOT written."""
    blocks = [_block("alpha", weight=5.0, tier="L2")]
    index_path = tmp_path / "agent_docs" / "MEMORY_INDEX.yaml"
    weights_path = tmp_path / ".agent" / "weights.yaml"
    l1_path = tmp_path / "agent_docs" / "L1_CONTEXT.md"
    l1_path.parent.mkdir(parents=True, exist_ok=True)
    _write_index(index_path, blocks)
    _write_weights(weights_path, blocks)
    with weights_path.open() as f:
        data = yaml.safe_load(f)
    data["meta"]["sessions_since_maintenance"] = 29
    data["meta"]["maintenance_interval"] = 30
    data["meta"]["maintenance_deferred"] = "next-start"
    with weights_path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    monkeypatch.setattr(weight_memory, "INDEX_PATH", index_path)
    monkeypatch.setattr(weight_memory, "WEIGHTS_PATH", weights_path)
    monkeypatch.setattr(weight_memory, "L1_PATH", l1_path)
    monkeypatch.setattr(weight_memory, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["wm", "--used", "alpha", "--loaded", "alpha", "--date", "2026-06-01", "--dry-run"])
    weight_memory.main()

    out = capsys.readouterr().out
    assert "AGENT MAINTENANCE DUE" not in out

    # Flag should still be set — dry-run must not write
    with weights_path.open() as f:
        saved = yaml.safe_load(f)
    assert saved["meta"]["maintenance_deferred"] == "next-start"
