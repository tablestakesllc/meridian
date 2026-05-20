> **How to use this file:**
> Give this prompt identically to both agents:
> - **Agent A (Generic):** Fresh session, no Meridian installed, no prior context of this codebase.
> - **Agent B (Meridian):** Session with Meridian installed and the seed pass complete.
>
> Do not give either agent any additional context, hints, or supplemental material.
> The prompt below is the complete task specification — copy it verbatim.

---

## Task Prompt

---

You are working in the Telegraf codebase (influxdata/telegraf).

**Record the start time now using the system time.** Write it as:
```
START: YYYY-MM-DD HH:MM:SS
```

---

### Your Goal

Meaningfully improve test coverage for the Windows Event Log input plugin:

```
plugins/inputs/win_eventlog/
```

---

### Before Writing Any Code

1. Read the plugin source files in `plugins/inputs/win_eventlog/`.
2. Establish the baseline coverage. Run:
   ```bash
   go test -coverprofile=coverage_before.out ./plugins/inputs/win_eventlog/... 2>&1
   go tool cover -func=coverage_before.out | grep -v "100.0%"
   ```
3. List every untested function or logical branch you can identify from the source and
   the coverage report. Do this before writing a single test.

---

### For Each Test You Write

Before writing the test code, state the following three things in a comment block or
in your reasoning:

- **Failure scenario:** What specific behavior breaks or goes undetected without this
  test?
- **Operational importance:** Why does this matter to an operator running Telegraf in
  production?
- **Convention used:** Which Telegraf testing convention or pattern does this test
  follow?

Then write the test.

---

### After Writing All Tests

1. Run coverage again:
   ```bash
   go test -coverprofile=coverage_after.out ./plugins/inputs/win_eventlog/... 2>&1
   go tool cover -func=coverage_after.out
   ```
2. Report the coverage delta:
   - Total coverage before → after
   - Per-function improvement (list functions that moved and by how much)
   - Functions still not covered after your changes
3. List any paths you identified as untestable, and briefly explain why (e.g., requires
   live Windows API, requires elevated privileges, external syscall with no interface
   boundary for mocking).

---

### Record End Time and Write Evaluation

**Record the end time now.** Write it as:
```
END: YYYY-MM-DD HH:MM:SS
ELAPSED: X minutes Y seconds
```

Then write the following structured evaluation to **both stdout and the file
`meridian-demo-eval.md`** in the repository root. Write stdout first, then write the
file. The file must be a clean copy — not interleaved with command output.

```markdown
# Demo Evaluation

**Agent:** [describe yourself: model, whether Meridian is installed, session context]
**Date:** YYYY-MM-DD
**Elapsed:** X minutes Y seconds

---

## Coverage Delta

| Metric | Before | After | Delta |
|---|---|---|---|
| Total coverage | X% | Y% | +Z% |

### Functions improved
[List each function, before %, after %]

### Functions still uncovered
[List each function with a brief reason if known]

---

## Tests Written

For each test, provide the full function name and answers to the three pre-test questions.

### `TestFunctionName`
- **Failure scenario:** ...
- **Operational importance:** ...
- **Convention used:** ...

[repeat for each test]

---

## Untestable Paths

| Path | Reason |
|---|---|
| ... | ... |

---

## Self-Assessment

Honest evaluation of your own work:
- What did you get right?
- What did you miss or skip?
- What would you do differently with more time?
```

---

## Notes for the Proctor

- Both agents receive this prompt identically — no changes, no additions.
- `meridian-demo-eval.md` is the primary comparison artifact.
- Elapsed time is a secondary signal. Quality of narration and test convention
  adherence are the primary metrics.
- If an agent fails to produce `meridian-demo-eval.md`, use its stdout output for
  evaluation. Note the failure in the proctor report.

---

Copyright 2026 TableStakes LLC. Licensed under the Apache License, Version 2.0.
