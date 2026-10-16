FROM node:22-bookworm

ARG CLAUDE_CODE_VERSION=latest
ARG TZ=Europe/Berlin
ARG SANDBOX_FAIL_CLOSED=true
ENV TZ=${TZ}

# --- System packages (installed at build time only; the agent user cannot use apt) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git less jq procps man-db unzip nano vim \
      sudo iptables ipset iproute2 dnsutils \
      python3 python3-venv python3-pip \
      ripgrep fzf \
      bubblewrap socat \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Agent CLIs, installed globally as root => read-only for the agent user ---
RUN npm install -g \
      "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
      "@anthropic-ai/sandbox-runtime" \
    && npm cache clean --force

# --- Directories owned by the agent user (volumes are mounted on top) ---
RUN mkdir -p /home/node/.claude /commandhistory /workspace \
    && chown -R node:node /home/node/.claude /commandhistory /workspace

# --- Firewall + locked policy files (root-owned, agent can read but not change) ---
COPY init-firewall.sh /usr/local/bin/init-firewall.sh
COPY allowed-domains.txt /etc/sandbox/allowed-domains.txt
COPY managed-settings.json /etc/claude-code/managed-settings.json
RUN chmod 0755 /usr/local/bin/init-firewall.sh \
    && chmod 0644 /etc/sandbox/allowed-domains.txt /etc/claude-code/managed-settings.json \
    && if [ "${SANDBOX_FAIL_CLOSED}" != "true" ]; then \
         tmp=$(mktemp) && jq '.sandbox.failIfUnavailable=false' /etc/claude-code/managed-settings.json > "$tmp" \
         && mv "$tmp" /etc/claude-code/managed-settings.json && chmod 0644 /etc/claude-code/managed-settings.json; \
       fi \
    && echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall \
    && chmod 0440 /etc/sudoers.d/node-firewall \
    && visudo -cf /etc/sudoers.d/node-firewall

USER node

# Caches live inside the repo (gitignored), so the sandbox never needs to write to $HOME
ENV CLAUDE_CONFIG_DIR=/home/node/.claude \
    DISABLE_AUTOUPDATER=1 \
    XDG_CACHE_HOME=/workspace/.cache \
    npm_config_cache=/workspace/.cache/npm \
    PIP_CACHE_DIR=/workspace/.cache/pip \
    UV_CACHE_DIR=/workspace/.cache/uv \
    PIP_REQUIRE_VIRTUALENV=true \
    HISTFILE=/commandhistory/.bash_history \
    PROMPT_COMMAND="history -a" \
    EDITOR=nano

WORKDIR /workspace
