# Meridian Agent Context and Memory System — Bootstrap Prompt (v4.6)

> **How to use this file:**
> Give this document to a fresh agent on any new repository to set up Meridian v4.6
> from scratch. The agent should follow the steps in order. No prior Meridian knowledge
> is required. All schemas and templates are included inline.

---

## What You Are Setting Up

You are setting up the **Meridian Agent Context and Memory System (v4.6)** in this
repository. Meridian is a file-native knowledge grounding system for AI coding agents.
It has no server, no vector database, and no external API dependencies. Everything lives
in the repository.

Meridian works by:
- Maintaining a structured index of named memory blocks — discrete pieces of domain
  knowledge about this codebase
- Applying a weight and decay system so frequently used knowledge stays hot-loaded and
  stale knowledge fades without being lost
- Dispatching context on demand using multi-match logic: domain tags, file access
  patterns, and keyword triggers
- Generating a hot-load file (`L1_CONTEXT.md`) at session end that is read at the start
  of every subsequent session

---

## Directory Structure to Create

```
agent_docs/
    MEMORY_INDEX.yaml          # shared block structure — committed
    weights.default.yaml       # maintainer-curated seed weights — committed
    SESSION_INIT.md            # session bootstrap instructions — committed
    SESSION_END.md             # session close checklist — committed
    MEMORY.md                  # raw wiki of domain knowledge sections — committed
    L1_CONTEXT.md              # auto-generated hot-load context — gitignored
    PROMPT_LOG.md              # running session log — committed

.agent/
    weights.yaml               # per-developer live weights — gitignored
    context_swap.json          # session checkpoint — gitignored

.agents/
    skills/                    # domain skill files — committed (Open Agent Skills standard path)
        <domain>/
            SKILL.md
        meridian-v4/
            SKILL.md
            weight_memory.py   # weight manager script — committed

<agent-auto-load-file>         # agent-specific session instructions (e.g. .github/copilot-instructions.md)
```

Add to `.gitignore`:
```
agent_docs/L1_CONTEXT.md
.agent/
```

---

## Step 1: Copy weight_memory.py

> **Upgrading from an earlier version?** Skip to the **Upgrade Log** section at the
> end of this file. Find the entry matching your current version and apply the steps
> listed there before continuing with setup.

Copy `weight_memory.py` from an existing Meridian installation into
`.agents/skills/meridian-v4/weight_memory.py`.
This script manages weight updates, L1 generation, seeding, and migration.
Do not modify it — it is the engine.

If no existing installation is available, use **Appendix C** (included at the end of
this document) to have an agent rebuild the script from the specification.

Verify it runs:
```bash
python .agents/skills/meridian-v4/weight_memory.py --help
```

> **Note:** On systems where `python` is not aliased (common on modern Linux), use
> `python3` in place of `python` throughout this guide.

---

## Step 2: Create MEMORY_INDEX.yaml

This is the shared block registry. It contains metadata about every memory block — IDs,
domain tags, skill routing, file associations, and summaries. It does NOT contain weights
(those live in `.agent/weights.yaml`).

Schema for each block entry:
```yaml
- id: <kebab-case-unique-id>
  mem: §<N>                        # section number in MEMORY.md
  domain: <domain-string>          # e.g. testing, cicd, frontend, db, security
  skill: <skill-name>              # matches a directory in .agents/skills/
  depends: []                      # list of block IDs this block depends on
  tags:
    - <keyword>                    # trigger keywords for dispatch
  summary: <one-line summary>      # shown in check-defaults and health reports
  files:
    - <path/to/relevant/file>      # files this block applies to; empty list is fine
  status: active                   # active | deprecated
```

Start with an empty blocks list and populate it as you add knowledge:
```yaml
meta:
  format_version: "4.1"
  description: "Meridian block index for <project name>"

blocks: []
```

---

## Step 3: Create weights.default.yaml

This is the committed seed file. New developers run `--seed` against this file to
initialize their local `.agent/weights.yaml`. Maintainers update this file when adding
new blocks or adjusting default priorities.

Schema:
```yaml
meta:
  schema_version: 1
  description: "Default seed weights for <project name>"
  thresholds:
    l1: 8.0        # blocks at or above this weight are hot-loaded into L1_CONTEXT.md
    archive: 2.0   # blocks at or below this weight are flagged for review
  delta:
    loaded_used: 0.10      # weight increase when a block is loaded AND actively used
    loaded_skipped: 0.00   # no change when loaded but not actively applied
    not_loaded: -0.05      # decay when a block is not loaded in a session

blocks:
  - id: <block-id>
    seed_weight: 5.0
    category: general
```

All new blocks start at `seed_weight: 5.0`. Blocks promoted to L1 will have weights
at or above 8.0 after sustained use.

---

## Step 4: Create SESSION_INIT.md

This file is the single source of truth for session bootstrap. It is agent-agnostic:
any agent reading this file follows the same procedure regardless of how it was invoked.
The agent-native pre-load file (e.g. `copilot-instructions.md`) should contain only a
single pointer: "read `agent_docs/SESSION_INIT.md` and run the Session-Start Checklist."

`SESSION_INIT.md` must contain three sections in order:

**1. Current State block** (agent-maintained, updated at session close):
```markdown
## Current State (Agent-Maintained)
> Written by the agent at session close.

**Last branch:** `<branch>`
**Last commit:** `<hash>` — <description>
**Next priority item:** <item>
**Open blockers:** <None or description>
**Last updated:** <YYYY-MM-DD PDT>
```

**2. Session-Start Checklist** — structured like `SESSION_END.md`: numbered sections,
imperative header, inline bash commands, and `[ ]` checkboxes. The checkbox format
drives sequential step execution; the mandatory output line makes compliance observable.

