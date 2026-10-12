# Project instructions for Claude

This repository is a sandboxed agent workspace. Guard rails are enforced by a dev
container, the Claude Code sandbox, permission rules, and a PreToolUse hook
(`.claude/hooks/guard.py`). Work with them, never around them.

## Hard rules
- **Never install anything without the user's explicit approval.** This includes
  packages (npm, pip, uv, cargo, go, ...), system tools, CLIs, plugins, MCP servers,
  container images, and cloned repositories. Before an install, state what, why,
  and the exact command, then wait.
- Prefer project-local installs (`npm install` in the repo, a `.venv`) over global ones.
- **Only write inside this repository.** Never write to `$HOME`, `/tmp`, or system paths.
- Reading outside the repository requires the user's permission; avoid it unless needed.
- Never modify `.claude/`, `.devcontainer/`, `.git/` internals, or `.mcp.json`.
  If a change there is needed, describe it and let the user make it.
- Never read or print secrets (`.env`, keys, tokens, credential files).
- If a guard blocks an action, do not try alternative commands to achieve the same
  effect. Explain what was blocked and ask the user.

## Workflow
- Non-trivial tasks: use the `planner` subagent first and show the plan.
- Implement in small steps (`implementer`), add tests (`test-engineer`).
- Before committing significant changes, run the `cross-review` skill
  (Claude reviewers + Codex review via the Codex plugin).
- Use `debugger` for failing tests before guessing at fixes.
- Keep commits small with clear messages. Never push; the user pushes.

## Project notes
<!-- Add stack, commands, and conventions for the current project here. -->
- Source code lives in `src/` (adjust as needed).
- Python: use a virtual environment in `.venv` (`python3 -m venv .venv`).
