#!/bin/bash
# Runs on your HOST machine (not in the container), before the container is created.
# devcontainer.json mounts these paths read-only, and a bind mount fails if its source
# does not exist yet, so create them here.
set -euo pipefail
cd "${1:-.}"

if [ ! -e .git ]; then
  git init -q && echo "[init] initialised git repository"
fi
if [ ! -d .git ]; then
  echo "[init] ERROR: .git is not a directory (worktree or submodule checkout?)." >&2
  echo "[init] The read-only mounts need a normal clone. Open the main checkout instead." >&2
  exit 1
fi

mkdir -p .git/hooks .git/modules .vscode
touch .git/config