Required checklist steps (in order):
   1. Read the Current State block — `[ ] Current State block read`
   2. Load L1 Context — regenerate if missing, then read `agent_docs/L1_CONTEXT.md` in full — `[ ] L1_CONTEXT.md read in full`
   3. Read most recent PROMPT_LOG session — `grep -n "^## Session:" agent_docs/PROMPT_LOG.md | tail -1` — `[ ] PROMPT_LOG session read`
   4. Confirm branch — `git branch --show-current` — `[ ] Branch identified, rules applied`
   5. Verify merge driver — `git config --local include.path` must output `../.gitconfig` — `[ ] Merge driver active`
   6. Reset context swap — `printf '{}' > .agent/context_swap.json` — `[ ] context_swap.json reset`
   7. Output confirmation line and open PROMPT_LOG entry — agent outputs:
      `Bootstrap complete — SESSION_INIT ✓ | L1 ✓ | PROMPT_LOG ✓ | branch: <name> | merge driver ✓`

End the checklist with an **Edge Cases** section for first-time setup (missing
`weights.yaml` or `L1_CONTEXT.md`) so those paths stay out of the normal flow.

**3. File map table** describing each Meridian file and whether it is committed or
   gitignored.

---

## Step 5: Create SESSION_END.md

This file is the session close checklist. It must instruct the agent to:

1. Write `.agent/context_swap.json` as a **session snapshot** — before touching any
   docs. This is the agent's save point; if context is compressed mid-session-end, the
   agent recovers state by reading this file. After writing, read it back in full and
   use it as the authoritative reference for all remaining steps:
   ```json
   {
     "session": "YYYY-MM-DDTHH:MM:SSZ",
     "branch": "<branch>",
     "head": "<git hash>",
     "blocks_loaded": ["<id>", "..."],
     "blocks_used": ["<id>", "..."],
     "new_candidates": [],
     "decisions": ["<key decision or gotcha from this session>"],
     "issues_created": []
   }
   ```
2. Update `agent_docs/SESSION_INIT.md` Current State block
3. Update project development log (DEVELOPMENT.md or equivalent)
4. Update `agent_docs/PROMPT_LOG.md` with all prompts from the session
5. Run the weight update script:
   ```bash
   python .agents/skills/meridian-v4/weight_memory.py \
       --used   "<comma-separated block IDs actively used>" \
       --loaded "<comma-separated block IDs loaded this session>" \
       --date   "YYYY-MM-DD"
   ```
6. Stage all changes and push in one commit:
   ```bash
   git add -A
   git commit -m "chore(docs): session-end [skip ci]"
   git push
   ```

---

## Step 6: Create MEMORY.md

This is the raw wiki. Every domain knowledge section lives here as a numbered section.
Start with a minimal file:

```markdown
# <Project Name> — Memory and Design Decisions

> Check the Memory Index below; load only the section(s) relevant to current work.

## Memory Index

| § | Topic | Read When |
|---|---|---|

---

## 1. <First topic>

**Added:** <date>

<Problem statement and fix.>
```

Sections are numbered sequentially. Do not delete sections — mark them deprecated if
they are no longer relevant.

---

## Step 7: Create PROMPT_LOG.md

Running log of user prompts per session. Append-only — new sessions are added at the bottom, oldest at top. Start with:

```markdown
# <Project Name> — Prompt Log

> **Format:** Append-only — sessions added at the bottom, oldest at top.
> **Session header:** `## Session: YYYY-MM-DD HH:MM PDT — <git config user.name>`  
> Run `git config user.name` at session start to get the name token.
> **Reading:** Run `grep -n "^## Session:" PROMPT_LOG.md | tail -1` to get the most recent session line number, then read from there to end of file.
> **Timezone:** All times in US Pacific (PDT/PST).

---

## Session: <YYYY-MM-DD HH:MM PDT> — <git config user.name>
### Context at Session Start
Meridian v4.6 initial setup.

### Prompts

| Time (PDT) | Prompt | Commit |
|---|---|---|
| <YYYY-MM-DD HH:MM PDT> | Initial Meridian v4.6 setup | — |
```

---

## Step 8: Create your agent’s auto-load instructions file

This file is loaded automatically by the agent at the start of every session. The
filename and location are agent-specific:

| Agent | Auto-load file |
|---|---|
| GitHub Copilot (VS Code) | `.github/copilot-instructions.md` |
| Cursor | `.cursor/rules/` (one `.mdc` file per rule group) |
| Claude Code | `CLAUDE.md` (repo root) |
| Generic | Agent-configured path |

**Keep this file minimal.** Its only job is to route the agent to `SESSION_INIT.md`.
All bootstrap logic — L1 loading, PROMPT_LOG reading, branch confirmation, merge driver
check, context swap reset — lives in the `SESSION_INIT.md` checklist, which is
agent-agnostic and the single source of truth.

The auto-load file must contain exactly one bootstrap instruction:

```markdown
## At the Start of Every New Conversation

Read `agent_docs/SESSION_INIT.md` in full and run the Session-Start Checklist defined
there. That checklist is the single source of truth for bootstrap — do not use a
checklist defined in this file.
```

You may add agent-specific or project-specific content after the bootstrap pointer
(branch rules, always-on standards, skill routing tables, etc.), but do not duplicate
any step from the `SESSION_INIT.md` checklist here. Duplication creates two competing
checklists that agents will conflate.

### Pre-Approved Commands

Many agents support declaring commands that can be run without prompting the user for
confirmation. Pre-approving Meridian's read-only and idempotent commands eliminates
unnecessary approval prompts during session-start and session-end.

| Agent | Configuration location |
|---|---|
| GitHub Copilot (VS Code) | `github.copilot.chat.agent.autoApproveTerminalCommands` in `.vscode/settings.json` |
| Cursor | Allowed tools list in agent config |
| Claude Code | `allowed_tools` in `CLAUDE.md` or settings |

Suggested baseline for any Meridian installation (adapt paths to your skill directory):

```json
// .vscode/settings.json
{
  "github.copilot.chat.agent.autoApproveTerminalCommands": [
    "python .agents/skills/meridian-v4/weight_memory.py --help",
    "python .agents/skills/meridian-v4/weight_memory.py --check-defaults",
    "python .agents/skills/meridian-v4/weight_memory.py --generate-l1",
    "python .agents/skills/meridian-v4/weight_memory.py --dry-run *",
    "git status",
    "git log *",
    "git branch *",
    "git diff *",
    "git config *"
  ]
}
```

> **After completing this step, prompt your user:**
> "I’ve created the auto-load file with the bootstrap pointer. Meridian recommends
> pre-approving its read-only commands so session-start and session-end can run without
> stopping for confirmation. The suggested list includes `git status/log/diff/branch`,
> `git config`, and `weight_memory.py --generate-l1`, `--check-defaults`, and
> `--dry-run`. Would you like to add, remove, or adjust anything before I configure
> auto-approval for your agent?"

---

## Step 9: Seed and Generate L1

Run in order:
```bash
# Initialize per-developer weights from the defaults file
python .agents/skills/meridian-v4/weight_memory.py --seed

