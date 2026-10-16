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

The container setup lives **inside each project**: VS Code looks for `.devcontainer/` at the top of
the folder you open, and the container can only see that folder. So you don't put projects into
this repo; you copy this repo's `.devcontainer/` into each project.

Git inside the container is **local only**: commit, branch, diff, log, merge, and so on all work,
but GitHub is not reachable and no credentials are in the container. Clone, pull, and push
happen on your host.

### 1. Clone the project on your host, next to this repo (not inside it)

```bash
cd ~/Claude
git clone git@github.com:<you>/example_project.git
```

```
~/Claude/
├── AI_SETUP/            ← this template (stays as it is)
└── example_project/     ← your project, opened in its own container
```

Cloning on your host is safe: git never copies hooks from a remote.

For a brand-new project instead, run `bash scripts/new-project.sh ../my-project` from this repo
(it copies everything and runs `git init`), then skip to step 3.

### 2. Copy the container setup into the project

```bash
cd ~/Claude/example_project
cp -r ../AI_SETUP/.devcontainer .
mkdir -p scripts && cp ../AI_SETUP/scripts/check-setup.sh scripts/
echo ".cache/" >> .gitignore
```

- `.cache/` holds the npm and pip caches, which the container keeps inside the project so they survive
  rebuilds. If you don't want to change the project's `.gitignore`, put the line in `.git/info/exclude`
  instead (same effect, but stays local).
- If the project **already has a `.devcontainer/`**, don't overwrite it. That container wouldn't have
  these protections; merge the two by hand.
- Commit `.devcontainer/` if you want future clones to work without this step.

### 3. Open it in the container

1. `code ~/Claude/example_project`
2. Click **Reopen in Container** in the popup (or `Ctrl+Shift+P` → **Dev Containers: Reopen in Container**).
3. The first start takes a few minutes (click *Show Log* to watch):

   | Step | Runs on | What it does |
   |---|---|---|
   | `initialize.sh` | your host | Creates `.git`, `.vscode/`, and `.git/modules/` if missing (the read-only mounts need them) |
   | Image build | Docker | Installs Claude Code, git, Python, ... (first time, or after changes) |
   | `post-create.sh` | container | Creates the cache folders (once per container) |
   | `init-firewall.sh` | container | Turns on the firewall (every start; the start fails if this fails) |

### 4. Check that you are inside the container

**In a window opened normally, Claude runs on your host without any limits.** Before starting Claude, check:

- The bottom-left corner of the window shows **"Dev Container: safe-agent-workspace"**.
- A new terminal (*Terminal → New Terminal*) shows the prompt **`node@agent-container:/workspace$`**.
  Inside the container, your project is at `/workspace`.

The first time, also run:

```bash
bash scripts/check-setup.sh      # every line should show [ok]
claude                           # log in: open the link in your browser, paste the code back
```

The login is stored in a Docker volume, so it survives restarts and rebuilds. Each project has its own
container and its own login.

### 5. Work with Claude

