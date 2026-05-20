# Meridian — Agent Context and Memory System

**Version:** 4.4  
**Publisher:** TableStakes LLC  
**License:** Apache 2.0

The **Meridian Agent Context and Memory System** is a file-native knowledge grounding
system for AI coding agents. It has no server, no vector database, and no external API
dependencies. Everything lives in the repository alongside your code.

---

## The Problem

AI coding agents are stateless. Every session starts from scratch. The agent that
debugged your pgBouncer issue last week has no memory of it today. It will rediscover
the same gotchas, re-debate the same design decisions, and miss the same project
conventions — every time.

Large tool vendors solve this with proprietary memory layers baked into their products.
Meridian solves it with markdown files, a structured index, and an unbiased Python script.

---

## How It Works

Meridian maintains a set of named **memory blocks** — discrete pieces of agent-curated
domain knowledge about your codebase, stored as annotated sections in a plain markdown
wiki.

Each block has a **weight** that changes over time based on how often it is loaded and
used.

At the end of every session, a lightweight script updates block weights and regenerates
a **hot-load file** (`L1_CONTEXT.md`). At the start of the next session, the agent
reads that file before doing anything else. Frequently used knowledge stays in the
hot-load file. Stale knowledge fades to on-demand retrieval. Nothing is ever deleted.

Three tiers:

| Tier | Weight | Behavior |
|---|---|---|
| L1 | ≥ 8.0 | Auto-loaded every session |
| L2 | 2.0 – 7.9 | Loaded on demand via skill trigger keywords |
| Archive | < 2.0 | Retained; recovers automatically when used again |

**Skills** are domain-specific context files loaded in three ways: trigger keywords in
the session, domain area, or a file path referenced directly from a curated memory
block. They route the agent to the right knowledge for the work at hand without
loading everything at once.

---

## What's in the Repo

- `BOOTSTRAP.md`: A step-by-step setup guide prompt for any new repository. Give it to a fresh
  agent and follow along. No prior Meridian knowledge required.
- `SEED_HISTORY.md`: A structured prompt that analyzes a repository's git history to
  generate an initial set of memory blocks. Run it once on a new codebase to give
  Meridian a grounded starting point instead of a blank slate.
- `demo/`: A reproducible test methodology and the prompts used to compare a
  Meridian-equipped agent against a baseline agent on an identical task.

The `weight_memory.py` script is defined in full in Appendix C of `BOOTSTRAP.md`. An
agent can rebuild it from scratch on any repository using that specification.

---

## Getting Started

1. Copy `BOOTSTRAP.md` into the prompt of a fresh agent to instance Meridian.
2. Optionally, copy `SEED_HISTORY.md` into the prompt of the same agent to populate
   your initial memory blocks from git history.
3. Open a clean agent and run `SESSION_INIT.md` to begin your first session.

Total setup time on a new repository: 30–60 minutes.

---

## Design Principles

**File-native.** Every Meridian artifact is a plain text file committed to your
repository. No lock-in, no accounts, no services to run.

**Tool-agnostic.** Meridian works with any AI coding agent that can read files. VS Code
Copilot, Cursor, Claude, a raw API call — if the agent can read a markdown file, it
can use Meridian.

**Earned, not configured.** Weights change based on actual session usage, not manual
tuning. Knowledge that gets used regularly rises to L1 automatically. Knowledge that
becomes irrelevant fades without being deleted.

**Pick what fits.** Use the bootstrap and skip the weight system. Use the skill routing
and skip the session lifecycle. Use the seed prompt to create any part or all of Meridian.
There is no required minimum. All parts of Meridian work on their own.

---

## Versions

| Version | Changes |
|---|---|
| 4.3 | Initial public release. Bootstrap, seed history, weight system, skill routing, session lifecycle. |
| 4.4 | Index-driven conflict detection for skill authoring. BAD/GOOD negative anchor rule for skills. |

---

## Testing

In two double-blind trials, Meridian shaped the context, grounded the memory, and
guided the agent to fully complete the task. The baseline agent (same model, no
Meridian) didn't adhere to the prompt as well and took longer to assess the work.
See `demo/TEST_PLAN.md` for the full methodology.

---

## License

Copyright 2026 TableStakes LLC. Licensed under the Apache License, Version 2.0.  
See [LICENSE](LICENSE) for the full text.
