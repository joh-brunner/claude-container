# Claude container

> [!WARNING]
> Please test this setup locally first, if it works well we can ask IT for a similar solution on the servers! 

A dev container for running **Claude Code** projects with **VS Code** isolated from your computer.
There are no Claude-specific controls used (no permission rules, hooks, command isolation, or instruction files).

> **In short:** this repo is just a `.devcontainer/` folder. Copy it into the top level of a project,
> open the project in VS Code, choose **Reopen in Container**, and work with the **Claude Code extension**
> (or `claude` in the terminal). Claude then runs inside the container, not on your computer.

```
your_project/
├── .devcontainer/     ← copied from this repo: the only thing a project needs
├── pyproject.toml     ← optional (Python projects): dependencies installed automatically with uv
└── ...your project folders and files...
```

Nothing needs to be built beforehand; VS Code builds the container the first time you open the project.
Python 3.12 and uv are preinstalled for Python projects. They are optional: other projects simply don't use them.
**You never have to open this repo itself in a container.**

**What the container enforces:**

```
┌─ Your computer ────────────────────────────────────────┐
│                                                        │
│  ┌─ Container ──────────────────────────────────────┐  │
│  │  Claude Code, runs without root                  │  │
│  │  optional: Python 3.12, uv                       │  │
│  │                                                  │  │
│  │  /workspace = your project folder                │  │
│  │    (the only folder shared with your computer)   │  │
│  │    read-only: .devcontainer/ .vscode/ .git/      │  │
│  └─────────────────────────┬────────────────────────┘  │
│                            │ firewall                  │
└────────────────────────────┼───────────────────────────┘
                             ▼ only the Claude API (and PyPI, for Python projects)
```

See [SECURITY_MODEL.md](SECURITY_MODEL.md) for what this protects against and what it doesn't.

---

## One-time setup (outside the container)

1. **Install** Docker (e.g. [through apt](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)), VS Code with the **Dev Containers** extension, and bash (Windows: WSL).
   Git is optional but recommended (see [Good to know](#good-to-know)). 
   **You need a Claude Pro/Max/Team plan or API key**.

2. **Linux (Docker Engine):** add your user to the `docker` group, then **restart**.
   Otherwise opening the container fails with `permission denied ... docker.sock`.

   ```bash
   sudo usermod -aG docker $USER
   ```

3. **VS Code user settings** (`Ctrl+Shift+P` → *Preferences: Open User Settings (JSON)*), so your GitHub
   login is not forwarded into the container:

   ```json
   "dev.containers.copyGitConfig": true,
   "dev.containers.gitCredentialHelperConfigLocation": "none"
   ```

4. **Clone this repo for the `.devcontainer/`**, e.g. to `~/Claude/AI_SETUP`.

## For each new project (first time, outside the container)

1. **Copy `.devcontainer/` into your project on top-level.** 
```
your_project/
├── .devcontainer/     ← copied from this repo: the only thing a project needs
├── pyproject.toml     ← optional (Python projects): dependencies installed automatically with uv
└── ...your project folders and files...
```

## Every time (inside the container, except steps 1 and 4)

1. **Open the project folder itself** in VS Code (`code ~/Claude/test-project`) and click
   **Reopen in Container**. The first start may take a few minutes.

2. **Check that you are inside** before starting Claude.
   - Bottom-left corner: **"Dev Container: safe-agent-workspace"**
   - Terminal prompt: **`dev@agent-container:/workspace$`**

3. **Work with Claude** in the Claude Code panel of the VS extension or with `claude` in the terminal.
   - *Optional, Python projects:* add packages with `uv add`. Projects with a `pyproject.toml` get `.venv/`
     installed on every start.
   - **Use git locally inside the container** as often as you like: `git status`, `git diff`, `git add`,
     `git commit`, branches, and so on all work.

4. **Push from a terminal on your computer** (outside the container, not the VS Code terminal).
   This is your checkpoint: nothing leaves the container until you push or run it on your computer.

   ```bash
   cd ~/Claude/test-project
   git log -p origin/main..   # review what was committed in the container
   git push
   ```

---

## Good to know

- **Changing protected files:** edit `.devcontainer/`, `.vscode/`, or git config (e.g. `git remote add`)
  on your computer, then rebuild or restart the container.
- **Customizing:** add domains in `allowed-domains.txt`, tools (or, for Python projects, another Python version) in the `Dockerfile`,
  then run **Dev Containers: Rebuild Container**. Projects have their own copy of `.devcontainer/`;
  copy it again to get updates from this repo.
- **Without git on your computer:** the container creates the repository itself, and all local git
  (commit, branch, diff, log) works inside it. Cloning, pushing, adding a remote, and reviewing on your
  computer don't. Set your name inside the container with `git config --global user.name/user.email`.
- **The `.git/` folder appears even if you never use git.** It must exist so it can be mounted read-only;
  otherwise Claude could create a repository with hooks that would run on your computer.
- **SSH agent:** if your desktop runs an SSH agent, VS Code forwards it into the container, and there is no
  setting to turn that off. The start log then shows `[warn] SSH agent forwarded`. Programs in the container
  could ask the agent to *use* your keys (not copy them); the firewall blocks SSH connections, which limits
  this. To avoid it, close all VS Code windows and start it with `env -u SSH_AUTH_SOCK code <project>`.
- **VS Code extension:** it runs inside the container. In the Extensions view it should be listed under
  *"Dev Container: safe-agent-workspace – Installed"*. Each project has its own container and login.

## Troubleshooting

- **The start fails with "setup check failed":** the log shows which check failed. A forwarded git
  credential helper means the VS Code settings above are missing.
- **`permission denied` on the Docker socket:** you're not in the `docker` group, or haven't logged out and back in.
- **"Bind source path does not exist":** `initialize.sh` didn't run on your computer (e.g. no bash).
  Create `.git/` and `.vscode/` in the project yourself.
- **Git can't lock `.git/config`:** expected, it's read-only. Run that command on your computer.
- **A download or package install fails with a network error:** the domain isn't in `allowed-domains.txt`.
  If the VS Code extension won't install, add `marketplace.visualstudio.com`,
  `vscode.blob.core.windows.net`, and `update.code.visualstudio.com`.
- **The firewall fails on start:** a domain is unreachable or changed IPs. Check your network or VPN and rebuild.
