---
name: meridian-skill-manager
description: 'Meridian skill lifecycle management: conflict detection between skills, circular-load detection, context poisoning guards, user-confirmation gate. Load when: creating a new skill, updating an existing skill, SESSION_END close checklist, skill trigger keyword audit.'
---

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
