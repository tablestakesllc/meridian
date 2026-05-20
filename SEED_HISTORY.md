# Meridian — Git History Memory Seeding Prompt (Generic)

> **How to use this file:**
> Give this document to an agent on any repository that already has Meridian installed
> (see MERIDIAN_BOOTSTRAP.md) but has no memory blocks yet. The agent will analyze the
> repository's git history and codebase to generate an initial set of meaningful memory
> blocks.
>
> Run this prompt ONCE at project start, or when onboarding Meridian onto an existing
> codebase. The output is a populated MEMORY_INDEX.yaml and a populated MEMORY.md.

---

## Your Task

You are seeding the Meridian Agent Context and Memory System for this repository. Your
goal is to analyze the project's history, conventions, and known pain points and convert
that knowledge into a structured set of memory blocks.

A good memory block is:
- A discrete, actionable piece of knowledge
- Something that caused a bug, required a non-obvious decision, or defines a convention
  that is not obvious from reading the code alone
- Specific enough that it changes what an agent would do on a task

A bad memory block is:
- A summary of what the project does (that belongs in a README)
- A description of a feature (not a pitfall or convention)
- Anything so obvious it would be in the first result of a web search

---

## Phase 1: Understand the Repository Shape

Run these commands and read the output before doing anything else.

```bash
# Top-level structure
ls -la

# Primary languages and file counts
find . -name "*.go" -o -name "*.ts" -o -name "*.py" -o -name "*.js" \
  | grep -v node_modules | grep -v .git | grep -v vendor \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20

# Read CONTRIBUTING.md, CHANGELOG.md, and any ADR (Architecture Decision Record) files
cat CONTRIBUTING.md 2>/dev/null || echo "No CONTRIBUTING.md"
ls docs/ 2>/dev/null
find . -name "*.md" -path "*/adr/*" -o -name "*.md" -path "*/decisions/*" 2>/dev/null
```

Read the output. Identify:
- Primary tech stack (languages, frameworks)
- Whether there is a formal contribution guide with conventions
- Whether there are architecture decision records

---

## Phase 2: Find the Hotspots

These commands identify which files and areas change most frequently. High-churn files
are where conventions matter most and where agents are most likely to make mistakes.

```bash
# Files changed most frequently across all history
git log --all --name-only --format='' | grep -v '^$' \
  | sort | uniq -c | sort -rn | head -30

# Directories with the most commits touching them (excludes top-level files)
git log --all --name-only --format='' | grep '/' \
  | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn | head -20

# Files that are almost always changed together (co-change pairs)
git log --all --name-only --format='%H' | awk '
  /^[0-9a-f]{40}$/ { hash=$0; next }
  NF { files[hash][NF++]=$0 }
' 2>/dev/null || \
git log --all --stat --format='' | grep '|' | awk '{print $1}' \
  | sort | uniq -c | sort -rn | head -20
```

Note the top 10 hotspot files. These will generate the most valuable memory blocks.

---

## Phase 3: Find the Documented Pain Points

```bash
# Search for TODO, FIXME, HACK, and WARNING comments
grep -rn "TODO\|FIXME\|HACK\|WARNING\|WORKAROUND\|DO NOT\|DANGER" \
  --include="*.go" --include="*.ts" --include="*.py" --include="*.js" \
  --include="*.yaml" --include="*.md" \
  . 2>/dev/null | grep -v ".git" | grep -v "vendor" | grep -v "node_modules" \
  | head -50

# Search for explicit "do not" patterns in comments
grep -rn "do not\|don't\|never\|always\|must\|required" \
  --include="*.go" --include="*.ts" --include="*.py" \
  . 2>/dev/null | grep -v ".git" | grep -v "vendor" | grep -v "node_modules" \
  | grep -i "//\|#\s" | head -30
```

Each FIXME, HACK, or strong-language comment is a candidate memory block. They document
decisions the original authors wanted future contributors to know.

---

## Phase 4: Analyze Commit Messages for Patterns