# Generate the initial L1_CONTEXT.md from current weights
python .agents/skills/meridian-v4/weight_memory.py --generate-l1
```

> **Note:** On a fresh install where `weights.default.yaml` starts with `blocks: []`,
> `--seed` will report "Seeded 0 new block(s)". This is expected — the command
> succeeded and your weights file is initialized. Blocks are added to the defaults
> file as you create them.

Verify both files exist:
- `.agent/weights.yaml`
- `agent_docs/L1_CONTEXT.md`

---

## Step 10: Verify

Run a check-defaults pass to confirm the index and weights are in sync:
```bash
python .agents/skills/meridian-v4/weight_memory.py --check-defaults
```

Output should report zero new blocks. If any are listed, run `--seed` again.

The system is now operational. Begin adding memory blocks as you work — each session's
`--used` and `--loaded` flags will grow the weights organically from actual use.

**Run the shake-down** to verify the full installation before your first real session:

> Open `agent_docs/MERIDIAN_SHAKEDOWN.md` and paste it into a new agent conversation.
> The agent works through 9 verification phases and produces a PASS/FAIL findings report.
> Fix any FAILs before proceeding.

---

## Block Annotation Format (for MEMORY.md sections)

When a MEMORY.md section corresponds to a block in MEMORY_INDEX.yaml, annotate it:

```markdown
<!-- block: <block-id> | domain: <domain> | mem: §<N> -->
<tight 3-5 line summary for L1 hot-loading>
<!-- /l1-summary -->

<full reference content — not emitted into L1_CONTEXT.md>
<!-- /block -->
```

The `<!-- /l1-summary -->` marker tells `weight_memory.py` where to stop when generating
L1. Content above the marker is hot-loaded. Content below is available on demand via the
`mem: §N` pointer but never clutters the session context.

---

## Step 11: Create the Meridian Core Skill Files

Meridian ships with two core skill files that teach the agent how to operate and extend
the memory system. Create them from the content in Appendix A and B:

```bash
mkdir -p .agents/skills/meridian-v4
mkdir -p .agents/skills/meridian-skill-manager
```

- Copy **Appendix A** content → `.agents/skills/meridian-v4/SKILL.md`
- Copy **Appendix B** content → `.agents/skills/meridian-skill-manager/SKILL.md`
- Copy **Appendix C** content → `.agents/skills/meridian-v4/REBUILD_SPEC.md`

Register both in your agent’s auto-load instructions file under the skill dispatch table:

| Condition | What to load |
|---|---|
| Adding new block, running weight update, block tier change, context_swap, MEMORY_INDEX edit, knowledge triage, first-boot seed, check-defaults, migrate | Skill: `meridian-v4` |
| Creating a new skill, updating an existing skill, SESSION_END skill audit, skill trigger keyword audit | Skill: `meridian-skill-manager` |

---

## Appendix A: `.agents/skills/meridian-v4/SKILL.md`

> Copy the following content into `.agents/skills/meridian-v4/SKILL.md`. The YAML
> frontmatter block starts the file; the section ends at the "Appendix B" header below.

```yaml
---
name: meridian-v4
description: 'Meridian v4.6 memory system operations: adding blocks, weight_memory.py session-end run, L1 promotion/demotion, per-developer weights.yaml, weights.default.yaml, L1_CONTEXT.md generation, context_swap.json, MEMORY_INDEX.yaml block registration, deciding where new knowledge goes. Use when: adding new block, running weight update, block tier change, context_swap, MEMORY_INDEX edit, knowledge triage, first-boot seed, check-defaults, migrate.'
---
```

# Meridian v4.6 Memory System — Operations Reference

This skill covers **operating** the v4.6 memory system. For system design rationale, see
the Always-On Standards section of your agent’s auto-load instructions file.

---

### File Map

| File | Role | Committed? | Edit frequency |
|---|---|---|---|
| `agent_docs/MEMORY_INDEX.yaml` | Shared block structure — IDs, tags, deps, summaries, status (no weights) | Yes | When adding/deprecating blocks |
| `agent_docs/weights.default.yaml` | Maintainer-curated seed weights and thresholds | Yes | When adding blocks or changing recommendations |
| `agent_docs/L1_CONTEXT.md` | Auto-generated L1 content — gitignored, per-developer | No | Regenerated by `weight_memory.py` at session-end |
| `agent_docs/MEMORY.md` | Raw wiki — every §N section ever recorded; never delete sections | Yes | When recording a new gotcha |
| `.agent/weights.yaml` | Per-developer live weights — gitignored | No | Updated by `weight_memory.py` |
| `.agent/context_swap.json` | Ephemeral per-commit state — gitignored | No | Written after each git commit |
| `.agents/skills/meridian-v4/weight_memory.py` | Weight manager script | Yes | Do not edit; run only |

---

### Session-End Weight Update (required every session)

```bash
python .agents/skills/meridian-v4/weight_memory.py \
  --used   "block-id-A,block-id-B" \
  --loaded "block-id-A,block-id-B,block-id-C" \
  --date   "YYYY-MM-DD"
