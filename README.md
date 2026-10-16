# safe-agent-workspace

A reusable dev container for running **Claude Code** in isolation from your computer.

All protection comes from the container. There are no Claude-specific rules, hooks,
settings, or instruction files: inside the container Claude behaves like stock Claude Code,
and the container decides what it can reach.

What you get:

- **An isolated container.** Only this project folder is shared with your computer.
  Claude runs as a normal user without root, and the installed tools are read-only.
- **A default-deny firewall.** Only the domains in `.devcontainer/allowed-domains.txt` are reachable.
- **Read-only protection for files that can run code on your computer:** `.devcontainer/`,
  `.vscode/`, `.git/hooks/`, `.git/config`, and `.git/modules/`. Claude can read them but not change them.
- **Scripts:** `check-setup.sh` verifies the container, and `new-project.sh` starts a new project from this template.

See [docs/SECURITY.md](docs/SECURITY.md) for what this protects against and what it doesn't.

---

## Setup (one time)

### 1. Install prerequisites on your computer

- **Docker Desktop** (or Docker Engine on Linux).
- **VS Code** with the **Dev Containers** extension (`ms-vscode-remote.remote-containers`).
- **Git** and **bash**. On Windows, use WSL or Git Bash. A setup script runs on your computer before each container start.
- A **Claude Pro/Max/Team** plan (or Anthropic API key).

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

Log in with your Claude account. The volume keeps the login across rebuilds.

### 5. Verify

```bash
bash scripts/check-setup.sh
```

Every line should show `[ok]`. For a live test, ask Claude:

> Write "hi" to .devcontainer/test.txt, then fetch https://example.com.

Both should fail: the first with `Read-only file system`, the second with a connection error.

---

## Workflow for a project

1. **Create the project** (on your host):
   ```bash
   bash scripts/new-project.sh ../my-project
   ```
   Or use "Use this template" on GitHub and clone the result. Each project gets its own
   container, volumes, and Claude login.

2. **Open it in the container:** `code ../my-project`, then **Reopen in Container**.
   Before the container starts, `.devcontainer/initialize.sh` runs on your host and creates
   `.git` and `.vscode` if they're missing, because the read-only mounts need them.

3. **Work with Claude** in the container terminal: `claude`.
   - By default Claude Code asks before running commands and editing files. That is
     Claude Code's normal behaviour, not something this repo adds.
   - Because the container is the boundary, you can choose to skip the prompts with
     `claude --dangerously-skip-permissions`. Claude can then do anything *inside the container*
     without asking. Read [docs/SECURITY.md](docs/SECURITY.md) first.
   - If you want Claude to follow project conventions, you can add a `CLAUDE.md`. It is
     guidance for Claude, not a security control.

4. **Install dependencies inside the container**, into the project (`npm install`, a `.venv`).
   npm and PyPI are reachable. System tools and other languages go in the `Dockerfile`; edit it on your host and rebuild.

5. **Commit inside the container, push from your host.** Claude can commit. Before pushing,
   review what's new on your host:
   ```bash
   git log -p origin/main..
   ```
   This review is your checkpoint: anything Claude wrote leaves the container when you push it,
   or when you run it on your host.

6. **Change protected files on your host**, outside the container: `.devcontainer/`, `.vscode/`,
   git config (`git remote add`, `git push -u`, ...). Then rebuild or restart the container.

## Customizing (edit on your host)

| Want to... | Edit | Then |
|---|---|---|
| Reach another domain | `.devcontainer/allowed-domains.txt` | Rebuild container |
| Add a language toolchain (Go, Rust, ...) | `.devcontainer/Dockerfile` | Rebuild container |
| Protect another path | Add a `readonly` bind mount in `.devcontainer/devcontainer.json`, and create the path in `.devcontainer/initialize.sh` | Rebuild container |
| Reach services on your computer (e.g. a database) | Set `ALLOW_HOST_NETWORK` to `true` in `devcontainer.json` | Rebuild container |

## Troubleshooting

- **The container fails to start with "bind source path does not exist".** `initialize.sh` didn't run on
  your host (for example, Windows without bash). Run `git init` and `mkdir .vscode` in the project
  folder yourself, then try again.
- **Git in the container says it could not lock `.git/config`.** Expected: the config is read-only.
  Run that git command on your host.
- **Git config changes on the host don't show up in the container.** `.git/config` is mounted as a
  single file, and git replaces the file when it writes it. Restart the container.
- **A package install fails with a network error.** The registry isn't in `allowed-domains.txt`. Add it and rebuild.
- **The firewall fails on start.** A domain may have changed its IPs or be unreachable.
  Rebuild, or check your network or VPN.