```bash
# Full commit log — last 500 commits
git log --oneline -500

# Commits that mention fixes, bugs, regressions, or breaking changes
git log --oneline --all --grep="fix\|bug\|regression\|breaking\|revert\|hotfix" \
  -100

# Conventional commit breaking-change marker (! after scope)
# The keyword grep above does not match `fix(config)!:` — this catches it
git log --oneline --all --grep="!" | head -20

# Commits that mention specific architectural areas
git log --oneline --all --grep="refactor\|migrate\|upgrade\|deprecat" -50
```

Look for:
- Recurring fix patterns (same area fixed multiple times = a non-obvious constraint)
- Revert commits (something was tried and undone = a known trap)
- Migration commits (the project changed how it does something = agents need to know
  the current way, not the old way)

---

## Phase 5: Read Key Conventions Files

```bash
# Makefile or task runner (shows how to build, test, lint)
cat Makefile 2>/dev/null | head -80
cat Taskfile.yml 2>/dev/null | head -80

# CI configuration (shows what checks must pass)
cat .github/workflows/*.yml 2>/dev/null | head -200
cat .gitlab-ci.yml 2>/dev/null | head -100

# Linter configuration
cat .golangci.yml 2>/dev/null
cat .eslintrc* 2>/dev/null
cat pyproject.toml 2>/dev/null | head -60

# Test conventions (look at a sample test file from the most-changed area)
find . -name "*_test.go" -o -name "*.test.ts" -o -name "test_*.py" \
  | grep -v vendor | grep -v node_modules | head -5
```

---

## Phase 6: Synthesize Memory Blocks

Using everything collected above, generate memory blocks. Each block follows this
template:

```
ID: <kebab-case, descriptive, 2-5 words>
Domain: <testing | cicd | frontend | backend | db | security | design | general>
Tags: <3-6 keywords that would appear in a task where this block is needed>
Summary (one line): <what an agent needs to know>
Files: <1-3 most relevant files>

MEMORY.md section content:
## N. <Short Topic Title>

**Added:** <today's date> (Meridian seed pass)

<One-sentence problem statement — what goes wrong without this knowledge.>

**Convention / Fix:**
<What the agent must do. Specific. Actionable.>

**Why:**
<One sentence on the root cause or design intent.>
```

Generate between 8 and 20 blocks. Fewer is better. A block that isn't specific enough to
change agent behavior should be cut.

---

## Phase 7: Populate the Files

### In MEMORY_INDEX.yaml

Add each block to the `blocks:` list using the schema from MERIDIAN_BOOTSTRAP.md.
Assign `seed_weight: 5.0` to all blocks in weights.default.yaml.

> **Elevated seeds:** If onboarding an existing production codebase, identify 2–3
> blocks that are critical to nearly every agent task (e.g., the primary plugin
> registration pattern, the project's test helper contract). Seed those at `8.5`
> instead of `5.0`. This puts real grounding into L1 immediately rather than waiting
> for organic weight accumulation over several sessions.

### In MEMORY.md

Add each block as a numbered section. Use the annotation format:

```markdown
<!-- block: <id> | domain: <domain> | mem: §<N> -->
<Summary line — also appears in L1 when weight is high enough>
<!-- /l1-summary -->

<Full detail — available on demand, not emitted into L1>
<!-- /block -->
```

### Run the seed and generate L1

```bash
python tools/weight_memory.py --seed
python tools/weight_memory.py --generate-l1
python tools/weight_memory.py --check-defaults
```

---

## Phase 8: Commit the Seed

```bash
git add agent_docs/MEMORY_INDEX.yaml agent_docs/MEMORY.md \
  agent_docs/weights.default.yaml agent_docs/SESSION_INIT.md \
  tools/weight_memory.py
git commit -m "feat(meridian): initial memory seed from git history analysis"
```

Do NOT commit `.agent/weights.yaml` or `agent_docs/L1_CONTEXT.md` — these are
gitignored and developer-local.

---

## Quality Check Before Committing

For each block you generated, answer these two questions:
1. Would an agent behave differently on a real task if it had this block versus not?
2. Is this specific to THIS repository, or is it generic knowledge any agent already has?

If the answer to question 1 is "probably not" or question 2 is "it's generic" — cut the
block. The goal is grounded, specific, repository-earned knowledge. Not a tutorial.