```

This reads `.agent/weights.yaml`, updates weights, regenerates `agent_docs/L1_CONTEXT.md`
as a side effect, and prints tier changes, integrity issues, and health warnings. No
manual L1_CONTEXT.md editing required.

**Classifying blocks:**

| Signal | Put in `--used` | Put in `--loaded` only |
|---|---|---|
| Block content was directly applied to a decision or fix | yes | yes |
| Block was loaded as context but wasn't the decisive reference | no | yes |
| Block was not loaded at all | neither | neither |

**L1 blocks** are in `agent_docs/L1_CONTEXT.md` (gitignored, auto-generated). Include
their IDs in `--loaded` for every session. If actively applied, also add to `--used`.

After running, review stdout for:
- `TIER CHANGES` — L1_CONTEXT.md is regenerated automatically; no manual action needed
- `ACTION REQUIRED` — L1 block content not found in annotated sources; add manually
- `RECOMMENDATIONS` — new blocks in defaults not yet in your weights; run `--check-defaults`

> **Rebuilding the script from scratch?** See Appendix C in this file, or read
> `.agents/skills/meridian-v4/REBUILD_SPEC.md` once created.

---

### First-Boot / New Contributor Setup

When `.agent/weights.yaml` doesn't exist (fresh clone, first session):

```bash
# 1. Seed weights from maintainer defaults
python .agents/skills/meridian-v4/weight_memory.py --seed

