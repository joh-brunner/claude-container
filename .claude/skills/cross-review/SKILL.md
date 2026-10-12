---
name: cross-review
description: Two-model review of the current changes. Runs the code-reviewer and security-auditor subagents (Claude), then gets an independent review from Codex (GPT) via the Codex plugin, and merges the findings. Use when the user asks for a thorough review, a second opinion, or before committing significant changes.
---

# Cross-review (Claude + Codex)

1. Run `git diff --stat` to confirm there are changes to review. If there are none, say so and stop.
2. Launch the `code-reviewer` and `security-auditor` subagents in parallel on the current diff.
3. Get an independent review from Codex using the Codex plugin (its review command or
   delegation). If the plugin is not available or not logged in, tell the user to run
   `/codex:setup`, or to run `/codex:review --background` themselves, and continue
   with the Claude findings only.
4. Merge the results into one report:
   - **Agreed issues** (found by both): highest confidence, list first
   - **Claude-only** and **Codex-only** findings, each with your assessment of whether it is valid
   - A short, prioritised fix list
5. Do not apply fixes unless the user asks.