- Run `claude` in the container terminal, or use the Claude Code panel (see
  [Using the VS Code extension](#using-the-vs-code-extension)).
- By default Claude Code asks before running commands and editing files. That is Claude Code's normal
  behaviour, not something this repo adds. Because the container is the boundary, you can skip the prompts
  with `claude --dangerously-skip-permissions`; Claude can then do anything *inside the container*
  without asking. Read [docs/SECURITY.md](docs/SECURITY.md) first.
- If you want Claude to follow project conventions, add a `CLAUDE.md`. It is guidance for Claude,
  not a security control.
- Install dependencies inside the container, into the project (`npm install`, a `.venv`). npm and PyPI
  are reachable. System tools and other languages go in the `Dockerfile`: edit it on your host and rebuild.
- Commit in the container as often as you like.

### 6. Review and push from your host

Use a terminal on your host, not the VS Code terminal (that one is inside the container):

```bash
cd ~/Claude/example_project
git log -p origin/main..      # read everything that was committed in the container
git push
```

This review is your checkpoint: code from the container reaches your host or GitHub only when you push
or run it there. Look closely at `.github/workflows/`, which run on GitHub with your repository's secrets.
`git pull` also happens on your host; the container sees the new files immediately.

### 7. Leave, and come back

- Close the window, or click the bottom-left corner → **Reopen Folder Locally**. The container stops
  when the window closes.
- Next time, `code ~/Claude/example_project` usually reopens straight into the container. If not,
  use **Reopen in Container** again. You are still logged in.

### Changing protected files

`.devcontainer/`, `.vscode/`, and git config (`git remote add`, `git push -u`, ...) are read-only in the
container. Change them on your host, then rebuild (`.devcontainer/`) or restart the container
(git config, so the container sees the new file).

## Using the VS Code extension

The Claude Code extension also runs inside the container. In a container window, VS Code shows its
interface on your host, but runs extensions that work with files and commands in the container. So the
Claude panel's process, and every command it runs, are inside the container, behind the firewall. The
extension is preinstalled through `devcontainer.json` and shares the terminal CLI's login.

Things to know:

- **Check where it is installed.** In the Extensions view (`Ctrl+Shift+X`), Claude Code should appear under
  **"Dev Container: safe-agent-workspace – Installed"**, not under "Local – Installed". If the extension is
  also installed in your normal VS Code and you open the project *without* the container, it runs on your
  host with no limits.
- **Quick test:** ask the panel to run `hostname` and `curl -m 5 https://example.com`. It should answer
  `agent-container`, and the curl should fail.
- **The extension may not install through the firewall.** VS Code downloads its server and extensions from
  Microsoft, and those domains are not in `allowed-domains.txt`. If the install fails, add
  `marketplace.visualstudio.com`, `vscode.blob.core.windows.net`, and `update.code.visualstudio.com`, then rebuild.
- **It brings its own copy of Claude Code**, stored in a folder the container user can write to. The
  "tools are read-only" and "version pinned" guarantees cover only the terminal `claude`. Everything still
  runs inside the container.

## Running on a remote server (SSH)

The same setup works on a server you connect to with VS Code's **Remote-SSH** extension. Docker,
the firewall, and the read-only mounts then all run on the server.

| Machine | Needs |
|---|---|
| Your laptop | VS Code with the **Remote-SSH** and **Dev Containers** extensions |
| The server | Docker (your user in the `docker` group), git, and bash. VS Code installs its own server part when you connect. |

Everywhere this README says "your host", read **the server**: clone the project there, `initialize.sh` runs
there, the read-only mounts protect the server, and you review and push from a terminal on the server.

To open a project:

1. `Ctrl+Shift+P` → **Remote-SSH: Connect to Host** → your server.
2. **File → Open Folder** → the project on the server.
3. **Reopen in Container**, then check the bottom-left corner as in step 4.

Security differences:

- **Turn off SSH agent forwarding.** With `ForwardAgent yes`, Dev Containers passes your laptop's SSH agent
  into the container, and Claude could *use* your SSH keys (push to all your repos, log in to other servers).
  Set `ForwardAgent no` for the server in your laptop's `~/.ssh/config`, and check that `echo $SSH_AUTH_SOCK`
  prints nothing in the container terminal.
- **Keep `ALLOW_HOST_NETWORK` set to `false`.** On a server it would open the server's whole local network,
  which may include internal company or university services.
- **Shared servers:** anyone in the server's `docker` group effectively has root there, and can read every
  container's files, including your project and your Claude login.

Compatibility: the firewall needs `NET_ADMIN` and `iptables` inside the container. With **rootless Docker or
Podman** (a Docker alternative common on Red Hat-based servers), this may fail. The container then refuses
to start, so it fails safely. If that happens, ask the admin about regular (rootful) Docker. To see what a
server has, run `docker --version` and `podman --version`.

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
