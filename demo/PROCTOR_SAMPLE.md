> **How to use this file:**
> Give this prompt to a fresh, non-Meridian agent after both demo agents have completed
> their runs. This agent has no context about either codebase, no knowledge of which
> agent had Meridian installed, and no prior relationship to this demo.
>
> Provide the proctor with access to both repository directories:
> - One directory containing Agent A's work
> - One directory containing Agent B's work
>
> Do not tell the proctor which agent had Meridian. Let it evaluate on technical merit.

---

## Task Prompt

---

You are a neutral technical evaluator. Two AI coding agents were given this identical task:

> Improve test coverage for the Windows Event Log input plugin
> (`plugins/inputs/win_eventlog`) in the Telegraf codebase.

You have been given access to two repositories — call them **Repo A** and **Repo B** —
each representing one agent's completed work. You do not know which agent had any
special tooling installed. Evaluate on technical merit only.

---

## Step 1: Read the Evaluation Files

Each agent was instructed to write a structured evaluation to `meridian-demo-eval.md`
in the repository root.

If either file is missing, note the failure and fall back to any available stdout
output or test files.

---

## Step 2: Review the Actual Test Code

Do not rely solely on the agents' self-reports. Read the test files directly.

```bash
# Find new or modified test files in each repo
git -C repo-a diff HEAD~1 --name-only | grep _test
git -C repo-b diff HEAD~1 --name-only | grep _test

# Check for uncommitted work
git -C repo-a status --short
git -C repo-b status --short

# Browse the test directory directly
ls repo-a/plugins/inputs/win_eventlog/
ls repo-b/plugins/inputs/win_eventlog/

# Read each test file in full
cat repo-a/plugins/inputs/win_eventlog/*_test.go
cat repo-b/plugins/inputs/win_eventlog/*_test.go
```

---

## Step 3: Verify Coverage Claims

Do not trust the coverage numbers in the evaluation files without verifying them.

```bash
cd repo-a
go test -coverprofile=verify.out ./plugins/inputs/win_eventlog/... 2>&1
go tool cover -func=verify.out
cd ..

cd repo-b
go test -coverprofile=verify.out ./plugins/inputs/win_eventlog/... 2>&1
go tool cover -func=verify.out
cd ..
```

Note any discrepancy between the claimed and verified coverage.

---

## Step 4: Score Against the Rubric

Score each agent **1–5** on each dimension. Use half-points if needed (e.g., 3.5).

### Primary rubric (scored)

| Dimension | Description | Weight |
|---|---|---|
| **Test correctness** | Tests compile, pass, and test what they claim. No false asserts, no tautologies, no tests that pass regardless of behavior. | 25% |
| **Coverage delta** | Verified improvement in total coverage percentage. Raw delta, not self-reported. | 15% |
| **Convention adherence** | Correct use of `testutil.Accumulator`, Windows build constraints on test files, snake_case field names, `acc.AddError()` pattern, `init()` registration awareness. | 20% |
| **Narration quality** | Did the agent state failure scenario, operational importance, and Telegraf convention for each test before writing it? Specificity matters — generic Go narration scores lower than Telegraf-specific narration. Deployment-level reasoning (how operators use the plugin in production) scores higher than code-level reasoning. | 15% |
| **Efficiency** | Coverage delta per minute of elapsed time. Use the agent's reported elapsed time. If not reported, note the gap but do not penalize if the work quality is high. | 10% |

### Meridian dimensions (scored, inform verdict)

These three dimensions are not in the primary rubric but must be assessed separately.
They address whether the agent behaved like a capable engineer who understood the task,
not just a code generator that satisfied a metric.

| Dimension | Description | Weight |
|---|---|---|
| **Prompt adherence** | Did the agent honor the full intent of the task, or only its minimum viable interpretation? For a plugin named "Windows Event Log," did the agent attempt to test Windows-specific behavior, or only what compiles on the evaluation platform? | 10% |
| **Contextual knowledge** | Does the agent's output show understanding beyond what is visible in the immediate source files — e.g., how the plugin is deployed, what operators depend on, what past bugs looked like? Cite specific narration text as evidence. Note: this is inferential. Do not claim causal attribution unless you have a control condition. | 3% |
| **Completeness** | Did the agent deliver committed, runnable work that durably improves the repository? Check `git status` and `git log`. Untracked files, staged-but-uncommitted changes, or missing commits are completeness failures. | 2% |

---

## Step 5: Write the Proctor Report

Write your complete evaluation to **both stdout and `meridian-proctor-report.md`**
in the current directory. Write stdout first, then write the file as a clean copy.

