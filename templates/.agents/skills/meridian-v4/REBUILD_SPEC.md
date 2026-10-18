# weight_memory.py — Rebuild Specification

> **When to read this file:** Only when `.agents/skills/meridian-v4/weight_memory.py` is missing, corrupted,
> or needs to be rebuilt from scratch. For normal memory operations, use `SKILL.md`.

This specification is the single source of truth for rebuilding `.agents/skills/meridian-v4/weight_memory.py`.
After implementing, keep this file in sync with any script changes.

---

### Purpose

Session-end weight update script for the Meridian agent context and memory system.
Updates block weights in `agent_docs/MEMORY_INDEX.yaml` based on session usage, applies
decay to unloaded blocks, reclassifies tiers, and runs integrity and health checks.

The script version label (used in help text, docstring, and `_weights_header()`) must
match `meta.meridian_version` in `agent_docs/weights.default.yaml`. Update both together
whenever the version is bumped.

---

### File Location

```
.agents/skills/meridian-v4/weight_memory.py
```

`REPO_ROOT` is resolved at import time by walking up from `__file__` until
`agent_docs/MEMORY_INDEX.yaml` is found. This is cross-platform (pathlib),
agent-agnostic, and survives script relocation or multi-root workspaces.

```python
def _find_repo_root() -> Path:
    sentinel = Path("agent_docs") / "MEMORY_INDEX.yaml"
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / sentinel).exists():
            return candidate
    raise RuntimeError(
        f"Cannot locate Meridian repo root from {here}. "
        f"Expected to find '{sentinel}' in an ancestor directory."
    )

REPO_ROOT = _find_repo_root()
INDEX_PATH = REPO_ROOT / "agent_docs" / "MEMORY_INDEX.yaml"
```

---

### CLI Interface

```
python .agents/skills/meridian-v4/weight_memory.py \
  --used   "block-a,block-b"            # blocks loaded AND actively used
  --loaded "block-a,block-b,block-c"    # superset: all blocks loaded
  --date   "YYYY-MM-DD"                 # session date (default: today)
  --dry-run                             # print changes; do not write
```

- `--used` and `--loaded` accept comma-separated block IDs, no spaces required.
- If a block ID appears in `--used` but not in `--loaded`: warn on stderr and auto-add
  to `--loaded`.
- `--date` defaults to `str(date.today())`. Parse with `date.fromisoformat()`; if
  invalid, fall back to `date.today()`.

Additional commands: `--seed`, `--generate-l1`, `--check-defaults`, `--migrate` are
also implemented. Their behavior is described in `SKILL.md` (First-Boot and Migration
sections). Run `--help` for the full list.

---

### Block Content Extraction (`extract_block_content`)

Used by `generate_l1_context()` to read a block's content from its annotated source.

**Constants (module-level):**
```python
BLOCK_START_RE    = re.compile(r"<!--\s*block:\s*(\S+?)\s*[\|>]")
BLOCK_END_RE      = re.compile(r"<!--\s*/block\s*-->")
L1_SUMMARY_END_RE = re.compile(r"<!--\s*/l1-summary\s*-->")
```

**Logic:**
Scan `BLOCK_SOURCES` for the block ID. Collect lines from `<!-- block: ID -->` to
`<!-- /block -->`.

If `<!-- /l1-summary -->` is encountered before `<!-- /block -->`:
- Stop collecting at that point (skip the marker line itself)
- When `<!-- /block -->` is reached, return only the collected lines with a synthetic
  `<!-- /block -->` appended
- Content between `<!-- /l1-summary -->` and `<!-- /block -->` is reference-only —
  never emitted into L1

If no split marker is found, return the full block content unchanged (backward-compatible).

**Block annotation format with split marker:**
```markdown
<!-- block: BLOCK_ID | domain: DOMAIN | mem: §N -->
...tight actionable content (≤15 lines, emitted into L1)...
<!-- /l1-summary -->
...full reference content (post-mortems, file lists, verbose examples)...
<!-- /block -->
```

---

### YAML Index Schema

Read via `yaml.safe_load`. Relevant fields per block:

```yaml
meta:
  format_version: 4
  thresholds:
    l1: 8.0         # weight >= this → L1
    archive: 2.0    # weight < this → ARCHIVE
  delta:
    loaded_used: 0.10
    loaded_skipped: 0.00
    not_loaded: -0.05
  updated: 'YYYY-MM-DD'   # set to session date before saving

blocks:
  - id: block-id          # string key — never modified by this script
    tier: L2              # L1 | L2 | ARCHIVE — recomputed every run
    weight: 5.0           # float — updated by this script
    status: active        # active | deprecated — read only; not modified
    skill: <skill-name>   # skill name or null — read only for integrity check
    last_used: '2026-01-01'  # set to session date when block is in --loaded
    # Other fields (mem, domain, depends, tags, summary, files) — preserve, do not modify
```

Read thresholds and deltas from `meta` — never hardcode them.

---

### Weight Logic (per block, in order)

