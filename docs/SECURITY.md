# Security model

No single control here is perfect, so the setup stacks independent layers. An
action has to get past all of them.

```
┌─ Layer 1: Dev container ─────────────────────────────────────────────┐
│  Only the repo is mounted from your host. Non-root user, no general   │
│  sudo. Global tools are root-owned (read-only). Memory and PID limits.│
│  ┌─ Layer 2: Firewall (iptables, default deny) ─────────────────────┐│
│  │  Outbound traffic only to allowed-domains.txt. IPv6 blocked.       ││
│  │  ┌─ Layer 3: Managed settings (/etc/claude-code, root-owned) ───┐ ││
│  │  │  Bypass mode off. Sandbox mandatory. No unsandboxed retries.  │ ││
│  │  │  Bash cannot read $HOME. Strict network allowlist.            │ ││
│  │  │  ┌─ Layer 4: Claude Code sandbox (bubblewrap) ─────────────┐ │ ││
│  │  │  │  Bash writes limited to the repo and session temp.      │ │ ││
│  │  │  │  Config files (.claude, .git/hooks, ...) write-protected.│ │ ││
│  │  │  │  ┌─ Layer 5: Permission rules + guard hook ───────────┐ │ │ ││
│  │  │  │  │  Ask: installs, downloads, outside reads, push, rm. │ │ │ ││
│  │  │  │  │  Deny: outside writes, sudo, pipe-to-shell,         │ │ │ ││
│  │  │  │  │  secrets, edits to the guard rails.                 │ │ │ ││
│  │  │  │  └─────────────────────────────────────────────────────┘ │ │ ││
│  │  │  └──────────────────────────────────────────────────────────┘ │ ││
│  │  └────────────────────────────────────────────────────────────────┘ ││
│  └────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────┘
```

## How each requirement is enforced

| Requirement | Enforced by |
|---|---|
| Ask before installing anything | Guard hook (detects around 40 package managers, downloaders, `git clone`, `docker`, `claude mcp` and `claude plugin`) plus `ask` permission rules. In auto or bypass-style modes the hook **denies** instead. Global installs are impossible anyway (root-owned `/usr/local`, no apt for the agent user). |
| No writes outside the repo | File tools: guard hook plus `Edit` deny rules. Shell: the OS sandbox (repo and session temp only), the guard hook (redirects, `cp`, `mv`, `tee`, `sed -i`, ...), and the container (host filesystem not mounted). |
| Reads outside the repo only with permission | File tools: guard hook asks. Shell: guard hook asks for outside paths it can see. In the container, the sandbox also denies Bash reads of `$HOME` outright (credentials live there). Secrets have explicit deny rules. |
| Guard rails can't be disabled by the agent | Hook and `Edit` deny rules on `.claude/`, `.devcontainer/`, and `.git/`. The sandbox's built-in protected paths. Managed settings are root-owned and override project settings. The firewall is root-owned. |

## What each layer protects against

- **Prompt injection** (malicious text in a README, issue, web page, or tool output):
  The agent can be tricked, but the tricked action still hits the sandbox, the firewall,
  and the prompts. Exfiltration needs an allowed domain, and there are few.
- **Malicious package install scripts:** installs require your approval. If approved,
  the script runs inside the sandbox and container, with no access to your host home directory.
- **Agent mistakes** (`rm -rf` in the wrong place): the host filesystem is not mounted,
  and `rm` always asks.
- **Credential theft:** host credentials are not in the container. The Claude login
  is in a volume that sandboxed Bash can't read. API-key environment variables are
  stripped from sandboxed commands.

## Known limitations (read these)

1. **The guard hook is heuristic.** It parses shell commands, but can't see inside
   `python -c "..."`, scripts, or deliberately obfuscated commands. The sandbox and
   container are the real boundaries; the hook provides clear prompts and early blocks.
2. **Allowed domains are exfiltration paths.** Keep `allowed-domains.txt` short.
   The firewall resolves domains to IPs at start, so CDN-hosted domains may share
   IPs with other sites.
3. **`enableWeakerNestedSandbox`** is on inside the container, because bubblewrap
   can't create a full sandbox in an unprivileged container. This weakens the inner
   sandbox, so the container is the primary boundary there.
4. **You can override everything.** Commands you type yourself (in a terminal, or with
   `!` in Claude Code) aren't subject to Claude's permission rules. Settings you add
   in `.claude/settings.local.json` can widen `allow` lists and excluded commands.
5. **MCP servers and plugins run with real access.** Only add ones you trust. Adding them
   via the CLI is gated by the hook, but installing through the `/plugin` UI is your
   own action.
6. **Auto mode** (default for new sessions on some plans since August 2026) replaces
   prompts with a classifier. This repo sets `defaultMode: "default"`. If you switch to
   auto mode anyway, the hook blocks installs and outside reads rather than silently allowing them.
7. **VS Code itself** has access to the container and can forward ports, credentials, and
   SSH agents. Use the host settings in the README to limit credential forwarding.

## Optional extra hardening

- Set `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` (in `devcontainer.json` → `containerEnv`)
  to strip credentials from **all** subprocesses and force shell-mode commands into
  the sandbox too.
- Pin `CLAUDE_CODE_VERSION` in `devcontainer.json` to known-good
  versions, and update deliberately. Auto-update is disabled in the container.
- Run a secret scanner (for example gitleaks) as a git pre-commit hook. You'd need
  to install it yourself in the Dockerfile.
- Use a separate Docker context or VM (for example Docker Desktop with enhanced
  container isolation) for untrusted repositories.
- For company code, confirm data-handling terms (training opt-out, retention, GDPR)
  with Anthropic before connecting real repositories.
