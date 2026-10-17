# Security model

This workspace has **one security boundary: the dev container**, together with its firewall.
There are no Claude-specific controls (no permission rules, hooks, command isolation, or instruction files).
Everything below is enforced by Docker and the Linux kernel, so it holds no matter what
Claude, a package, or a prompt injection tries.

```
┌─ Your computer ──────────────────────────────────────────────────────┐
│                                                                        │
│  ┌─ Dev container ────────────────────────────────────────────────┐   │
│  │  Non-root user, no general sudo. Tools root-owned (read-only).  │   │
│  │  Memory and PID limits. Claude can do anything in here.          │   │
│  │                                                                   │   │
│  │  /workspace = your project folder (shared with your computer)    │   │
│  │    read-write: everything else                                    │   │
│  │    read-only:  .devcontainer/  .vscode/  .git/hooks/              │   │
│  │                .git/config     .git/modules/                      │   │
│  └───────────────────────────┬───────────────────────────────────┘   │
│                              │  Firewall (iptables, default deny)     │
└──────────────────────────────┼─────────────────────────────────────────┘
                               ▼  only domains in allowed-domains.txt
```

## What is enforced

| Protection | How |
|---|---|
| Your computer's files are out of reach | Only the project folder is mounted. Everything else Claude sees is the container's own file system. |
| Your credentials are out of reach | SSH keys, git credentials, and cloud logins stay on your computer (see the VS Code settings in the README). Exception: VS Code forwards a running SSH agent (see below). |
| Network limited to an allowlist | `init-firewall.sh` sets `iptables` default-deny and allows only the IPs of the domains in `allowed-domains.txt`. IPv6 is blocked. The agent user can't change the rules. |
| No system-wide changes | No general `sudo`; global tools in `/usr/local` are root-owned. |
| No code execution on your computer through config files | These paths are mounted read-only, because files there can run code on your computer: |

The read-only paths:

| Path | Why it is dangerous |
|---|---|
| `.git/hooks/` | Hook scripts run on your computer when you commit, push, or check out from your host. |
| `.git/config` | `core.hooksPath` can point hooks somewhere writable; `core.fsmonitor` runs a command on every `git status`. |
| `.git/modules/` | Submodules' own configs and hooks, with the same risks. |
| `.devcontainer/` | Defines the container and firewall. Changes take effect on your next rebuild, and `initialize.sh` runs on your computer. |
| `.vscode/` | Workspace settings and tasks can run commands when VS Code opens the folder. |

## What it protects against

- **Agent mistakes** (`rm -rf` in the wrong place): limited to the project folder. Your other files aren't mounted.
- **Malicious packages:** install scripts run inside the container, without access to your computer or credentials.
- **Prompt injection** (malicious text in a file, web page, or tool output): a tricked Claude is still inside
  the container and can only send data to allowed domains.

## Accepted risks (read these)

1. **Inside the container, Claude can do anything.** It can read every file in the project,
   including `.env` and other secrets, change or delete files outside the read-only paths,
   and install packages from PyPI. Commit often: uncommitted work can be lost.
2. **Data can leave through allowed domains.** The firewall can't tell Claude Code apart from
   the commands it runs. A malicious command could send project files to `api.anthropic.com`
   using someone else's API key, or publish them to PyPI. DNS (port 53) is also open,
   which allows slow leaks through DNS lookups.
3. **Your Claude login can be stolen.** It is stored in the container (`/home/dev/.claude`),
   so any command can read it and send it out through an allowed domain. If you suspect
   this happened, log out of all sessions in your Claude account settings.
4. **Code you run on your computer from the project.** The container only protects your computer
   while the code stays inside it. Anything Claude wrote runs on your computer if you run it there:
   Python scripts, `Makefile`s, tests, `.envrc` (direnv), and so on. CI workflows (`.github/workflows/`)
   run on GitHub with your repository's secrets when you push. Review changes before you run or push them.
5. **The firewall works on IP addresses.** Domains are resolved once, at container start. Other
   sites that share those IPs (for example on the same CDN) are reachable too.
6. **VS Code** has access to the container and can forward ports, credentials, and SSH agents.
   Use the host settings in the README to limit credential forwarding. A running SSH agent on your computer
   is forwarded with no setting to disable it: programs in the container can then use (not copy) your SSH
   keys. The firewall blocks SSH connections, and the start log warns about it. Start VS Code with
   `env -u SSH_AUTH_SOCK code` to avoid it.
7. **MCP servers and plugins** you add run inside the container with the same access as Claude.

## Optional extra hardening

- **Limit DNS** to Docker's resolver (`127.0.0.11`) in `init-firewall.sh`, to close DNS leaks.
- **Remove PyPI** from `allowed-domains.txt` if you don't install packages in the container.
  Put dependencies in the `Dockerfile` instead; the image build is not firewalled.
- **Make more paths read-only**, for example `.github/` (add a `readonly` bind mount in `devcontainer.json` and create the path in `initialize.sh`).
- **Pin `CLAUDE_CODE_VERSION`** in `devcontainer.json` and update deliberately. Auto-update is disabled.
- **Use a separate Docker context or VM** (for example Docker Desktop with enhanced container
  isolation) for untrusted repositories.
- For company code, confirm data-handling terms (training opt-out, retention, GDPR)
  with Anthropic before connecting real repositories.
