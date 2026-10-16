#!/bin/bash
# Verify the sandbox inside the dev container. Run: bash scripts/check-setup.sh
set -uo pipefail
pass() { echo "  [ok]   $1"; }
fail() { echo "  [FAIL] $1"; FAILED=1; }
FAILED=0
cd "$(dirname "$0")/.."

echo "Tools"
command -v claude >/dev/null && pass "claude $(claude --version 2>/dev/null | head -1)" || fail "claude not found"
command -v bwrap  >/dev/null && pass "bubblewrap present" || fail "bubblewrap missing (sandbox cannot start)"
command -v socat  >/dev/null && pass "socat present"      || fail "socat missing"

echo "Policy"
[ -f /etc/claude-code/managed-settings.json ] && pass "managed settings installed" || fail "managed settings missing (not in container?)"
[ -w /etc/claude-code/managed-settings.json ] && fail "managed settings are writable by $(whoami)" || pass "managed settings read-only"
[ -w /usr/local/bin/claude ] 2>/dev/null && fail "claude binary writable" || pass "global CLIs read-only"
sudo -n true 2>/dev/null && fail "unrestricted sudo available" || pass "no general sudo"
python3 -m json.tool .claude/settings.json >/dev/null && pass ".claude/settings.json is valid JSON" || fail "invalid .claude/settings.json"

echo "Network"
if curl --connect-timeout 5 -s https://example.com >/dev/null 2>&1; then fail "example.com reachable (firewall off?)"; else pass "example.com blocked"; fi
curl --connect-timeout 8 -s -o /dev/null https://api.anthropic.com && pass "api.anthropic.com reachable" || fail "api.anthropic.com blocked"

echo "Filesystem"
touch /home/node/.write-test 2>/dev/null && { rm -f /home/node/.write-test; echo "  [info] \$HOME writable by you (expected; Claude's sandbox still blocks it)"; }
touch /etc/write-test 2>/dev/null && fail "/etc writable" || pass "/etc not writable"

echo "Guard hook"
python3 scripts/test-guard.py >"${TMPDIR:-/tmp}/guard-test.log" 2>&1 && pass "guard tests: $(tail -1 "${TMPDIR:-/tmp}/guard-test.log")" || { fail "guard tests failed (see "${TMPDIR:-/tmp}/guard-test.log")"; }

echo
[ "$FAILED" = 0 ] && echo "All checks passed." || { echo "Some checks failed."; exit 1; }
