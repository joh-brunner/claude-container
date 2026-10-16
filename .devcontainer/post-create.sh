#!/bin/bash
# Runs once when the container is created (as user "node").
set -euo pipefail

cd /workspace

# Cache directories inside the repo (gitignored)
mkdir -p /workspace/.cache/npm /workspace/.cache/pip /workspace/.cache/uv

# Git: trust the mounted repo (it is created on the host by initialize.sh)
git config --global --add safe.directory /workspace

chmod +x scripts/*.sh 2>/dev/null || true

cat <<'EOF'

============================================================
 Container ready. Next steps (inside this container):

   1. claude            -> log in and trust the folder
   2. Verify:           bash scripts/check-setup.sh
============================================================
EOF
