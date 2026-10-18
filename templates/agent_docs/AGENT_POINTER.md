<!-- meridian:pointer -->
## Meridian Session Bootstrap

Read `agent_docs/SESSION_INIT.md` in full and run the Session-Start Checklist defined there. That checklist is the single source of truth for session bootstrap.

Meridian (`agent_docs/`) is this project's only durable memory store; follow the memory-custody rule in `agent_docs/MEMORY.md` §0.

Never repeat a step from `SESSION_INIT.md` in this file.
<!-- /meridian:pointer -->

<!-- meridian:fill id="agent-pointer-notes" -->
Optional. This file is the source text for your agent's auto-load file (for example `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, `.cursor/rules/meridian.mdc`, `.clinerules/meridian.md` or `.windsurfrules`). Copy the block between the `meridian:pointer` markers, markers included, to the top of that file. Add agent-specific notes after the block (tool permissions, pre-approved commands), never steps from SESSION_INIT.md. Delete this marker when done.
<!-- /meridian:fill -->
