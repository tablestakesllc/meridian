# Meridian — Post-Deployment Shake-Down Prompt (v4.6)

> **How to use:** Paste this file into a new agent conversation on a repository where
> Meridian has just been installed (MERIDIAN_BOOTSTRAP.md steps 1–11 complete) or
> upgraded to a new version.
>
> The agent works through each phase in order and reports findings. Run this ONCE after
> initial setup and again after any major version upgrade.
>
> This document is generic — it contains no project-specific data. Copy it to any
> Meridian-enabled repo's `agent_docs/` directory unchanged.

---

## Your Task

You are performing a systematic shake-down of the Meridian v4.6 installation in this
repository. Work through each phase in order. For each numbered check, output one of:

- `PASS` — check succeeded, no issues
- `FAIL <reason>` — check failed, include the error or discrepancy
- `SKIP <reason>` — check not applicable, explain why

After all phases, output a **Findings Report** (template at the end).

---

## Phase 1 — Directory Structure

Verify the following paths exist. For each, report PASS or FAIL.

1. `agent_docs/MEMORY_INDEX.yaml` — block registry
2. `agent_docs/weights.default.yaml` — canonical default weights
3. `.agents/skills/meridian-v4/weight_memory.py` — CLI entry point
4. `.agent/weights.yaml` — per-developer weights (gitignored)
5. `agent_docs/SESSION_INIT.md` — session-start checklist
6. `agent_docs/SESSION_END.md` — session-end checklist
7. `agent_docs/PROMPT_LOG.md` — session history log
8. `agent_docs/MEMORY.md` — raw knowledge wiki

Gitignored files (`.agent/weights.yaml`, `agent_docs/L1_CONTEXT.md`) may be absent on a
fresh clone — that is expected. Note them as `SKIP (generate with --seed / --generate-l1)`.

---

## Phase 2 — CLI: Help and Version

Run each command and confirm it exits with code 0 and prints sensible output.

1. `python .agents/skills/meridian-v4/weight_memory.py --help`
   - Expected: usage block listing all flags

2. `python .agents/skills/meridian-v4/weight_memory.py --check-defaults`
   - Expected: reports any blocks in `weights.default.yaml` missing from `weights.yaml`
   - A fresh clone before `--seed` will list all blocks as new — that is expected; report
     PASS and note the count

---

## Phase 3 — Seed and L1 Generation

Simulate what a new developer runs after cloning.

1. Run `python .agents/skills/meridian-v4/weight_memory.py --seed`
   - Expected: outputs "Seeded N new block(s)" and exits 0
   - If `weights.yaml` already populated: "Seeded 0 new block(s)" is correct — PASS

2. Verify `.agent/weights.yaml` exists and has a `blocks:` key with at least one entry
   (or an empty list if `weights.default.yaml` has `blocks: []`)

3. Run `python .agents/skills/meridian-v4/weight_memory.py --generate-l1`
   - Expected: exits 0; `agent_docs/L1_CONTEXT.md` now exists

4. Read the first 30 lines of `agent_docs/L1_CONTEXT.md` and confirm:
   - Starts with `# L1 Context —`
   - Contains a `## Top Blocks` section
   - Contains a `## File → Skill Routing Table` section (may be empty if no
     `files:` globs are defined in MEMORY_INDEX.yaml — note either way)

---

## Phase 4 — Dry-Run

Simulate the weight update that runs at session-end without writing any file.

Run:
```bash
python .agents/skills/meridian-v4/weight_memory.py \
    --used   "" \
    --loaded "" \
    --date   "2025-01-01" \
    --dry-run
```

Expected: exits 0, prints a preview of weight changes (may be empty if no block IDs
provided — that is fine). Confirm no exception is raised.

---

## Phase 5 — Routing Table Quality Check

1. Count the rows in the `## File → Skill Routing Table` in `agent_docs/L1_CONTEXT.md`:
   ```bash
   awk '/File.*Skill Routing Table/,0' agent_docs/L1_CONTEXT.md \
       | grep "^| " | grep -v "File pattern" | wc -l
   ```
   - **Why the scoped `awk`:** L1_CONTEXT.md embeds raw block content from SKILL.md files,
     which may contain their own markdown tables. A bare `grep "^| "` over the whole file
     counts those internal table rows too and produces a misleading total. The `awk` range
     expression restricts counting to lines after the routing table header.
   - Report the count. **Zero** means no blocks carry both a `files:` glob AND a `skill:`
     field (acceptable on a minimal install — note it; the routing table section will be
     absent entirely). Any rows present should have a non-empty `Skill(s)` column —
     spot-check two rows.

