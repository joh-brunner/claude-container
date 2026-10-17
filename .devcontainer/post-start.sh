#!/bin/bash
# Runs on every container start (as user "dev"), only after init-firewall.sh succeeded.
# Package installs happen here rather than in post-create.sh, which runs before the
# firewall is up: install scripts from packages should never run with open network.
set -uo pipefail
cd /workspace

# Verify the protections; like the firewall, a failed check fails the container start.
if ! bash /workspace/.devcontainer/check-setup.sh; then
  echo "[post-start] ERROR: setup check failed (see [FAIL] lines above). Not continuing." >&2
  exit 1
fi

if [ -f pyproject.toml ]; then
  echo "[post-start] pyproject.toml found, running uv sync"
  uv sync || echo "[post-start] WARNING: uv sync failed (see above). Fix it and run 'uv sync' by hand." >&2
fi
