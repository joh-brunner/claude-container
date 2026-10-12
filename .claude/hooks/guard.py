#!/usr/bin/env python3
"""
guard.py - PreToolUse hook for Claude Code.

Policy (defense in depth; the OS sandbox and the dev container are the hard
boundaries, this hook adds intent-level checks with clear messages):

  1. Installing anything (packages, tools, software, plugins, MCP servers,
     images, cloned repos, downloads) -> ASK. In non-interactive / auto modes
     (auto, bypassPermissions, dontAsk) -> DENY, because nobody would be asked.
  2. Writing outside the repository (file tools or shell) -> DENY.
  3. Reading outside the repository -> ASK (DENY in non-interactive modes).
  4. Modifying the guard rails themselves (.claude/, .devcontainer/, .git
     internals, .mcp.json) -> DENY. Edit those files yourself.
  5. Privilege escalation and pipe-to-shell -> DENY.

Anything not matched falls through to Claude Code's normal permission flow.

The shell analysis is heuristic. It cannot see inside `python -c`, `node -e`,
scripts, or obfuscated commands. That is what the sandbox and container are for.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

NON_INTERACTIVE_MODES = {"auto", "bypassPermissions", "dontAsk"}

# Paths outside the repo that are always fine to touch.
SAFE_OUTSIDE_PREFIXES = (
    "/dev/null",
    "/dev/stdout",
    "/dev/stderr",
    "/dev/stdin",
    "/dev/tty",
    "/dev/fd/",
)

# Repo-relative paths Claude must never modify (edit these yourself).
PROTECTED_REPO_PATHS = (
    ".claude",
    ".devcontainer",
    ".mcp.json",
    ".git/hooks",
    ".git/config",
    ".gitconfig",
    ".vscode",
)

CONTROL_OPERATORS = {";", "&&", "||", "|", "&", "|&", "(", ")", "\n", "{", "}", "`"}
REDIRECT_OPERATORS = {">", ">>", ">|", "&>", "&>>", "<>"}
WRAPPER_COMMANDS = {"env", "time", "nice", "nohup", "command", "exec", "builtin", "stdbuf", "timeout", "xargs"}
PRIVILEGE_COMMANDS = {"sudo", "su", "doas", "pkexec", "runuser", "chroot", "nsenter", "unshare"}
SHELL_INTERPRETERS = {"sh", "bash", "zsh", "dash", "ksh", "fish", "python", "python3", "node", "perl", "ruby", "php"}
WRITE_COMMANDS = {
    "cp", "mv", "rm", "rmdir", "mkdir", "touch", "tee", "ln", "install", "rsync",
    "chmod", "chown", "chgrp", "truncate", "dd", "shred", "unlink", "scp", "patch",
    "tar", "unzip", "gunzip", "7z", "curl", "wget", "git",
}


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #
def emit(decision: str, reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": f"[guard] {reason}",
        }
    }))
    sys.exit(0)


def ask_or_deny(mode: str, reason: str) -> None:
    if mode in NON_INTERACTIVE_MODES:
        emit("deny", f"{reason} Blocked because permission mode '{mode}' would not ask you. "
                     "Switch to the default (manual) mode to approve this.")
    emit("ask", reason)


# --------------------------------------------------------------------------- #
# Path helpers
# --------------------------------------------------------------------------- #
def resolve(path: str, cwd: str) -> str:
    path = path.strip().strip("'\"")
    path = re.sub(r"^\$\{?HOME\}?", os.path.expanduser("~"), path)
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(cwd, path)
    return os.path.realpath(path)


def is_inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def is_safe_outside(path: str) -> bool:
    return any(path == p.rstrip("/") or path.startswith(p) for p in SAFE_OUTSIDE_PREFIXES)


def is_protected(path: str, root: str) -> bool:
    if not is_inside(path, root):
        return False
    rel = os.path.relpath(path, root)
    return any(rel == p or rel.startswith(p + os.sep) for p in PROTECTED_REPO_PATHS)


def looks_like_path(token: str) -> bool:
    if not token or token.startswith("-") and "=" not in token:
        return False
    if "://" in token:  # URLs are handled by install/network rules
        return False
    return bool(re.match(r"^(/|~|\.\.(/|$)|\$\{?HOME\}?)", token))


def path_candidates(token: str) -> list[str]:
    """Extract path-like pieces from a token, including --flag=/path and VAR=/path."""
    out = []
    if looks_like_path(token):
        out.append(token)
    if "=" in token:
        rhs = token.split("=", 1)[1]
        if looks_like_path(rhs):
            out.append(rhs)
    return out


# --------------------------------------------------------------------------- #
# Shell parsing
# --------------------------------------------------------------------------- #
def tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command.replace("$(", " ( ").replace("`", " ` "),
                        posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        # Unbalanced quotes etc. Fall back to a crude split.
        return command.split()


def split_segments(tokens: list[str]) -> list[dict]:
    """Split into simple commands, remembering which operator preceded each."""
    segments, current, prev_op = [], [], None
    for tok in tokens:
        if tok in CONTROL_OPERATORS:
            if current:
                segments.append({"tokens": current, "prev_op": prev_op})
            current, prev_op = [], tok
        else:
            current.append(tok)
    if current:
        segments.append({"tokens": current, "prev_op": prev_op})
    return segments


def command_and_args(tokens: list[str]) -> tuple[str, list[str]]:
    """Skip env assignments and wrappers; return (basename(cmd), args)."""
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok):
            i += 1
            continue
        base = os.path.basename(tok)
        if base in WRAPPER_COMMANDS:
            i += 1
            # skip wrapper options such as `timeout 30` or `env -i`
            while i < len(tokens) and (tokens[i].startswith("-") or tokens[i].isdigit()):
                i += 1
            continue
        return base, tokens[i + 1:]
    return "", []


def positional(args: list[str]) -> list[str]:
    return [a for a in args if not a.startswith("-")]


INSTALLISH_SYSTEM = {"install", "add", "reinstall", "upgrade", "update", "dist-upgrade",
                     "full-upgrade", "tap", "-S", "-Sy", "-Syu", "-U", "-i", "localinstall", "groupinstall"}


def detect_install(cmd: str, args: list[str]) -> str | None:
    """Return a human-readable description if this simple command installs something."""
    pos = positional(args)
    sub = pos[0] if pos else ""
    sub2 = pos[1] if len(pos) > 1 else ""
    full = " ".join([cmd] + args)

    rules = [
        (cmd == "npm" and sub in {"install", "i", "in", "ins", "inst", "insta", "instal", "isnt", "isntal",
                                   "add", "ci", "clean-install", "install-test", "it", "install-ci-test",
                                   "update", "up", "upgrade", "exec", "x", "link", "ln", "rebuild"},
         "npm package install/exec"),
        (cmd == "pnpm" and sub in {"add", "install", "i", "update", "up", "upgrade", "dlx", "link", "exec"},
         "pnpm package install/exec"),
        (cmd == "yarn" and (sub == "" or sub in {"add", "install", "up", "upgrade", "dlx", "global", "link"}),
         "yarn package install"),
        (cmd == "bun" and sub in {"add", "install", "i", "update", "x", "link"}, "bun package install"),
        (cmd in {"npx", "pnpx", "bunx", "uvx"}, f"{cmd} (downloads and runs a package)"),
        (cmd == "corepack", "corepack (downloads package managers)"),
        (cmd == "deno" and sub in {"install", "add"}, "deno install"),
        (cmd in {"pip", "pip3"} and sub in {"install", "download"}, "pip install"),
        (cmd.startswith("python") and "-m" in args and
         args[args.index("-m") + 1:args.index("-m") + 2] in (["pip"], ["ensurepip"]) and
         ("install" in args or "ensurepip" in args), "pip install via python -m"),
        (cmd == "pipx", "pipx install/run"),
        (cmd == "uv" and (sub in {"add", "sync", "tool"} or (sub == "pip" and sub2 in {"install", "sync"})
                          or (sub == "run" and "--with" in " ".join(args)) or (sub == "python" and sub2 == "install")),
         "uv package/tool install"),
        (cmd == "poetry" and sub in {"add", "install", "update", "self"}, "poetry install"),
        (cmd == "pdm" and sub in {"add", "install", "update", "sync"}, "pdm install"),
        (cmd in {"conda", "mamba", "micromamba"} and sub in {"install", "create", "update", "env"}, "conda install"),
        (cmd == "cargo" and sub in {"install", "add", "binstall"}, "cargo install"),
        (cmd == "rustup" and sub not in {"show", "--version", ""}, "rustup toolchain change"),
        (cmd == "go" and sub in {"install", "get"}, "go install/get"),
        (cmd == "gem" and sub in {"install", "update"}, "gem install"),
        (cmd in {"bundle", "bundler"} and sub in {"install", "add", "update"}, "bundler install"),
        (cmd == "composer" and sub in {"install", "require", "update", "global"}, "composer install"),
        (cmd == "dotnet" and sub in {"add", "tool", "workload", "restore"}, "dotnet package/tool install"),
        (cmd in {"nuget"} and sub == "install", "nuget install"),
        (cmd in {"apt", "apt-get", "aptitude", "dnf", "yum", "zypper", "pacman", "apk", "brew", "port",
                 "snap", "flatpak", "choco", "winget", "scoop", "emerge", "xbps-install", "pkg"}
         and (sub in INSTALLISH_SYSTEM or cmd == "xbps-install"), f"system package install ({cmd})"),
        (cmd == "dpkg" and ("-i" in args or "--install" in args), "dpkg install"),
        (cmd in {"nix-env", "nix"} and any(a in args for a in ("-i", "--install", "profile", "install")),
         "nix install"),
        (cmd in {"nvm", "fnm", "volta", "asdf", "mise", "rtx", "pyenv", "rbenv", "sdk", "sdkman", "goenv"}
         and sub in {"install", "add", "plugin", "use", "global"}, f"toolchain install ({cmd})"),
        (cmd == "make" and "install" in pos, "make install"),
        (cmd in {"curl", "wget", "aria2c", "fetch"}, f"network download ({cmd})"),
        (cmd == "git" and (sub == "clone" or (sub == "submodule" and sub2 in {"add", "update"})
                           or (sub == "lfs" and sub2 in {"pull", "fetch", "install"})), "git clone/submodule fetch"),
        (cmd in {"docker", "podman", "nerdctl"} and sub in {"pull", "run", "build", "create", "compose", "buildx"},
         f"container image pull/run ({cmd})"),
        (cmd == "claude" and sub in {"mcp", "plugin", "plugins", "install", "update", "migrate-installer"},
         "Claude Code plugin/MCP/self install"),
        (cmd == "codex" and sub in {"mcp", "plugin", "plugins", "update"}, "Codex MCP/plugin change"),
        (cmd in {"code", "code-insiders", "cursor"} and "--install-extension" in args, "editor extension install"),
    ]
    for matched, label in rules:
        if matched:
            return f"{label}: `{full[:160]}`"
    return None


def plugins_root() -> str:
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(os.path.realpath(config_dir), "plugins")


def check_plugin_scripts(tokens: list[str], segments: list[dict], cwd: str, mode: str) -> set[str]:
    """
    Commands that run a script from the Claude plugin cache are excluded from the
    sandbox (the Codex companion needs ~/.codex and network). Only allow that for
    a single, plain `node <plugins>/.../codex-companion.mjs ...` command.
    Returns the set of tokens that were validated as trusted plugin scripts.
    """
    root = plugins_root()
    trusted: set[str] = set()
    plugin_tokens = [t for t in tokens if "/plugins/" in t or t.endswith("codex-companion.mjs")]
    if not plugin_tokens:
        return trusted
    for tok in plugin_tokens:
        if ".." in tok.split("/"):
            emit("deny", "Plugin script paths containing '..' are not allowed.")
        resolved = resolve(tok, cwd)
        if not is_inside(resolved, root):
            if tok.endswith("codex-companion.mjs"):
                emit("deny", "Only the Codex companion from the Claude plugin cache may run outside the sandbox; "
                             f"{resolved} is not in {root}.")
            continue
        if len(segments) != 1 or any(t in REDIRECT_OPERATORS for t in tokens):
            emit("deny", "Plugin scripts must run as a single command without chaining, pipes, or redirects.")
        cmd, args = command_and_args(segments[0]["tokens"])
        if cmd not in {"node"} or not args or resolve(args[0], cwd) != resolved:
            ask_or_deny(mode, f"Unusual use of a plugin-cache file: `{' '.join(tokens)[:160]}`")
        if os.path.basename(resolved) != "codex-companion.mjs":
            ask_or_deny(mode, f"Running a plugin script other than the Codex companion: {resolved}")
        trusted.add(tok)
    return trusted


def analyze_bash(command: str, cwd: str, root: str, mode: str) -> None:
    tokens = tokenize(command)
    segments = split_segments(tokens)
    trusted_plugin_tokens = check_plugin_scripts(tokens, segments, cwd, mode)

    # --- privilege escalation & pipe-to-shell ------------------------------
    for idx, seg in enumerate(segments):
        cmd, args = command_and_args(seg["tokens"])
        raw_first = os.path.basename(seg["tokens"][0]) if seg["tokens"] else ""
        if cmd in PRIVILEGE_COMMANDS or raw_first in PRIVILEGE_COMMANDS:
            emit("deny", f"Privilege escalation (`{cmd or raw_first}`) is not allowed.")
        if cmd in {"curl", "wget"} and idx + 1 < len(segments) and segments[idx + 1]["prev_op"] in {"|", "|&"}:
            nxt, _ = command_and_args(segments[idx + 1]["tokens"])
            if nxt in SHELL_INTERPRETERS or nxt in PRIVILEGE_COMMANDS:
                emit("deny", "Piping a download straight into a shell/interpreter is not allowed. "
                             "Download it, review it, then decide.")
        if cmd in {"eval"} and any("base64" in t for t in args):
            emit("deny", "Evaluating encoded payloads is not allowed.")

    # --- path checks: writes outside / to protected paths, reads outside ----
    outside_reads: list[str] = []
    for seg in segments:
        toks = seg["tokens"]
        cmd, args = command_and_args(toks)
        is_write_cmd = cmd in WRITE_COMMANDS or (cmd in {"sed", "perl"} and any(a.startswith("-i") for a in args))
        cmd_index = len(toks) - len(args) - 1  # position of the command token itself

        for i, tok in enumerate(toks):
            if i == cmd_index or (i < cmd_index and os.path.basename(tok) in WRAPPER_COMMANDS):
                continue  # executable path (or wrapper like /usr/bin/env), not data
            if tok in trusted_plugin_tokens:
                continue  # validated Codex companion script
            redirect_target = i > 0 and toks[i - 1] in REDIRECT_OPERATORS and not tok.startswith("&")
            # a bare relative redirect target inside the repo is fine; check it anyway for protection
            candidates = path_candidates(tok)
            if redirect_target and not candidates:
                candidates = [tok]
            for cand in candidates:
                resolved = resolve(cand, cwd)
                if is_safe_outside(resolved):
                    continue
                if is_protected(resolved, root) and (is_write_cmd or redirect_target):
                    emit("deny", f"Modifying guard-rail files ({os.path.relpath(resolved, root)}) is not allowed. "
                                 "Edit them yourself outside of Claude.")
                if is_inside(resolved, root):
                    continue
                if redirect_target or is_write_cmd:
                    emit("deny", f"Writing outside the repository is not allowed "
                                 f"(`{cmd}` touches {resolved}). Do it manually if you really need it.")
                outside_reads.append(resolved)

    # Also catch bare references to guard files in write-ish commands (relative paths)
    for seg in segments:
        cmd, args = command_and_args(seg["tokens"])
        if cmd in WRITE_COMMANDS or (cmd in {"sed", "perl"} and any(a.startswith("-i") for a in args)):
            for a in args:
                if a.startswith("-") or looks_like_path(a):
                    continue
                if is_protected(resolve(a, cwd), root) and cmd not in {"curl", "wget", "tar", "unzip"}:
                    emit("deny", f"Modifying guard-rail files ({a}) is not allowed. Edit them yourself.")
        if cmd == "git" and args[:1] == ["config"] and not any(
                a in args for a in ("--get", "--get-all", "--list", "-l", "--get-regexp")):
            ask_or_deny(mode, "Changing git config can alter hooks and credential behaviour.")

    # --- installs ---------------------------------------------------------------
    for seg in segments:
        cmd, args = command_and_args(seg["tokens"])
        label = detect_install(cmd, args)
        if label:
            ask_or_deny(mode, f"Install/download detected -> {label}. Approve only if you expect this.")

    if outside_reads:
        uniq = sorted(set(outside_reads))[:5]
        ask_or_deny(mode, "Command reads outside the repository: " + ", ".join(uniq))


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        emit("ask", "Guard could not parse the tool call; asking to be safe.")

    tool = data.get("tool_name", "")
    tin = data.get("tool_input", {}) or {}
    mode = data.get("permission_mode", "default") or "default"
    cwd = data.get("cwd") or os.getcwd()
    root = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)

    if tool == "Bash":
        analyze_bash(tin.get("command", ""), os.path.realpath(cwd), root, mode)
        return

    if tool in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        target = tin.get("file_path") or tin.get("notebook_path") or ""
        if not target:
            return
        resolved = resolve(target, cwd)
        if not is_inside(resolved, root):
            emit("deny", f"Writing outside the repository is not allowed ({resolved}).")
        if is_protected(resolved, root):
            emit("deny", f"Guard-rail file ({os.path.relpath(resolved, root)}) is read-only for Claude. "
                         "Edit it yourself.")
        return

    if tool in {"Read", "Glob", "Grep", "LS"}:
        targets = [tin.get("file_path"), tin.get("path")]
        pattern = tin.get("pattern") or ""
        if tool == "Glob" and looks_like_path(pattern):
            targets.append(pattern.split("*")[0] or "/")
        for t in filter(None, targets):
            resolved = resolve(t, cwd)
            if not is_inside(resolved, root) and not is_safe_outside(resolved):
                ask_or_deny(mode, f"Reading outside the repository: {resolved}")
        return


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # never fail open silently
        emit("ask", f"Guard hit an internal error ({type(exc).__name__}); asking to be safe.")
