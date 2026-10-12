#!/bin/bash
# Create a fresh project from this template (run on your host machine).
# Usage: bash scripts/new-project.sh ../my-new-project
set -euo pipefail
TARGET="${1:?usage: new-project.sh <target-directory>}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"

if [ -e "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  echo "Target $TARGET exists and is not empty." >&2; exit 1
fi
mkdir -p "$TARGET"

( cd "$SRC" && tar --exclude=.git --exclude=.cache --exclude=node_modules --exclude=.venv \
    --exclude=.claude/settings.local.json --exclude='.env' -cf - . ) | ( cd "$TARGET" && tar -xf - )

rm -rf "$TARGET/src" && mkdir -p "$TARGET/src" && touch "$TARGET/src/.gitkeep"
( cd "$TARGET" && git init -q && git add -A && git commit -qm "Initial commit from safe-agent-workspace template" ) \
  || echo "(git commit skipped - configure git user.name/email first)"

echo "Created $TARGET. Open it in VS Code and choose 'Reopen in Container'."
