#!/bin/bash
# Runs on your HOST machine (not in the container), before the container is created.
# devcontainer.json mounts these paths read-only, and a bind mount fails if its source
# does not exist yet, so create them here.
set -euo pipefail
cd "${1:-.}"

if [ ! -e .git ]; then
  if command -v git >/dev/null 2>&1; then
    git init -q && echo "[init] initialised git repository"
  else
    # Git is optional on the host: create the same empty repository `git init` would,
    # so git works inside the container (where it is installed).
    mkdir -p .git/objects/info .git/objects/pack .git/refs/heads .git/refs/tags .git/info
    echo "ref: refs/heads/main" > .git/HEAD
    printf '[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n\tlogallrefupdates = true\n' > .git/config
    echo "[init] git not found on host: created an empty git repository by hand"
  fi
fi
if [ ! -d .git ]; then
  echo "[init] ERROR: .git is not a directory (worktree or submodule checkout?)." >&2
  echo "[init] The read-only mounts need a normal clone. Open the main checkout instead." >&2
  exit 1
fi

mkdir -p .git/hooks .git/modules .vscode
touch .git/config