# 2. If L1_CONTEXT.md also missing:
python .agents/skills/meridian-v4/weight_memory.py --generate-l1
```

`--seed` creates `.agent/weights.yaml` from `agent_docs/weights.default.yaml`, populates
`author`/`author_email` from `git config`, and generates `L1_CONTEXT.md` if it doesn't
exist. It reports `domain` category blocks so the agent can ask the user to confirm or
adjust them.

**Onboarding conversation (agent, after `--seed`):**
> "This is your first session on this project. Based on `weights.default.yaml`, these
> domain-specific blocks are seeded at elevated weights. Want to keep, adjust, or skip any?"
> [list `category: domain` blocks with reasons]

User confirms or adjusts. Agent updates `.agent/weights.yaml` if changes are requested,
then regenerates L1 if any weights crossed 8.0.

---

### Checking for New Defaults (ongoing)

When a maintainer adds a new block to `weights.default.yaml`, contributors learn via:

1. Automatic notice in `--used/--loaded` output: `RECOMMENDATIONS: N new block(s) in defaults`
2. Manual check: `python .agents/skills/meridian-v4/weight_memory.py --check-defaults`

Never auto-applies. Always a recommendation the developer accepts explicitly.

---

### One-Time Migration (v4 → v4.1)

For repos currently on v4 (weights in `MEMORY_INDEX.yaml`):

```bash
python .agents/skills/meridian-v4/weight_memory.py --migrate --dry-run  # preview first
python .agents/skills/meridian-v4/weight_memory.py --migrate             # then run for real
git rm --cached agent_docs/L1_CONTEXT.md           # untrack from git
```

Migration preserves all earned weight history. Each developer runs `--migrate` once on
their local clone.

---

### L1_CONTEXT.md — Lifecycle

`agent_docs/L1_CONTEXT.md` is **gitignored**. It is:
- Auto-generated as a side effect of every `--used/--loaded` run
- Per-developer (your L1 blocks may differ from a colleague's if weights diverge)
- Regenerated on demand via `--generate-l1`
- Not manually editable (overwritten at next session-end)

Block content is extracted from `<!-- block: <id> --> ... <!-- /block -->` annotations
in `agent_docs/MEMORY.md` and `.agents/skills/*/SKILL.md`. If a block is at L1 weight
but has no annotation in any source file, the script prints `ACTION REQUIRED`.

---

### Adding a New Block

1. **Identify the right home** (see Knowledge Triage below)
2. **Add to `agent_docs/MEMORY_INDEX.yaml`**:

```yaml
- id: <kebab-case-id>
  mem: §N          # MEMORY.md section number, or §0 if no entry yet
  domain: <domain> # cicd | db | frontend | security | deployment | observability | worker | api | design
  skill: <skill-name>  # directory name in .agents/skills/; null if none
  depends: []      # block IDs that must co-load with this one
  tags: [tag1, tag2]
  summary: "One sentence: what the block covers and why it matters"
  files: []        # REQUIRED on every block. File globs that trigger this block.
                   # Use [] for cicd/behavior/infra blocks with no file association.
                   # Omitting creates a schema inconsistency — always include the field.
  status: active   # active | deprecated
```

> **Integrity rule:** Every active L2 block must have a `skill` value pointing to an
> existing SKILL.md file, or its weight must be >= 8.0 (L1, auto-loaded). A block with
> `skill: null` and weight < 8.0 will appear as "Orphaned L2" in the integrity report
> at every session-end weight update. If a block is universally applicable and has no
> natural trigger skill, promote it to L1 from the start.

3. **Add to `agent_docs/weights.default.yaml`**:

```yaml
- id: <kebab-case-id>
  seed: 5.0        # 5.0 general | 5.5–7.0 domain | 8.0+ operational
  category: general  # general | domain | operational
  reason: "Why this seed weight (one sentence)"
```

4. **Annotate the source** in the skill file or MEMORY.md section:

```markdown
<!-- block: <block-id> | domain: <domain> | mem: §N -->
...tight actionable content (≤15 lines)...
<!-- /l1-summary -->
...full reference content — never emitted into L1_CONTEXT.md...
<!-- /block -->
```

`extract_block_content()` stops at `<!-- /l1-summary -->` for L1 generation. Blocks
without the marker emit their full content. Add the marker when verbosity would inflate
L1 without adding actionable value.

5. **Run the skill audit** (`meridian-skill-manager`) before committing a new block that
   overlaps with existing content.

---

### Knowledge Triage — Where Does New Information Go?

```
Is it a hard-won gotcha, bug root cause, or non-obvious design decision?
  YES → MEMORY.md new §N  +  MEMORY_INDEX.yaml new block pointing to §N
        The relevant skill file should reference this §N in its Sections Covered table
  NO  ↓

Is it domain-specific procedural guidance (how to apply a pattern in this project)?
  YES → Add inline to the relevant skill file
        If it maps to a MEMORY.md concept, cross-reference the §N
  NO  ↓

Is it a behavioral or workflow preference that applies every session?
  YES → L1_CONTEXT.md directly (weight >= 9.0, agent-operating-prefs pattern)
  NO  ↓

Is it already covered but the existing block needs updating?
  YES → Update MEMORY.md §N and/or the skill's procedural section
        No new MEMORY_INDEX entry needed unless it's a genuinely new topic
```

**The one migration debt case:** A skill section that *only* says "read MEMORY.md §N"
with no added procedural guidance. Add the procedural layer in the skill file rather
than just pointing elsewhere.

---

### context_swap.json — Format and Timing

Write `.agent/context_swap.json` after each git commit. SESSION_INIT wipes it.

```json
{
  "branch": "<current branch>",
  "head": "<git rev-parse HEAD>",
  "session_date": "YYYY-MM-DD",
  "blocks_loaded": ["block-id-A", "block-id-B"],
  "blocks_used": ["block-id-A"],
  "new_candidates": ["block-id that might warrant a new block next session"],
  "decisions": ["One-line summary of a key decision made this commit"],
  "issues_created": [
    {
      "number": 0,
      "title": "<issue title>",
      "identified_during": "<brief description of work context>",
      "why": "<one sentence: why it was cut as a separate issue>"
    }
  ]
}
```

**Checkpoint on issue creation:** Whenever a new issue is created mid-session, write an
immediate checkpoint to `.agent/context_swap.json` — do not wait for the next commit.
If `issues_created` is empty, omit the field or leave it as `[]`.

---

### Tier Thresholds

| Tier | Weight range | Behavior |
|---|---|---|
| L1 | >= 8.0 | Full content in `agent_docs/L1_CONTEXT.md`; auto-loaded every session |
| L2 | 2.0 – 7.9 | Indexed in MEMORY_INDEX.yaml; loaded on-demand via skill trigger |
| ARCHIVE | < 2.0 | Retained in index for weight recovery; not in active loading path |

**Weight deltas per session:**

| Block state | Delta |
|---|---|
| Loaded AND used | +0.10 |
| Loaded, not used | 0.00 |
| Not loaded | −0.05 |

---

### Archive Recovery — No Block Is Ever Deleted

ARCHIVE is a **weight state**, not a deletion. A block at weight 1.5 is still in
`MEMORY_INDEX.yaml` and its content is still in `MEMORY.md §N` or its skill file. It
recovers automatically when loaded and used in a future session.

**Never:**
- Remove a block entry from `MEMORY_INDEX.yaml`
- Delete a `§N` section from `MEMORY.md`
- Remove a block annotation from a skill file because the block is in ARCHIVE

Before starting work in a domain that has been quiet for a long time, scan
`MEMORY_INDEX.yaml` for ARCHIVE blocks in that domain and manually include relevant ones
in `--loaded` if you reference them.

---

### Burst Work Hedge

When the same domain dominates 3+ consecutive sessions, blocks in that domain accumulate
weight faster than steady-state calibration intended.

**Do not adjust weights manually.** Instead:

1. In `context_swap.json`, note to `decisions`: `"Burst: <domain> — N consecutive
   sessions; other domains may be underweighted temporarily"`
2. At the end of a burst, include adjacent domain blocks in `--loaded` (even if not
   used) to stop their decay.
3. Weight imbalance self-corrects within 5–8 normal mixed sessions.

---

### Depends List Maintenance

The `depends` list declares blocks that must co-load with a given block.

**When to add a dependency:**
- Block A's content directly references a concept defined in block B
- Block A describes a fix that requires understanding block B's root cause
- Loading block A without block B would produce an incomplete or misleading picture

**Keeping depends accurate:** When updating a block's content, re-read its `depends`
list. When a block is archived, check if any active blocks still list it in `depends`.

---

### Block Status Field

| Value | Meaning |
|---|---|
| `active` | Normal block — subject to weight changes, promotion, demotion |
| `deprecated` | Pattern superseded; weight decays but block is never deleted |

`weight_memory.py` warns when a `deprecated` block has weight > 4.0 — it's being
actively used, which contradicts deprecated status. To deprecate: change
`status: active` → `status: deprecated` in `MEMORY_INDEX.yaml`; add a note in the
source: `NOTE: Deprecated — superseded by <block-id>`. Never delete.

---

### Memory Health Check

**Automated signal:** If ≥40% of active blocks are stale (last loaded >90 days ago),
the script prints a human action notice.

**What to do:**
1. Tell the user: "Memory health check flagged N% of active blocks unseen for 90+ days."
2. Ask whether to run a review now or defer.
3. If running: scan `git log --oneline --since="90 days ago"` for domain work with no
   corresponding block. Add missing blocks.
4. Run `weight_memory.py` with the review session's `--used`/`--loaded`.

Do not manually inflate weights to suppress the warning.

---

## Appendix B: `.agents/skills/meridian-skill-manager/SKILL.md`

> Copy the following content into `.agents/skills/meridian-skill-manager/SKILL.md`.

```yaml
---
name: meridian-skill-manager
description: 'Meridian skill lifecycle management: conflict detection between skills, circular-load detection, context poisoning guards, user-confirmation gate. Load when: creating a new skill, updating an existing skill, SESSION_END close checklist, skill trigger keyword audit.'
---
```

# Meridian Skill Manager

Load this skill before creating or modifying any skill file, and during the SESSION_END
close.

---

### When This Skill Applies

- Creating a new `.agents/skills/*/SKILL.md`
- Editing an existing skill (content, triggers, frontmatter)
- Adding or modifying a skill trigger row in `copilot-instructions.md`
- SESSION_END — run the audit checklist below before committing docs

---

### Audit Checklist

Run all four checks in order. For any finding, stop and present the issue to the user
before proceeding.

#### 1. Conflict Detection

A conflict is when two or more skills or context files describe the same topic with
different rules, values, or procedures.

**Step 1a — Index-driven scope (always run first):**

Open `agent_docs/MEMORY_INDEX.yaml`. For the new or changed block, read its `domain`,
`tags`, `depends`, and `skill` fields. Build the affected skill set:

1. Find all blocks in the index that share the same `domain`. Collect their `skill`
   values (non-null only).
2. Walk the `depends` list. For each dep block, also collect its `skill` value.
3. The union of those `skill` values is the **affected skill set** — the only skills
   whose content could realistically conflict with the change.
4. Read each skill in the affected set and scan for content that contradicts the
   new/changed block.

This scopes the search precisely. You do not need to scan all skill files for every
change.

**Step 1b — Free-form scan (for L1 block changes):**

If the changed content is in an L1 block (weight >= 8.0), also grep across all skill
files for the core noun/keyword of the changed rule. L1 blocks establish operational
rules that skills document procedures for — a new L1 rule can conflict with a skill's
documented commands or thresholds even when the index `domain` does not overlap.

**Action:** Present conflicting excerpts side-by-side. Recommend which should be
authoritative (usually the more specific/recent one). Wait for user decision before
editing.

---

#### 2. Circular Load Detection

A circular load occurs when skill A triggers skill B, and skill B triggers skill A — or
when a session-init instruction reads a file that reads the first file again.

**How to check:**
- For every trigger keyword in the new/changed skill, check whether those keywords
  appear in the content of other skills as topics they cover.
- Check `copilot-instructions.md` session-start steps for self-referential chains.

**Common safe pattern:** SESSION_INIT.md referencing `copilot-instructions.md`, which
references SESSION_INIT.md is a known intentional loop — do NOT flag unless both
change in the same session.

**Action:** Map the load chain as a numbered list. Ask the user whether to break the
cycle by scoping one trigger more narrowly or merging the overlapping content.

---

#### 3. Context Poisoning Guard

Context poisoning is when loaded content degrades agent effectiveness by: (a) stale
facts that were once true but aren't now, (b) over-broad triggers that cause unrelated
skills to load, or (c) redundant coverage that dilutes signal.

**How to check:**

**(a) Stale facts:**
- Scan for version numbers, dates, specific file paths, or API contracts that may have
  changed.
- Cross-reference against the current codebase. Flag any reference to a file or pattern
  that no longer exists.

**(b) Over-broad triggers:**
- Read the `description` field. Rule of thumb: if a trigger keyword matches more than
  ~30% of all sessions, it is too broad.

**(c) Redundancy:**
- If new skill content duplicates content already in `agent_docs/L1_CONTEXT.md`, it is
  redundant — remove the duplicate from the skill (the L1 block is the authority).
- If two skills cover >60% of the same topic area, recommend merging them.

**Action:** List each finding with the specific excerpt and location. User decides.

---

#### 4. Migration Debt Check

The migration debt case is narrow: a skill section that **only** says "read MEMORY.md
§N" with no added procedural guidance. That section adds nothing beyond what the index
alone provides.

**How to check:**
- Read each section of the skill file. Flag any section whose entire content is a bare
  `"Read §N"` reference with nothing else.
- A section that says "Read §N for background, then apply it like this: ..." is correct.

**Action:** Flag each bare stub. Recommend adding the procedural layer inline in the
skill file. Wait for user confirmation before editing.

---

#### 5. Action Gate

**Never take corrective action autonomously.** If any of checks 1–4 produce a finding:

1. Present findings clearly: what the issue is, where it is, why it matters.
2. Provide a concrete recommendation.
3. Wait for explicit user confirmation before making any edit.

If all checks pass: state "Skill audit complete — no conflicts, loops, poisoning, or
migration debt detected" and proceed.

---

### Adding a New Skill — Standard Structure

```markdown
---
name: <project>-<name>
description: '<skill-name> knowledge: <topic list>. Use when: <trigger list>.'
---

