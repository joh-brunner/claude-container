# Codex inside Claude Code

The official plugin [`openai/codex-plugin-cc`](https://github.com/openai/codex-plugin-cc)
lets Claude Code delegate to, or get reviews from, your local Codex CLI. Usage counts
against your **ChatGPT/Codex** limits (or your OpenAI API key), not your Claude plan.

## Installation

This repo preconfigures the marketplace and plugin in `.claude/settings.json`:

```json
"extraKnownMarketplaces": {
  "openai-codex": { "source": { "source": "github", "repo": "openai/codex-plugin-cc" } }
},
"enabledPlugins": { "codex@openai-codex": true }
```

When you trust the folder, Claude Code offers to install it. To install manually instead:

```
/plugin marketplace add openai/codex-plugin-cc
/plugin install codex@openai-codex
/reload-plugins
/codex:setup
```

Codex itself is already installed in the container (`codex --version`). Log in with:

```bash
codex login --device-auth                              # ChatGPT account
printenv OPENAI_API_KEY | codex login --with-api-key   # or an API key
```

## Commands

| Command | What it does |
|---|---|
| `/codex:setup` | Checks that Codex is installed and logged in |
| `/codex:review` | Standard read-only Codex review of your current changes (`--base <ref>` for a branch; `--background` recommended for big diffs) |
| `/codex:adversarial-review` | Skeptical review that challenges design decisions |
| `/codex:rescue <task>` | Hands a task to Codex (`--background`, `--model`, `--effort`, `--resume`, `--fresh`) |
| `/codex:status`, `/codex:result`, `/codex:cancel` | Manage background Codex jobs |
| `/codex:transfer` | Moves the current Claude conversation into a Codex thread you can `codex resume` |

You can also just ask, for example: "Ask Codex for a second opinion on this function."

The plugin also offers a **Review Gate**, which stops Claude from finishing changes until Codex has reviewed them. See the plugin README to enable it.

## Model choice

Set in `~/.codex/config.toml` (inside the container):

| Model | Use for |
|---|---|
| `gpt-5.6-luna` | Cheap, fast checks |
| `gpt-5.6-terra` | Balanced everyday reviews |
| `gpt-5.6-sol` | Default here: thorough reviews and hard tasks |
| `gpt-6-astra` | Most capable; about 2.5x Sol's price; availability may depend on your plan and rollout |

Or per call: `/codex:rescue --model gpt-6-astra --effort high <task>`.

Cost note: GPT-5.6 prompts above 272K input tokens are billed at a higher rate for the
whole request. The template sets `model_auto_compact_token_limit = 260000` to stay below that.

## Safety settings

`~/.codex/config.toml` (from `.devcontainer/codex-config.toml`):

- `approval_policy = "untrusted"`: Codex asks before running commands it doesn't know are safe.
- `sandbox_mode = "workspace-write"` with `network_access = false`: Codex writes only
  in the workspace and has no network from its own sandbox.

Codex reads `AGENTS.md` for project rules. This repo's version mirrors `CLAUDE.md`.

Codex option names change between versions. If Codex warns about an unknown key,
check `codex --help` or the Codex docs and adjust the file.