2. Open `agent_docs/MEMORY_INDEX.yaml`. Confirm at least one block has a `files:` key
   with at least one glob entry. If none do, note this as an observation (not a failure).

---

## Phase 6 — Merge Driver

Verify the union merge driver is configured. This prevents weight conflicts during merges.

1. Run `git config --local include.path` — expected output: `../.gitconfig`
2. Check `.gitconfig` exists in the project root and contains `[merge "union"]`
3. Check `.gitattributes` exists and contains at least one line matching
   `merge=union` for YAML files

If any of these fail, the merge driver is not set up. Apply the three steps manually:
1. Create `.gitconfig` with the union driver definition
2. Create `.gitattributes` with the YAML glob patterns
3. Run `git config --local include.path ../.gitconfig`

---

## Phase 7 — SESSION_INIT Bootstrap Confirmation Line

1. Read `agent_docs/SESSION_INIT.md`
2. Confirm it contains all of the following checklist items:
   - A step to load `agent_docs/L1_CONTEXT.md`
   - A step to read the most recent PROMPT_LOG session
   - A step to confirm the active branch
   - A step to verify the merge driver
   - A step to reset `context_swap.json` (`printf '{}' > .agent/context_swap.json`)
   - A required agent output line: `Bootstrap complete — SESSION_INIT ✓ | L1 ✓ | ...`

3. For each item above, report PASS or FAIL with the specific line reference.

---

## Phase 8 — SESSION_END Structure

1. Read `agent_docs/SESSION_END.md`
2. Confirm it includes (in any order):
   - A step to write `context_swap.json` snapshot **before** doc updates
   - A step to update SESSION_INIT.md Current State block
   - A step to update the dev log (DEVELOPMENT.md or equivalent)
   - A step to update PROMPT_LOG.md
   - A step to run the weight update script (`--used`, `--loaded`, `--date`)
   - A final git commit + push step

3. Confirm context_swap.json write appears as the **first** substantive step
   (before SESSION_INIT update). Report PASS or FAIL.

---

## Phase 9 — Minimal Session-End Simulation

Simulate a session-end cycle with dummy data (no real git push).

1. Write a test context_swap:
   ```bash
   printf '{"session":"2025-01-01T00:00:00Z","branch":"test","head":"abc123","blocks_loaded":[],"blocks_used":[],"decisions":["shakedown test"]}' > .agent/context_swap.json
   ```
2. Confirm the file was written: `cat .agent/context_swap.json`
3. Run a dry-run weight update:
   ```bash
   python .agents/skills/meridian-v4/weight_memory.py \
       --used "" --loaded "" --date "2025-01-01" --dry-run
   ```
4. Confirm L1_CONTEXT.md regenerates: `python .agents/skills/meridian-v4/weight_memory.py --generate-l1`
5. Reset context_swap: `printf '{}' > .agent/context_swap.json`

Report PASS for each step if no errors occur.

---

## Findings Report

After completing all phases, output this block filled in:

```
Meridian v4.6 Shake-Down — Findings Report
===========================================
Date: <YYYY-MM-DD>
Repository: <repo name>
Agent: <agent name/version>

Phase 1 — Directory Structure:        PASS / PARTIAL / FAIL
Phase 2 — CLI Help and Check-Defaults: PASS / PARTIAL / FAIL
Phase 3 — Seed and L1 Generation:     PASS / PARTIAL / FAIL
Phase 4 — Dry-Run:                    PASS / PARTIAL / FAIL
Phase 5 — Routing Table Quality:      PASS / PARTIAL / FAIL
Phase 6 — Merge Driver:               PASS / PARTIAL / FAIL
Phase 7 — SESSION_INIT Bootstrap:     PASS / PARTIAL / FAIL
Phase 8 — SESSION_END Structure:      PASS / PARTIAL / FAIL
Phase 9 — Session-End Simulation:     PASS / PARTIAL / FAIL

Failures:
- <Phase N>: <description of failure and resolution if known>

Observations (non-blocking):
- <anything noteworthy that isn't a failure>

Overall: PASS / NEEDS ATTENTION
```

A result of **PASS** on all phases means the installation is functioning correctly.
A result of **NEEDS ATTENTION** means at least one FAIL was found — address each failure
before the installation is considered production-ready.
