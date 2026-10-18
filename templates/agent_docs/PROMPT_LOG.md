<!-- meridian:fill id="prompt-log-title" -->
Write the H1 title with the project name: `# <Project Name> — Prompt Log`.
<!-- /meridian:fill -->

> **Format:** Append-only — sessions added at the bottom, oldest at top.
> **Session header:** `## Session: YYYY-MM-DD HH:MM PDT — <git config user.name>`
> Run `git config user.name` at session start to get the name token.
> **Reading:** Run `grep -n "^## Session:" agent_docs/PROMPT_LOG.md | tail -1` to get the most recent session line number, then read from there to end of file.
> **Timezone:** All times in US Pacific (PDT/PST).

---