```markdown
# Meridian Demo — Proctor Report

**Date:** YYYY-MM-DD
**Proctor:** [Your model/version]
**Note:** Agent identities are blinded. Repo A and Repo B labels are assigned
arbitrarily and do not indicate which agent had special tooling.

---

## Executive Summary

[2–4 sentences. Frame around the three Meridian dimensions: contextual knowledge,
prompt adherence, completeness. Which repo produced better work, and the single most
important reason why. Be specific — cite actual test names, coverage numbers, or
convention patterns.]

---

## Repo A — Evaluation

### Timing
- Elapsed: [from eval file, or "not reported"]
- Commit status: [committed / untracked / not reported]

### Coverage (verified)
| Metric | Before | After | Delta |
|---|---|---|---|
| Total | X% | Y% | +Z% |

Discrepancy from self-report: [none | describe]

### Scores
| Dimension | Score (1–5) | Key evidence |
|---|---|---|
| Test correctness | X | ... |
| Coverage delta | X | ... |
| Convention adherence | X | ... |
| Narration quality | X | ... |
| Efficiency | X | ... |
| Prompt adherence | X | ... |
| Contextual knowledge | X | ... |
| Completeness | X | ... |
| **Weighted total** | **X.X** | |

### Notable Strengths
[Specific things Repo A did well — cite test names or patterns]

### Notable Gaps
[Specific things Repo A missed or got wrong — cite evidence]

---

## Repo B — Evaluation

[Same structure as Repo A]

---

## Comparative Analysis

### Contextual knowledge from commit history
[Did either agent show operational or deployment-level knowledge beyond what is visible
in the source files? Cite specific narration text. If yes, assess whether it is
plausibly attributable to commit-history seeding or simply to thorough reading.
Be honest about the inferential gap — a single trial cannot prove causation.]

### Completeness of results
[Did either agent leave work uncommitted or untracked? Quantify: tests committed vs
untracked, Windows coverage attempted vs not attempted. State plainly whether each
agent left the repository in a better state than they found it.]

### Prompt adherence
[Quote the original task. Identify the minimum viable interpretation and the full
interpretation. Which agent chose which, and what evidence supports that reading?
If both interpreted the task the same way, say so.]

### Domain awareness signal
[The core question: did one repo consistently use Telegraf-specific patterns where the
other used generic Go patterns? Examples to look for:
- `testutil.Accumulator` vs custom result capture
- `//go:build windows` on test files
- `acc.AddError()` vs `return err` in Gather()
- snake_case field names vs camelCase
- `init()` registration awareness
Cite specific line-level examples from both repos.]

### Coverage delta comparison
[Side-by-side numbers. Which agent improved coverage more, and on which functions?]

### Timing comparison
[Elapsed times, and coverage-per-minute efficiency if both are reported]

---

## Final Verdict

| Dimension | Weight | Repo A | Repo B | Winner |
|---|---|---|---|---|
| Test correctness | 25% | X | Y | A / B / Tie |
| Coverage delta | 15% | X | Y | A / B / Tie |
| Convention adherence | 20% | X | Y | A / B / Tie |
| Narration quality | 15% | X | Y | A / B / Tie |
| Efficiency | 10% | X | Y | A / B / Tie |
| Prompt adherence | 10% | X | Y | A / B / Tie |
| Contextual knowledge | 3% | X | Y | A / B / Tie |
| Completeness | 2% | X | Y | A / B / Tie |
| **Weighted total** | 100% | **X.X** | **Y.Y** | **A / B / Tie** |

**Winner: Repo [A / B / Tie]**

[One paragraph per Meridian dimension, grounded and specific. Avoid agent hype — state
what the output shows, not what the tooling promises. If the causal link between
tooling and behavior cannot be established from a single trial, say so.]
```

---

## Proctor Notes

- **Blinding is intentional.** Do not ask which repo had Meridian. The evaluation
  should be reproducible by any reviewer who sees only the code.
- **Verify, don't trust.** Always run the coverage commands yourself. Agents
  misreport coverage numbers.
- **Convention adherence is the key signal.** A generic agent trained on Go will write
  correct tests. The question is whether it writes *Telegraf-correct* tests. Look for
  `testutil.Accumulator`, build constraints, and `acc.AddError()` — these are the
  patterns a cold-start agent gets wrong and a Meridian-seeded agent should get right.
- **Narration quality is observable.** Read the pre-test statements in the eval file
  or in code comments. Generic narration: "this tests error handling." Telegraf-specific
  narration: "Gather() calls acc.AddError() on partial failure — without this test, a
  misconfigured channel silently drops metrics for the entire collection interval."
- **If both agents produce identical quality:** that is a valid finding. Report it
  honestly. It means the task was too easy to differentiate, not that Meridian failed.

---

Copyright 2026 TableStakes LLC. Licensed under the Apache License, Version 2.0.
