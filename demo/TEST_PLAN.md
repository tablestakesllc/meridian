# Meridian v4.3 Demo — Test Plan

This document records the methodology used for the Meridian v4.3 demo comparison.
It can be reproduced on any codebase of your choosing.

---

## Objective

Compare an AI coding agent with no persistent memory (the **generic agent**) against
the same agent equipped with the Meridian v4.3 memory system (the **Meridian agent**)
on an identical real-world coding task. Evaluate both agents using a neutral third-party
proctor agent that has no knowledge of which repo is which.

---

## Test Codebase

Choose a real open-source repository with meaningful test coverage gaps. A good
candidate has:
- An active git history (enough signal for the seed prompt)
- At least one non-trivial module or plugin with incomplete tests
- A consistent testing convention the agents can follow

---

## Agents

| Agent | Memory | System prompt |
|---|---|---|
| Generic | None — fresh session, no persistent instructions | Default only |
| Meridian | Meridian v4.3 (bootstrap + seeded MEMORY_INDEX) | BOOTSTRAP.md + seeded memory |

Both agents use the same underlying model and receive the identical task prompt
(`TASK_PROMPT.md`). The only difference is the Meridian agent's session context
(L1_CONTEXT.md + skill files loaded via session-init ritual).

---

## Phase 1: Repository Setup

Both agents operate on independent forks/clones of the chosen codebase.

**Repo A** — generic agent workspace: clean clone, no additional files, no instructions
beyond the task prompt.

**Repo B** — Meridian agent workspace: same clone, then Meridian is bootstrapped
(see Phase 2).

---

## Phase 2: Meridian Bootstrap (Repo B only)

The Meridian agent is initialized using `BOOTSTRAP.md` — the canonical
setup prompt as it existed at the time of the demo.

Steps performed by the agent:
1. Creates directory structure (`agent_docs/`, `.agent/`, `tools/`, `.github/skills/`)
2. Creates `MEMORY_INDEX.yaml` (initially empty blocks list)
3. Creates `weights.default.yaml` with seed thresholds
4. Creates `SESSION_INIT.md`, `SESSION_END.md`, `MEMORY.md`, `PROMPT_LOG.md`
5. Creates `.github/copilot-instructions.md` with session-start and skill dispatch
6. Creates core skill files
7. Runs `python tools/weight_memory.py --seed`
8. Runs `python tools/weight_memory.py --generate-l1`

---

## Phase 3: Memory Seeding (Repo B only)

After bootstrap, the Meridian agent runs through `SEED_HISTORY.md` —
the git history analysis prompt — to generate initial memory blocks from the chosen
repository's commit history.

The seed prompt analyzes:
- High-churn files and directories
- Bug fix patterns from commit messages
- Architectural and dependency patterns
- Breaking changes and deprecation signals

Output: a populated `MEMORY_INDEX.yaml` and `L1_CONTEXT.md` reflecting the seeded
blocks, grounded in the codebase's actual history.

---

## Phase 4: Demo Environment Setup

Both repos are verified before the task runs:

**Generic (Repo A):**
- Clean clone of the target codebase
- No additional files, no instructions beyond the task prompt

**Meridian (Repo B):**
- Same clone + bootstrapped Meridian installation
- `agent_docs/L1_CONTEXT.md` populated with seeded blocks
- `agent_docs/SESSION_INIT.md` Current State block filled in
- Agent runs the session-init ritual (read SESSION_INIT, read L1_CONTEXT, check branch)

Both agents have access to the internet and to the source tree. Both receive the task
prompt verbatim with no additional framing.

---

## Phase 5: Agent Runs

Both agents receive the identical prompt: **`TASK_PROMPT.md`** (included in this
folder). Each agent runs independently with no access to the other agent's work.

---

## Phase 6: Proctor Evaluation

After both agents complete, a fresh non-Meridian agent is given
**`PROCTOR_PROMPT.md`** (included in this folder) with access to both repos labeled
only as `repo-a/` and `repo-b/`.

The proctor is not told which repo used Meridian. It has no prior context about the
experiment.

**Proctor rubric (5 dimensions):**

| Dimension | Weight |
|---|---|
| Test correctness | 30% |
| Coverage delta | 20% |
| Convention adherence | 25% |
| Narration quality | 15% |
| Efficiency | 10% |

The proctor is instructed to:
- Read the agent's self-evaluation from each repo
- Read the actual test code diffs
- Independently verify coverage claims
- Score each repo on the rubric
- Write a proctor report with findings

---

## Notes and Limitations

1. **Cold memory** — the Meridian agent has no prior sessions on the chosen codebase.
   All memory is generated in one seed pass. A real Meridian deployment would have
   accumulated session data over time.

2. **Proctor blinding** — the proctor agent has no knowledge of which repo is Meridian
   and no relationship to the agents that ran the task.

3. **Task selection matters** — results will vary based on the chosen module and
   codebase. Prefer tasks with a non-trivial interpretation gap to make the test
   meaningful.

---

## Folder Contents

| File | Description |
|---|---|
| `TEST_PLAN.md` | This document |
| `BOOTSTRAP.md` | Bootstrap prompt used to initialize Meridian on the Meridian agent repo |
| `SEED_HISTORY.md` | Git history seed prompt run on the test codebase clone |
| `TASK_PROMPT.md` | Task prompt given identically to both agents |
| `PROCTOR_PROMPT.md` | Proctor evaluation prompt — used by a blinded third agent |

---

Copyright 2026 TableStakes LLC. Licensed under the Apache License, Version 2.0.
