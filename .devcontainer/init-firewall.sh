#!/bin/bash
# Default-deny outbound firewall for the agent container.
# Only domains in /etc/sandbox/allowed-domains.txt (resolved at start) are reachable.
# Runs as root via a single sudoers entry; the agent user cannot change it.
set -euo pipefail
IFS=$'\n\t'

DOMAINS_FILE="/etc/sandbox/allowed-domains.txt"
ALLOW_HOST_NETWORK="${ALLOW_HOST_NETWORK:-false}"

echo "[firewall] configuring default-deny egress..."

# Keep Docker's embedded DNS NAT rules before flushing
DOCKER_DNS_RULES=$(iptables-save -t nat | grep "127\.0\.0\.11" || true)

iptables -F; iptables -X
iptables -t nat -F; iptables -t nat -X
iptables -t mangle -F; iptables -t mangle -X
ipset destroy allowed-domains 2>/dev/null || true

if [ -n "$DOCKER_DNS_RULES" ]; then
  iptables -t nat -N DOCKER_OUTPUT 2>/dev/null || true
  iptables -t nat -N DOCKER_POSTROUTING 2>/dev/null || true
  echo "$DOCKER_DNS_RULES" | xargs -L 1 iptables -t nat
fi

# DNS + loopback
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A INPUT  -p udp --sport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
iptables -A INPUT  -p tcp --sport 53 -j ACCEPT
iptables -A INPUT  -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

ipset create allowed-domains hash:net

while IFS= read -r line || [ -n "$line" ]; do
  domain="${line%%#*}"
  domain="$(echo "$domain" | tr -d '[:space:]')"
  [ -z "$domain" ] && continue
  ips=$(dig +short A "$domain" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || true)
  if [ -z "$ips" ]; then
    echo "[firewall] WARNING: could not resolve $domain (skipped)"
    continue
  fi
  while IFS= read -r ip; do
    ipset add allowed-domains "$ip" -exist
  done <<< "$ips"
  echo "[firewall] allowed $domain"
done < "$DOMAINS_FILE"

# Optional: allow the Docker host network (e.g. a database running on your machine).
# Off by default because it widens what the agent can reach.
if [ "$ALLOW_HOST_NETWORK" = "true" ]; then
  HOST_IP=$(ip route | awk '/default/ {print $3; exit}')
  HOST_NETWORK=$(echo "$HOST_IP" | sed 's/\.[0-9]*$/.0\/24/')
  iptables -A INPUT  -s "$HOST_NETWORK" -j ACCEPT
  iptables -A OUTPUT -d "$HOST_NETWORK" -j ACCEPT
  echo "[firewall] host network $HOST_NETWORK allowed"
fi

iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP
iptables -A INPUT  -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m set --match-set allowed-domains dst -j ACCEPT
iptables -A OUTPUT -j REJECT --reject-with icmp-admin-prohibited

# Block IPv6 entirely (the allowlist is IPv4 only)
if command -v ip6tables >/dev/null 2>&1; then
  ip6tables -F 2>/dev/null || true
  ip6tables -P INPUT DROP 2>/dev/null || true
  ip6tables -P FORWARD DROP 2>/dev/null || true
  ip6tables -P OUTPUT DROP 2>/dev/null || true
  ip6tables -A INPUT -i lo -j ACCEPT 2>/dev/null || true
  ip6tables -A OUTPUT -o lo -j ACCEPT 2>/dev/null || true
fi

# --- Verify -----------------------------------------------------------------
if curl --connect-timeout 5 -s https://example.com >/dev/null 2>&1; then
  echo "[firewall] ERROR: example.com is reachable - firewall is NOT working" >&2
  exit 1
fi
echo "[firewall] OK: example.com blocked"

if ! curl --connect-timeout 10 -s -o /dev/null https://api.anthropic.com; then
  echo "[firewall] ERROR: api.anthropic.com unreachable - check allowed-domains.txt" >&2
  exit 1
fi
echo "[firewall] OK: api.anthropic.com reachable"
echo "[firewall] done."
