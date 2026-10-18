<!-- meridian:fill id="session-end-title" -->
Write the H1 title with the project name: `# Session Close — <Project Name>`.
<!-- /meridian:fill -->

> **Run this checklist at the end of every session before yielding back to the user.**
> Steps must be done in order.

---

## 0. Skill Audit (if any skill was created or modified this session)

Load `meridian-skill-manager` → run its audit checks → resolve findings with the user → then continue.

```
[ ] Skill audit run (or no skill changed)
```

---

## 1. Write Session Context Snapshot

Write `.agent/context_swap.json` per the `meridian-compaction` Pre-Compaction Checkpoint protocol. Read it back in full and use it as the reference for the remaining steps.

```
[ ] context_swap.json written and read back
```

---

## 2. Tests and Checks

<!-- meridian:fill id="pre-push-checks" -->
List the commands that must pass before any push in this project (tests, lint, build), one per line in a bash block, with a `[ ]` checkbox per command. If the project has none, write "No automated checks" and keep the step.
<!-- /meridian:fill -->

---

## 3. Update `agent_docs/SESSION_INIT.md` Current State

- **Last branch**, **Last commit** (hash + one-line description), **Next priority item**, **Open blockers**, **Last updated** (date + PDT/PST)

```
[ ] Current State updated
```

---

## 4. Update `agent_docs/PROMPT_LOG.md`

One row per user prompt, then a close row with the current time:

```
| YYYY-MM-DD HH:MM PDT | Session close — docs updated | `<hash>` |
```

Times are US Pacific: PST (UTC−8) November to mid-March, PDT (UTC−7) mid-March to November.

```
[ ] All prompts logged, close row added
```

---

## 5. Update `agent_docs/MEMORY.md` (if applicable)

For any non-obvious bug, constraint, design decision or tooling quirk: add a numbered section with a block annotation, an entry in `MEMORY_INDEX.yaml` and a seed in `weights.default.yaml` (skill `meridian-v4` → Adding a New Block).

```
[ ] MEMORY.md / index / weights updated (or nothing new)
```

---

## 6. Update Memory Weights

```bash
python .agents/skills/meridian-v4/weight_memory.py \
    --used   "BLOCK_ID,..." \
    --loaded "BLOCK_ID,..." \
    --date   "YYYY-MM-DD"
```

Include every L1 block in `--loaded`. `L1_CONTEXT.md` is regenerated automatically. Then refresh `.agent/context_swap.json` with the final block IDs and head.

```
[ ] Weights updated; context_swap.json refreshed
```

---

## 7. Commit

```bash
git status --short
git add <files changed this session>
git commit -m "chore(docs): session-end"
```

```
BAD:  git commit -m "chore(docs): session-end [skip ci]" — squash merges copy the marker into the merge commit and the main branch skips CI
GOOD: git commit -m "chore(docs): session-end"
```

Push only when the user asks.

```
[ ] Committed; pushed only if the user asked
```

---

## 8. Report to the User

Branch and head, commits this session, check results, docs updated, and next steps.

---

## Quick-Reference Checklist

```
[ ] Skill audit (if skills changed)   (step 0)
[ ] context_swap.json written         (step 1)
[ ] Tests and checks                  (step 2)
[ ] SESSION_INIT Current State        (step 3)
[ ] PROMPT_LOG                        (step 4)
[ ] MEMORY.md (if applicable)         (step 5)
[ ] weight_memory.py run              (step 6)
[ ] Commit; no skip markers           (step 7)
[ ] Report                            (step 8)
```
