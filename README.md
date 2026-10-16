# safe-agent-workspace

A reusable, locked-down workspace for agentic coding with **Claude Code** and
**OpenAI Codex** (via the official Codex plugin for Claude Code).

What you get:

- **A sandbox container** with a default-deny firewall. Only an allowlist of domains is reachable.
- **Claude Code's OS-level sandbox** inside it. Shell commands can only write to the repo.
- **Permission rules and a guard hook** that:
  - ask before any install (packages, tools, software, plugins, MCP servers, images, clones, downloads)
  - block writes outside the repo
  - ask before reads outside the repo
  - protect the guard rails themselves from being edited by Claude
- **Codex plugin preconfigured.** Claude Code offers to install it when you trust the folder.
- **Scripts**: `check-setup.sh` verifies everything, `test-guard.py` tests the hook,
  and `new-project.sh` starts a new project from this template.

See [docs/SECURITY.md](docs/SECURITY.md) for the security model and its limits,
and [docs/CODEX.md](docs/CODEX.md) for Codex details.

---

## Setup (one time)

### 1. Install prerequisites on your computer

- **Docker Desktop** (or Docker Engine on Linux).
- **VS Code** with the **Dev Containers** extension (`ms-vscode-remote.remote-containers`).
- **Git.**
- A **Claude Pro/Max/Team** plan (or Anthropic API key) and a **ChatGPT** plan
  (Free works for the Codex plugin; paid plans get more usage) or OpenAI API key.

Recommended VS Code *user* settings on the host, so your host credentials are not forwarded into the container:

```json
"dev.containers.copyGitConfig": true,
"dev.containers.gitCredentialHelperConfigLocation": "none"
```

With these settings, `git push` from inside the container will not work; push from your host terminal instead. That is intended.

### 2. Put this repo on your machine

```bash
git clone <your-copy-of-this-repo> safe-agent-workspace
cd safe-agent-workspace
```

Tip: on GitHub, mark the repository as a **Template repository**. Each new project can then start from "Use this template".

### 3. Open it in the container

1. Run `code .`
2. When prompted, choose **Reopen in Container**. You can also open the command palette and run
   **Dev Containers: Reopen in Container**.
3. The first build takes a few minutes. On every start, the firewall script runs and
   prints `[firewall] OK` lines. If it fails, the container start fails. That is deliberate.

### 4. Log in (inside the container terminal)

```bash
claude
```

- Log in with your Claude account. The volume keeps the login across rebuilds.
- When asked, **trust the folder**.
- Accept the prompt to install the **Codex plugin** from the `openai-codex` marketplace.
  - If no prompt appears, install it manually inside Claude Code:
    ```
    /plugin marketplace add openai/codex-plugin-cc
    /plugin install codex@openai-codex
    /reload-plugins
    ```

In a second terminal:

```bash
codex login --device-auth
```

If device login isn't available in your Codex version, use an API key instead:

```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```

Then, back in Claude Code:

```
/codex:setup
```

### 5. Verify

```bash
bash scripts/check-setup.sh
```

Every line should show `[ok]`. Inside Claude Code, also run:

- `/sandbox`: the Config tab shows the resolved sandbox and whether it is active.
- `/permissions`: shows the allow, ask, and deny rules.
- `/hooks`: shows the guard hook.

Then run a quick live test by asking Claude:

> Install the npm package left-pad, then write "hi" to ~/test.txt, then read /etc/hostname.

You should see a **prompt** for the install, a **block** for the write, and a
**prompt** for the read.

---

## Daily use

| Task | How |
|---|---|
| Get a Codex review | `/codex:review` or `/codex:adversarial-review` |
| Hand work to Codex | `/codex:rescue <task>`, with `/codex:status`, `/codex:result`, and `/codex:cancel` to manage it |
| Continue in Codex | `/codex:transfer` |

**Stay in the default (manual) permission mode.** The guard hook **denies**
installs and outside reads in auto mode, because nobody would be asked.
Bypass mode is disabled entirely.

## Starting a new project from this template

On your host:

```bash
bash scripts/new-project.sh ../my-next-project
code ../my-next-project   # then "Reopen in Container"
```

Each project gets its own container, volumes, and Claude/Codex login.
The `${devcontainerId}` in the volume names keeps them separate.

Then edit the "Project notes" section of `CLAUDE.md` with the stack and commands.

## Customizing (do this yourself; Claude is blocked from editing these files)

| Want to... | Edit | Then |
|---|---|---|
| Reach another domain | `.devcontainer/allowed-domains.txt`, plus `sandbox.network.allowedDomains` in `.claude/settings.json` if Bash needs it | Rebuild container |
| Allow a harmless command without prompts | `permissions.allow` in `.claude/settings.local.json` (personal) or `settings.json` (shared) | Restart `claude` |
| Fewer Bash prompts | Set `"autoAllowBashIfSandboxed": true` in `.claude/settings.local.json`. Sandboxed commands then run without prompts, while installs, outside reads, and blocked writes still get stopped by the hook | Restart `claude` |
| Add a language toolchain (Go, Rust, ...) | Add it to the `Dockerfile` | Rebuild container |
| Change the Codex model | `~/.codex/config.toml` inside the container | Next Codex call |

## Running without the container (host mode)

Everything in `.claude/` also works when you run `claude` directly on macOS, Linux, or WSL2.
The sandbox then uses Seatbelt (macOS) or bubblewrap (Linux; install `bubblewrap` and `socat`).
You lose the firewall, the read-only toolchain, the locked managed settings, and the
home-directory read fence, so **the container is the recommended mode**.

## Troubleshooting

- **Claude refuses to start with a sandbox error inside the container.** Bubblewrap could not
  start in your Docker setup. Set `"SANDBOX_FAIL_CLOSED": "false"` in
  `devcontainer.json` build args and rebuild. The container and firewall remain the boundary.
  Run `/sandbox` for details.
- **`/codex:*` commands fail with sandbox or permission errors.** The Codex plugin runs your
  local `codex` CLI. `codex *` is already excluded from Claude's sandbox. If the plugin
  launches it differently, the error shows the command. Add a matching pattern to
  `sandbox.excludedCommands` in `.claude/settings.local.json`. Codex is still bounded by
  the container, the firewall, and its own `workspace-write` sandbox.
- **A package install was approved but fails with a network error.** Add the registry
  to both allowlists (see Customizing) and rebuild.
- **The firewall fails on start.** A domain may have changed its IPs or be unreachable.
  Rebuild, or check your network or VPN.
- **"Yes, and don't ask again" doesn't save.** Run `claude doctor` and follow its advice on
  stale sandbox mask files.