```python
if block_id in used_ids:
    delta = delta_used       # +0.10
    block["last_used"] = session_date
elif block_id in loaded_ids:
    delta = delta_skipped    # 0.00
    block["last_used"] = session_date
else:
    delta = delta_not_loaded # -0.05
    # do NOT update last_used

new_weight = round(max(0.0, min(10.0, old_weight + delta)), 2)
block["weight"] = new_weight
```

---

### Tier Classification (after weight update)

```python
def classify_tier(weight, l1_thresh, archive_thresh):
    if weight >= l1_thresh:     return "L1"
    if weight < archive_thresh: return "ARCHIVE"
    return "L2"
```

Apply to every block after weight update. If `new_tier != old_tier`, record for report.

---

### stdout Report (always print; dry-run or not)

Print in this order:

**1. Header**
```
Meridian Memory Weight Update — YYYY-MM-DD   (prefix "DRY RUN — " if --dry-run)
  Session blocks loaded : N
  Session blocks used   : N
  Total blocks          : N
  Blocks with delta     : N
```

**2. Tier changes**
If any blocks changed tier:
```
  ⚠  TIER CHANGES — L1_CONTEXT.md auto-regenerated:
     ↑ PROMOTED     block-id    L2 → L1  (7.95 → 8.05)
     ↓ DEMOTED      block-id    L1 → L2  (8.00 → 7.95)
     → moved        block-id    L2 → ARCHIVE  (2.05 → 1.95)
```
Label: `↑ PROMOTED` if new_tier == L1; `↓ DEMOTED` if old_tier == L1; `→ moved` otherwise.

`L1_CONTEXT.md` is regenerated automatically as a side effect of every `--used/--loaded`
run — no manual content editing required.

Otherwise: `  No tier changes this session.`

**3. Top weight changes**
Sort all changed blocks by `abs(new_weight - old_weight)` descending. Show top 10:
```
  Top weight changes (showing up to 10):
    block-id      5.00 → 5.10  (+0.10, loaded+used)
    block-id      5.00 → 4.95  (-0.05, not loaded (decay))
```
Reason strings: `"loaded+used"`, `"loaded (skipped)"`, `"not loaded (decay)"`.

**4. Deprecated blocks with high weight**
```
  ⚠  DEPRECATED BLOCKS WITH HIGH WEIGHT (weight > 4.0):
    block-id    weight: 4.50
  ACTION REQUIRED: review whether these blocks are still deprecated...
```
Filter: `status == "deprecated"` AND `weight > 4.0`.

**5. Integrity check**
Skip blocks where `tier == "L1"` or `status == "deprecated"`.

For remaining blocks:
- `skill` is null/None → add to `orphaned_l2` list
- `skill` is set but `.agents/skills/<skill>/SKILL.md` does not exist → add to
  `missing_skill_file` list

If issues found:
```
  ⚠  INTEGRITY ISSUES:
  Orphaned L2 blocks (N) — no skill assigned; unreachable via trigger:
    block-id
  FIX: assign each block to a skill in MEMORY_INDEX.yaml,
       or promote to L1 if it should auto-load every session.
  Blocks pointing to missing skill files (N):
    block-id    → .agents/skills/<skill>/SKILL.md  (not found)
  FIX: create the missing skill file or correct the skill: field.
```

If clean: `  Integrity: OK — all active L2 blocks have valid skill links.`

**6. Memory health check**
```python
active_blocks = [b for b in blocks if b["tier"] != "ARCHIVE" and b["status"] != "deprecated"]
stale = [(id, days) for b in active_blocks
         if (days := (session_date - date.fromisoformat(str(b["last_used"]))).days) > 90]
stale_pct = len(stale) / len(active_blocks) * 100
```

If `stale_pct >= 40`:
```
  ⚠  MEMORY HEALTH: N/M active blocks (XX%) unseen for 90+ days.
  HUMAN ACTION RECOMMENDED: schedule a memory health review —
  scan recent commits for domain knowledge not yet captured as blocks.
```

Otherwise: `  Health: N/M blocks (XX%) stale >90d  (warn at 40%)`

---

### Save Behavior

Write the comment header first, then `yaml.dump`:

```python
# Read version dynamically so the header stays in sync with weights.default.yaml
_version = _meridian_version()  # reads meta.meridian_version from weights.default.yaml
header = (
    f"# Meridian Agent Memory Index — {_version}\n"
    "#\n"
    "# Single source of truth for all memory blocks: weights, tiers, and dependencies.\n"
    "# Do NOT edit manually during a session — updated by the agent at session-end.\n"
    "#\n"
    "# APPLY WEIGHT UPDATES:\n"
    "#   python .agents/skills/meridian-v4/weight_memory.py --used BLOCK_ID,... --loaded BLOCK_ID,... --date YYYY-MM-DD\n"
    "#\n"
)
with path.open("w", encoding="utf-8") as f:
    f.write(header)
    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
```

Note: `_meridian_version()` reads `meta.meridian_version` from `weights.default.yaml`
at call time. This keeps the header in sync automatically — no hardcoded version string
in the script itself.
