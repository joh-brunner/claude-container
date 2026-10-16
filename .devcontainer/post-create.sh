#!/bin/bash
# Runs once when the container is created (as user "node").
set -euo pipefail

cd /workspace

# Cache directories inside the repo (gitignored)
mkdir -p /workspace/.cache/npm /workspace/.cache/pip /workspace/.cache/uv

# Git: trust the mounted repo; initialise if this is a fresh copy
git config --global --add safe.directory /workspace
if [ ! -d .git ]; then
  git init -q && echo "[setup] initialised git repository"
fi

chmod +x .claude/hooks/guard.py scripts/*.sh scripts/*.py 2>/dev/null || true

cat <<'EOF'

============================================================
 Container ready. Next steps (inside this container):

   1. claude            -> log in and trust the folder
   2. Verify:           bash scripts/check-setup.sh
============================================================
EOF
