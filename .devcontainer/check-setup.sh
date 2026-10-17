#!/bin/bash
# Verify the container's protections. Run inside the container: bash .devcontainer/check-setup.sh
set -uo pipefail
pass() { echo "  [ok]   $1"; }
fail() { echo "  [FAIL] $1"; FAILED=1; }
warn() { echo "  [warn] $1"; }
FAILED=0
cd "$(dirname "$0")/.."

echo "Tools"
command -v claude >/dev/null && pass "claude $(claude --version 2>/dev/null | head -1)" || fail "claude not found"
command -v uv >/dev/null && pass "$(uv --version)" || fail "uv not found"

echo "Container"
[ -d /workspace ] && pass "running in the dev container" || fail "/workspace missing (not in container?)"
[ -w /usr/local/bin/claude ] 2>/dev/null && fail "claude binary writable" || pass "global CLIs read-only"
sudo -n true 2>/dev/null && fail "unrestricted sudo available" || pass "no general sudo"
touch /etc/write-test 2>/dev/null && fail "/etc writable" || pass "/etc not writable"

echo "Network"
if curl --connect-timeout 5 -s https://example.com >/dev/null 2>&1; then fail "example.com reachable (firewall off?)"; else pass "example.com blocked"; fi
curl --connect-timeout 8 -s -o /dev/null https://api.anthropic.com && pass "api.anthropic.com reachable" || fail "api.anthropic.com blocked"

echo "Credentials (should stay on your host)"
[ -z "$(git config --global --get-all credential.helper 2>/dev/null)" ] && pass "no git credential helper" || fail "git credential helper set (check VS Code host settings)"
# VS Code forwards your SSH agent whenever it was started with SSH_AUTH_SOCK set, with no setting to
# turn it off. Programs here could then use (not copy) your SSH keys; the firewall blocks SSH itself.
[ -z "${SSH_AUTH_SOCK:-}" ] && pass "no SSH agent forwarded" \
  || warn "SSH agent forwarded by VS Code: your SSH keys can be used (not copied) from here"

echo "Read-only paths (files that can run code on your host)"
for p in .devcontainer .vscode .git/hooks .git/config .git/modules; do
  if [ ! -e "$p" ]; then fail "$p missing (did initialize.sh run on the host?)"
  elif [ -w "$p" ]; then fail "$p is writable"
  else pass "$p read-only"; fi
done

echo
[ "$FAILED" = 0 ] && echo "All checks passed." || { echo "Some checks failed."; exit 1; }