# <Project> <Name> Knowledge

## Sections Covered

| MEMORY § | Topic |
|---|---|
| §N | ... |

## <Section>

<!-- block: <block-id> | domain: <domain> | mem: §N -->
...content...
<!-- /block -->
```

**Registration — two places, both required:**

1. `copilot-instructions.md` skill table — add a row with condition and `Skill: <skill-name>`
2. `agent_docs/MEMORY_INDEX.yaml` — add an entry for each new block with the skill name,
   appropriate domain, and initial weight (5.0 is a reasonable cold-start value)

**Trigger keyword rule:** Be specific. Use domain nouns, error messages, flag names, or
file names — not generic verbs like "create" or "update."

---

### Skill Authoring Standards — BAD/GOOD Negative Anchor Rule

**When documenting a required shell command, invocation form, flag syntax, or file
operation:** always include a negative example alongside the positive one.

**Why this matters:** LLM-based coding agents have strong trained priors for common
shell patterns. A positive-only rule ("run it directly") is frequently overridden by
pattern completion at generation time. An explicit negative anchor suppresses the wrong
prior by making the failure mode visible.

**Required for any rule that:**
- Names a specific script invocation, executable, or command prefix
- Prohibits a flag, wrapper, or suffix
- Requires a specific quoting style or path form
- Forbids a common shortcut that pattern completion will otherwise generate

**Format:**
```
BAD:  `<wrong form>` — <one-line reason it fails>
GOOD: `<correct form>`
```

**Example — direct script invocation:**
```
BAD:  `bash ./tools/my_script.sh` — bypasses the shebang; breaks if bash not on PATH
GOOD: `./tools/my_script.sh`
```

**Retrofit rule:** If you are editing a skill section that contains a positive-only
command pattern rule and that section lacks a BAD/GOOD block, add one before committing
the edit. Do not defer it.

---

## Appendix C: `weight_memory.py` Rebuild Specification

> Copy the following content into `.agents/skills/meridian-v4/REBUILD_SPEC.md`.
> This file is also the specification an agent follows to rebuild `.agents/skills/meridian-v4/weight_memory.py`
> from scratch if the script is missing or corrupted.

# weight_memory.py — Rebuild Specification

> **When to read this file:** Only when `.agents/skills/meridian-v4/weight_memory.py` is missing, corrupted,
> or needs to be rebuilt from scratch. For normal memory operations, use `SKILL.md`.

This specification is the single source of truth for rebuilding `.agents/skills/meridian-v4/weight_memory.py`.
After implementing, keep this file in sync with any script changes.

---

### Purpose

Session-end weight update script for the Meridian v4.6 agent context and memory system.
Updates block weights in `agent_docs/MEMORY_INDEX.yaml` based on session usage, applies
decay to unloaded blocks, reclassifies tiers, and runs integrity and health checks.

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
header = (
    "# Meridian Agent Memory Index — v4.6\n"
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

---

## Upgrade Log — Migration Notes by Version

> **Purpose:** When upgrading an existing Meridian installation to a newer version,
> the agent reads this section and applies every entry whose version is newer than the
> installed version (`meta.meridian_version` in `weights.default.yaml`). Entries are
> append-only — never edit or delete a past entry.
>
> **Format:** Each entry lists the installed version being upgraded FROM, and the
> concrete file changes required. The agent applies them in order, top to bottom.

---

### v4.5 → v4.6

**Check your installed version:** `grep meridian_version agent_docs/weights.default.yaml`

**1. Replace `weight_memory.py`**

Replace `.agents/skills/meridian-v4/weight_memory.py` with the v4.6 version. The script
adds four new CLI flags plus two new behaviors. No existing flags or behaviours removed.

New flags:

- `--calibrate` — Calibrates the L1/archive weight thresholds from git commit frequency
  history. Writes updated `thresholds.l1` and `thresholds.archive` to `.agent/weights.yaml`.
  Use `--calibrate --dry-run` to preview before applying. Run once per developer.

- `--export-defaults` — **Read-only.** Compares `.agent/weights.yaml` against
  `weights.default.yaml` and prints two tables: (1) PROMOTE CANDIDATES — blocks whose
  local weight has drifted >= `export_promote_threshold` (default 1.5) above seed;
  (2) SEED TOO HIGH — blocks whose local weight is <= `export_demote_threshold` (default
  3.0) below seed. Output is a human-readable recommendation table; the maintainer edits
  `weights.default.yaml` manually. Nothing is written.

- `--maintenance-reset` — Resets `sessions_since_maintenance` to 0 and clears any
  `maintenance_deferred` flag in `.agent/weights.yaml`. Run after completing a memory
  health review to stop the maintenance prompt from firing.

- `--maintenance-defer VALUE` — Defers the maintenance prompt. VALUE is one of:
  `'next-start'` or `'next-end'` (one-time suppression: the maintenance notice is
  skipped for the next `--used/--loaded` run, then the flag is auto-cleared — both
  values have identical runtime behavior); or an integer N (sets the counter to
  `maintenance_interval - N` so the prompt fires again in N sessions).

**Maintenance scheduling:** `sessions_since_maintenance` is incremented on every
non-dry-run `--used/--loaded` call (dry-run does not write weights, so the counter
is not persisted). The maintenance prompt fires when the counter reaches
`maintenance_interval` (default: **30 sessions**, configurable via
`meta.maintenance_interval` in `weights.default.yaml`). The `maintenance_deferred`
flag is checked inside `cmd_update` itself — no SESSION_INIT or SESSION_END
checklist changes are required.

New behaviors:

- **File-glob auto-dispatch:** blocks with `files:` globs in `MEMORY_INDEX.yaml` whose
  patterns match files returned by `git diff --name-only @{u}..HEAD` (committed work since
  the upstream) are auto-added to `--loaded` before weight updates. Falls back to
  `git diff --name-only HEAD` (uncommitted changes) when no upstream is configured.
- **Dry-run L1 preview:** `--dry-run` shows L1 candidates sorted by weight descending.

**2. Update `weights.default.yaml` version**

Set `meta.meridian_version: "v4.6"` in `agent_docs/weights.default.yaml`.

**3. Remove hardcoded File → Skill routing tables (if any)**

`generate_l1_context()` now auto-generates a `## File → Skill Routing Table` section at
the bottom of `agent_docs/L1_CONTEXT.md` derived from the `files:` globs in
`MEMORY_INDEX.yaml`. If you have a hardcoded routing table in `agent_docs/MEMORY.md` or
your agent auto-load file, replace it with a single pointer paragraph:

