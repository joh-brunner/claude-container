FROM node:22-bookworm

ARG CLAUDE_CODE_VERSION=latest
ARG TZ=Europe/Berlin
ENV TZ=${TZ}

# --- System packages (installed at build time only; the agent user cannot use apt) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git less jq procps man-db unzip nano vim \
      sudo iptables ipset iproute2 dnsutils \
      python3 python3-venv python3-pip \
      ripgrep fzf \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Agent CLIs, installed globally as root => read-only for the agent user ---
RUN npm install -g \
      "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    && npm cache clean --force

# --- Directories owned by the agent user (volumes are mounted on top) ---
RUN mkdir -p /home/node/.claude /commandhistory /workspace \
    && chown -R node:node /home/node/.claude /commandhistory /workspace

# --- Firewall (root-owned, agent can read but not change) ---
COPY init-firewall.sh /usr/local/bin/init-firewall.sh
COPY allowed-domains.txt /etc/agent-firewall/allowed-domains.txt
RUN chmod 0755 /usr/local/bin/init-firewall.sh \
    && chmod 0644 /etc/agent-firewall/allowed-domains.txt \
    && echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall \
    && chmod 0440 /etc/sudoers.d/node-firewall \
    && visudo -cf /etc/sudoers.d/node-firewall

USER node

# Caches live inside the repo (gitignored), so they survive container rebuilds
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
