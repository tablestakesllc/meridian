<!-- meridian:pointer -->
## Meridian Session Bootstrap

Read `agent_docs/SESSION_INIT.md` in full and run the Session-Start Checklist defined there. That checklist is the single source of truth for session bootstrap.

Meridian (`agent_docs/`) is this project's only durable memory store; follow the memory-custody rule in `agent_docs/MEMORY.md` §0.

Never repeat a step from `SESSION_INIT.md` in this file.
<!-- /meridian:pointer -->

<!-- meridian:fill id="agent-pointer-notes" -->
Optional. This file is the source text for your agent's auto-load file: `CLAUDE.md` (Claude Code), `AGENTS.md` (Cursor, Windsurf and other AGENTS.md readers), `.github/copilot-instructions.md` (VS Code Copilot) or `.clinerules/meridian.md` (Cline). With Latitude, run `latitude-mcp --init --config-only --client <client>` and it does this for you. By hand: copy the block between the `meridian:pointer` markers, markers included, to the very top of that file (after any YAML front matter), so the agent reads it first. Leave existing content below it and review it with the user: move project knowledge into Meridian, keep only agent-specific settings (tool permissions, pre-approved commands), never steps from SESSION_INIT.md. Delete this marker when done.
<!-- /meridian:fill -->
