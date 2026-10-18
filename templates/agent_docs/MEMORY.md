<!-- meridian:fill id="memory-title" -->
Write the file's H1 title with the project name: `# <Project Name> — Memory and Design Decisions`.
<!-- /meridian:fill -->

> **Meridian memory.** This file is the content source for memory blocks. The index lives in
> `agent_docs/MEMORY_INDEX.yaml`; hot-loaded blocks are compiled into `agent_docs/L1_CONTEXT.md`.
> Do not read this file in full at session start. Check the Memory Index and load only the
> sections that apply.
>
> Block annotation: `<!-- block: <id> | domain: <domain> | mem: §<N> -->` … `<!-- /block -->`.
> An optional `<!-- /l1-summary -->` line inside a block ends the part that goes into L1.
> Sections are never deleted; mark them deprecated instead.

---

## Memory Index

| § | Block | Topic |
|---|---|---|
| 0 | `agent-operating-prefs` | Agent operating rules for this repository |
| 1 | `meridian-memory-files` | How to change Meridian's own memory files |

---

## §0 — Agent Operating Preferences

<!-- block: agent-operating-prefs | domain: operations | mem: §0 -->

**Session bootstrap:** `agent_docs/SESSION_INIT.md` is the single source of truth for session start, and `agent_docs/SESSION_END.md` for session close. The agent auto-load file is a thin pointer to `SESSION_INIT.md`; never duplicate its checklist elsewhere.

**Memory files are read in full:** never read `SESSION_INIT.md`, `SESSION_END.md`, `L1_CONTEXT.md`, `MEMORY_INDEX.yaml` or any `SKILL.md` in partial ranges.

**Skills and routing:** domain guidance lives in `.agents/skills/`. When opening a file, check the File → Skill Routing Table in `agent_docs/L1_CONTEXT.md` and load the listed skills first.

**Memory upkeep:** record non-obvious bugs, constraints and design decisions as new §N sections with an index entry and a seed weight. Never edit `L1_CONTEXT.md` or `.agent/weights.yaml` by hand; `weight_memory.py` regenerates them at session end.

**Memory custody — Meridian owns all agent memory for this project:** all durable project knowledge lives in Meridian (`agent_docs/MEMORY.md` + `MEMORY_INDEX.yaml`). Do not keep project knowledge in an agent's own memory store, for example Claude Code auto-memory (`~/.claude/projects/<project>/memory/`), Cursor Memories, Windsurf Cascade Memories, a Cline Memory Bank (`memory-bank/`), or any other per-tool or editor memory feature: two copies drift, and the agent then acts on the stale one without knowing it. When you learn something durable, write it to Meridian as a §N section with an index entry and a seed weight. If an agent memory store already holds knowledge about this project: (1) tell the user and list what it holds; (2) review each entry against Meridian for duplication; (3) with the user's agreement, merge only the unique information into Meridian, updating an existing section where one already covers the topic; (4) delete the agent-specific memory entries; (5) write a single agent memory entry stating that Meridian owns all agent memory for this project and that `agent_docs/SESSION_INIT.md` is the entry point. That pointer is the only permitted content of an agent memory store for this project. Never move secrets, credentials, personal data or anything about other private projects into Meridian: its files are committed and may be public.

**Git:** never push without explicit instruction from the user. Never write `[skip ci]` or similar skip markers in a commit message.

<!-- meridian:fill id="operating-rules" -->
Add this project's own always-on rules here as short bold-labelled paragraphs: branch model and merge targets, how to run tests or CI before a push, commit conventions, and anything the agent must never do. Remove this marker when done.
<!-- /meridian:fill -->

<!-- /block -->

---

## 1. Meridian Memory Files

<!-- block: meridian-memory-files | domain: operations | mem: §1 -->
Before editing `agent_docs/MEMORY_INDEX.yaml`, `agent_docs/weights.default.yaml` or `agent_docs/MEMORY.md`, load skill `meridian-v4`. A new block needs all three: the index entry (with `files:` globs), a seed weight, and a block annotation around its content. Never delete a block or a section; archive is a weight state and deprecation is a `status` value.
<!-- /block -->

---

<!-- meridian:fill id="first-section" -->
Optional. Add the next numbered section, `## 2. <Topic>`, for the most important non-obvious fact about this codebase, with a block annotation around it, an index entry in MEMORY_INDEX.yaml and a seed in weights.default.yaml. Delete this marker if there is nothing to record yet.
<!-- /meridian:fill -->
