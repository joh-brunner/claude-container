#!/bin/bash
# Runs once when the container is created (as user "dev").
set -euo pipefail

cd /workspace

# Cache directories inside the repo (gitignored)
mkdir -p /workspace/.cache/pip /workspace/.cache/uv

# Git: trust the mounted repo (it is created on the host by initialize.sh)
git config --global --add safe.directory /workspace

cat <<'EOF'

============================================================
 Container ready.

   Open the Claude Code panel and log in.
   (The setup is checked automatically on every start.)
============================================================
EOF
