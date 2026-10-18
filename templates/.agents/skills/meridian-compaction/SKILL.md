---
name: meridian-compaction
description: 'Meridian session compaction checkpoint and recovery protocol. Owns context_swap.json format specification. Always loaded by SESSION_INIT.md. Use when: TASK RESUMPTION detected, conversation compaction, session resume, checkpoint write, continuing interrupted work.'
---

# Meridian Compaction Recovery

Loaded at bootstrap. Owns the checkpoint and recovery lifecycle for
context_swap.json. This file is read on compaction recovery and written on
session-end and context-pressure events.

---

## context_swap.json Format

{
  "branch": "<current branch>",
  "head": "<git rev-parse HEAD>",
  "session_date": "YYYY-MM-DD",
  "blocks_loaded": ["id1", "id2"],
  "blocks_used": ["id1"],
  "decisions": ["one-line key decision"],
  "issues_created": [
    {
      "number": 0,
      "title": "<title>",
      "why": "<one-line reason>"
    }
  ],
  "task": "one-line: what was being done"
}

This file is gitignored. SESSION_INIT step 6 wipes it to {} at full bootstrap.
SESSION_END step 0b writes a session snapshot before doc updates.

---

## Pre-Compaction Checkpoint (Write)

When context pressure is high (approaching token limit, multiple compactions in
session, user warns) or on every git commit, extract the following from the
conversation without re-reading any files:

| Field | How to extract |
|---|---|
| branch | Find "On \`name\`" in conversation or run git branch --show-current |
| head | Find "at \`hash\`" in conversation or run git rev-parse HEAD |
| blocks_loaded | Scan conversation for --loaded args or SKILL.md file read events |
| blocks_used | Scan conversation for --used args or block content directly applied |
| task | The last user prompt before this checkpoint |
| decisions | Scan for "decision:", "agreed:", "confirmed:", "decided:" |
| issues | Scan for "#NNN" creation or "gh issue create" commands |

Write to .agent/context_swap.json. Do not read files to populate fields.
The goal is minimal token extraction from the conversation already in memory.
Do not validate block IDs against MEMORY_INDEX.yaml at write time.

BAD: Reading MEMORY_INDEX.yaml during checkpoint -- burns tokens on validation
     that rehydration will repeat; doubles the cost with no gain
GOOD: Write what the conversation contains; validate on rehydration if needed

---

## Post-Compaction Rehydration (Read)

When "TASK RESUMPTION" appears in the conversation or compaction language is
detected, run this protocol instead of the full SESSION_INIT checklist:

Step 1 -- Read agent_docs/SESSION_INIT.md Current State block only. Record
branch, last commit, blockers. Do not read the full file.

Step 2 -- Read agent_docs/L1_CONTEXT.md in full. This recovers operating rules,
the file-to-skill routing table, and the sub-agent handoff block. Meridian
scaffolding must load before context_swap.json so block IDs are interpretable.

Step 3 -- Read .agent/context_swap.json. Block IDs now resolve to known skills
via the routing table from Step 2. Branch sanity-checks against Step 1.

Step 4 -- Run git branch --show-current. Confirm the branch matches what Step 1
and Step 3 expect.

Step 5 -- Report recovered state to user:
"Recovered from compaction. Branch: X. Head: Y. Task: Z. Ready."

Do not rerun the full session-start checklist. Do not read PROMPT_LOG.
Do not re-verify merge driver. Do not wipe context_swap.json.

BAD: Rerunning full SESSION_INIT checklist after compaction -- reads
     PROMPT_LOG, re-verifies merge driver, and burns tokens on steps
     already verified earlier in the same session
GOOD: Recovery protocol above -- 4 targeted reads, no redundant verification

If .agent/context_swap.json reads as {} (empty), fall back to the full
SESSION_INIT checklist. The compaction signal was a false positive.

---

## Timing Rules

Write context_swap.json:
- After each git commit
- After creating a new issue mid-session
- On detection of context pressure (approaching token limit)
- Before any conversation compaction is requested

Read context_swap.json:
- Only during rehydration Step 3 above
- Never during normal SESSION_INIT bootstrap

Wipe context_swap.json:
- SESSION_INIT step 6 resets to {} at full bootstrap start
- Never wipe during recovery