> "Check the auto-generated routing table at the bottom of `agent_docs/L1_CONTEXT.md`."

The table is regenerated at every session-end weight update — it is always current.

**4. One-time: set up the YAML union merge driver**

v4.6 automates this during `--seed` for new installs. For upgrades (where
`.agent/weights.yaml` already exists), apply the three steps manually:

**4a.** Create `.gitconfig` at the repo root (skip if it already exists):

```
[merge "union"]
	name = union merge driver
	driver = git merge-file --union %O %A %B
```

**4b.** Create `.gitattributes` at the repo root (skip if it already exists):

```
# Meridian memory files — use union merge driver to prevent conflicts
.agent/**/*.yaml      merge=union
.agents/**/*.yaml     merge=union
agent_docs/**/*.yaml  merge=union
```

**4c.** Register the driver locally:

```bash
git config --local include.path ../.gitconfig
```

Verify:

```bash
git config --local include.path    # expected: ../.gitconfig
```

**5. Optional: run `--calibrate`**

Calibrates the L1/archive weight thresholds based on your project's git commit frequency.
Run once per developer to seed thresholds appropriate for the repository's pace:

```bash
python .agents/skills/meridian-v4/weight_memory.py --calibrate --dry-run  # preview first
python .agents/skills/meridian-v4/weight_memory.py --calibrate             # then apply
```

**5a. Patch: `--dry-run` crash on blocks with `skill: null`**

If you run `--dry-run` and see:

```
TypeError: unsupported format string passed to NoneType.__format__
```

this means a block in your `MEMORY_INDEX.yaml` has `skill: null` (or omits the `skill:`
key). The v4.6 dry-run L1 preview passes the raw value to a `{skill:25s}` format spec,
which crashes on `None`.

**Fix:** In `weight_memory.py`, find `_preview_l1_blocks()` and change:

```python
# Before (crashes when skill is None)
skill = meta.get("skill", "?")
```
```python
# After (safe — treats None and missing as "?")
skill = meta.get("skill") or "?"
```

This was patched in the canonical `weight_memory.py` in the same commit that introduced
this upgrade log. If you copied the script before the patch, apply the one-liner above.

**6. Update `REBUILD_SPEC.md`**

Append the four new flags and two new behaviors from step 1 above to
`.agents/skills/meridian-v4/REBUILD_SPEC.md` — the CLI Interface section and any
relevant logic sections. The spec must stay in sync with the script so a future
reconstruction is accurate.

**7. Verify**

```bash
python .agents/skills/meridian-v4/weight_memory.py --generate-l1
```

`agent_docs/L1_CONTEXT.md` should now contain a `## File → Skill Routing Table` section
derived from your `MEMORY_INDEX.yaml` `files:` globs.

---

### v4.5 — Session-Init Restructure (2026-05-24)

