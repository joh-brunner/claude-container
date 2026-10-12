#!/bin/bash
# Runs once when the container is created (as user "node").
set -euo pipefail

cd /workspace

# Codex config: install template only if the user has none yet
if [ ! -f "$CODEX_HOME/config.toml" ]; then
  cp /etc/sandbox/codex-config.toml "$CODEX_HOME/config.toml"
  echo "[setup] wrote $CODEX_HOME/config.toml from template"
fi

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

   1. claude            -> log in, trust the folder, accept the
                           Codex plugin install prompt
   2. codex login --device-auth
                        (or: printenv OPENAI_API_KEY | codex login --with-api-key)
   3. In Claude Code:   /codex:setup
   4. Verify:           bash scripts/check-setup.sh
============================================================
EOF
