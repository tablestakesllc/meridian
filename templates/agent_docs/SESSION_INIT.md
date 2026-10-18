## Current State (Agent-Maintained)
> Written by the agent at session close. Read this first for rapid state reconstruction.

**Last branch:** `<branch>`
**Last commit:** `<hash>` — <description>
**Next priority item:** <item>
**Open blockers:** None.
**Last updated:** <YYYY-MM-DD PDT>

---

# Session-Start Checklist

<!-- latitude:halt -->
> **HALT.** Before you advance past this block, check your available MCP tools.
>
> If `get_context_for_task` and `load_blocks` are in your tool list, Latitude is
> running. **Stop reading this file** and call the `bootstrap` **tool** now. The
> bootstrap tool delivers everything in this file.
>
> BAD:  Seeing the redirect but continuing to read the checklist steps anyway.
> GOOD: Finding the Latitude tools and calling the `bootstrap` tool.
>
> Continue only when Latitude tools are absent.
<!-- /latitude:halt -->

---

<!-- meridian:fill id="session-init-title" -->
Write the H1 title with the project name: `# Session Bootstrap — <Project Name>`.
<!-- /meridian:fill -->

> **Run this checklist at the start of every session before providing a briefing or accepting a task.**
> Steps must be completed in order. Do not skip or reorder.

---

## 1. Read Current State

The Current State block is at the very top of this file. Record:
- Active branch, last commit, next priority item, open blockers.

```
[ ] Current State block read
```

---

## 2. Load L1 Context + Compaction Protocol

If `agent_docs/L1_CONTEXT.md` is missing (fresh clone or first run):
```bash
python .agents/skills/meridian-v4/weight_memory.py --generate-l1
```

Then read **`agent_docs/L1_CONTEXT.md`** in full — it contains the operating rules and
the file→skill routing table. Then load skill: `meridian-compaction`.

```
[ ] L1_CONTEXT.md read in full
[ ] File → Skill Routing Table noted
[ ] meridian-compaction skill loaded
```

---

## 3. Read Most Recent PROMPT_LOG Session

```bash
grep -n "^## Session:" agent_docs/PROMPT_LOG.md | tail -1
```

Read from that line number to end of file.

```
[ ] Most recent PROMPT_LOG session read
```

---

## 4. Confirm Branch

```bash
git branch --show-current
```

<!-- meridian:fill id="branch-rules" -->
State this project's branch rules in one to three lines: the default branch, where work happens, and which branches the agent must never commit to directly.
<!-- /meridian:fill -->

```
[ ] Active branch identified — branch rules applied
```

---

## 5. Verify Merge Driver

```bash
git config --local include.path
```

Expected output: `../.gitconfig`

If missing or empty, stop and tell the user:
> "One-time setup required: run `git config --local include.path ../.gitconfig` to activate the merge driver, then continue."

```
[ ] Merge driver active (../.gitconfig)
```

---

## 6. Reset Context Swap

```bash
mkdir -p .agent && printf '{}' > .agent/context_swap.json
```

Do NOT delete the file. Do NOT read the file before overwriting.

```
[ ] context_swap.json reset to {}
```

---

## 7. Output Confirmation and Open PROMPT_LOG Entry

Output this exact line before the briefing:

> `Bootstrap complete — SESSION_INIT ✓ | L1 ✓ | PROMPT_LOG ✓ | branch: <name> | merge driver ✓`

Then run `git config user.name` and append to the bottom of `agent_docs/PROMPT_LOG.md`:

```
## Session: YYYY-MM-DD HH:MM PDT — <git config user.name>
### Context at Session Start
[one-sentence summary including current branch]

### Prompts

| Time (PDT) | Prompt | Commit |
|---|---|---|
```

Provide a concise briefing — branch, last commit, backlog in priority order, open blockers.
Then wait for the first task.

---

## Edge Cases (first-time setup only)

**`.agent/weights.yaml` missing** — run once, before step 2:
```bash
python .agents/skills/meridian-v4/weight_memory.py --seed
```

**`agent_docs/L1_CONTEXT.md` missing** — step 2's `--generate-l1` fallback.

---

## File Map

| File | Role | Committed? |
|---|---|---|
| `agent_docs/SESSION_INIT.md` | Session-start checklist and Current State | Yes |
| `agent_docs/SESSION_END.md` | Session-close checklist | Yes |
| `agent_docs/PROMPT_LOG.md` | Append-only log of user prompts per session | Yes |
| `agent_docs/MEMORY.md` | Raw wiki — §0 operating rules plus numbered sections; never delete sections | Yes |
| `agent_docs/MEMORY_INDEX.yaml` | Shared block structure — IDs, tags, deps, summaries, status | Yes |
| `agent_docs/weights.default.yaml` | Seed weights, thresholds, meridian_version, contract_version | Yes |
| `agent_docs/L1_CONTEXT.md` | Auto-generated hot-load context | No (generated) |
| `agent_docs/meridian-manifest.json` | Seed bundle manifest (installed version and file hashes) | Yes |
| `agent_docs/AGENT_POINTER.md` | Source text for the agent auto-load file (`meridian:pointer` block) | Yes |
| `.agents/skills/meridian-v4/weight_memory.py` | Weight manager script | Yes |
| `.agents/skills/<dir>/SKILL.md` | Skills — core Meridian skills and domain skills | Yes |
| `.agent/weights.yaml` | Per-developer live weights | No (gitignored) |
| `.agent/context_swap.json` | Session checkpoint | No (gitignored) |