Applies to any v4.5 installation created before 2026-05-24. No version bump — this is
a behavioral correction within v4.5.

**Change:** `SESSION_INIT.md` is now the single source of truth for bootstrap procedure.
The agent-native auto-load file (e.g. `copilot-instructions.md`) becomes a thin pointer
only. All checklist steps move into `SESSION_INIT.md`, structured like `SESSION_END.md`.

**1. Rebuild the SESSION_INIT.md bootstrap section**

Replace whatever flat checklist or procedure section exists in `agent_docs/SESSION_INIT.md`
with a hard checklist using this structure (mirrors `SESSION_END.md` format):

```markdown
# Session-Start Checklist

> **Run this checklist at the start of every session before providing a briefing or
> accepting a task.**
> Steps must be completed in order. Do not skip or reorder.

---

## 1. Read Current State
[instructions + `[ ] Current State block read`]

## 2. Load L1 Context
[regenerate-if-missing command + read instruction + `[ ] L1_CONTEXT.md read in full`]

## 3. Read Most Recent PROMPT_LOG Session
[grep command + `[ ] Most recent PROMPT_LOG session read`]

## 4. Confirm Branch
[git branch command + `[ ] Branch identified — branch rules applied`]

## 5. Verify Merge Driver
[git config command + missing-driver recovery instructions + `[ ] Merge driver active`]

## 6. Reset Context Swap
[printf/Set-Content command + do-not-delete warning + `[ ] context_swap.json reset`]

## 7. Output Confirmation and Open PROMPT_LOG Entry
[mandatory output line + git config user.name + PROMPT_LOG append template + briefing
instructions]

---

## Edge Cases (first-time setup only)
[weights.yaml missing → --seed; L1_CONTEXT.md missing → --generate-l1]
```

**2. Replace the bootstrap section in the auto-load file**

In your agent-native auto-load file (e.g. `.github/copilot-instructions.md`,
`CLAUDE.md`, `.cursor/rules/*.mdc`), replace the entire bootstrap checklist with:

```markdown
## At the Start of Every New Conversation

Read `agent_docs/SESSION_INIT.md` in full and run the Session-Start Checklist defined
there. That checklist is the single source of truth for bootstrap — do not use a
checklist defined in this file.
```

Retain any agent-specific or project-specific content that follows (branch rules,
always-on standards, skill routing). Do not duplicate any checklist steps.

**3. Verify**

Open a new agent session and confirm the agent outputs the bootstrap confirmation line:
```
Bootstrap complete — SESSION_INIT ✓ | L1 ✓ | PROMPT_LOG ✓ | branch: <name> | merge driver ✓
```
before providing a briefing.

---

### v4.4 → v4.5

**Check your installed version:** `grep meridian_version agent_docs/weights.default.yaml`

**1. Move skills directory**

Skills moved from `.github/skills/` to `.agents/skills/` (Open Agent Skills standard).

```
git mv .github/skills .agents/skills
```

Then update any references in your auto-load instructions file (e.g. `copilot-instructions.md`,
`AGENTS.md`) that contain `.github/skills/` → `.agents/skills/`.

**2. Move `weight_memory.py` into the skill directory**

```
git mv tools/weight_memory.py .agents/skills/meridian-v4/weight_memory.py
```

Update `REPO_ROOT` inside the script (see File Location section in Appendix C).

**3. Replace fixed-depth `REPO_ROOT` with sentinel-walk**

In `weight_memory.py`, replace the `REPO_ROOT = Path(__file__).parent.parent` line with
the `_find_repo_root()` function documented in Appendix C → File Location. Also update
`skills_dir` inside the integrity check from `.github/skills` to `.agents/skills`.

**4. Update `weights.default.yaml` version**

Set `meta.meridian_version: "v4.5"` in `agent_docs/weights.default.yaml`.

**5. Switch PROMPT_LOG to append-only**

If your `PROMPT_LOG.md` was prepend-only (newest session at top), reorder it so the
oldest session is at the top and new sessions are appended at the bottom. Add a divider
comment at the transition point. Update your auto-load instructions to read with:
```
grep -n "^## Session:" agent_docs/PROMPT_LOG.md | tail -1
```
then read from that line to end of file.

**6. Add session owner to PROMPT_LOG headers**

Change session header format from `## Session: YYYY-MM-DD` to:
```
## Session: YYYY-MM-DD HH:MM PDT — <git config user.name>
```

**7. Fix `.gitattributes` paths**

If your `.gitattributes` merge driver entries reference `docs/SESSION_INIT.md`,
`docs/PROMPT_LOG.md`, or `docs/MEMORY.md`, update them to `agent_docs/` prefix.

**8. Update test fixtures**

In `test_weight_memory.py`, change skill fixture path from
`tmp_path / ".github" / "skills" / skill_name / "SKILL.md"` →
`tmp_path / ".agents" / "skills" / skill_name / "SKILL.md"`.

**9. Verify**

```
.venv/bin/python .agents/skills/meridian-v4/weight_memory.py --dry-run --used "" --loaded ""
```

Output should show `Integrity: OK` with no missing skill file warnings.

---

### v4.3 → v4.4

**Check your installed version:** `grep meridian_version agent_docs/weights.default.yaml`

**1. Update `weights.default.yaml` version**

Set `meta.meridian_version: "v4.4"`.

**2. Add index-driven conflict detection to skill-manager**

In `.agents/skills/meridian-skill-manager/SKILL.md`, add Step 1a (index-driven scope)
before the existing free-form grep scan. The audit checklist should now have two sub-steps:
1a (MEMORY_INDEX domain/skill lookup) and 1b (free-form scan for L1 blocks only).

**3. Add BAD/GOOD anchors to skill creation workflow**

In `.agents/skills/meridian-skill-manager/SKILL.md`, Step 2 of the creation workflow
should explicitly show a BAD example (missing audit) and a GOOD example (audit performed
before writing). See Appendix B in this file for the full template.

**4. L1_CONTEXT.md version header**

The L1 header now reads `meridian_version` from `weights.default.yaml` at generation
time rather than hardcoding it. No file change required — regenerate L1 by running
`weight_memory.py --generate-l1` after updating `weights.default.yaml`.
