FROM python:3.12-slim-bookworm

ARG CLAUDE_CODE_VERSION=latest
ARG TZ=Europe/Berlin
ENV TZ=${TZ}

# --- System packages (installed at build time only; the agent user cannot use apt) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git less jq procps man-db unzip nano vim \
      sudo iptables ipset iproute2 dnsutils \
      ripgrep fzf \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Agent user (uid 1000, so files it creates in the project belong to you on a typical Linux host) ---
RUN useradd --create-home --uid 1000 --shell /bin/bash dev

# --- Claude Code (native build, no Node.js), copied to a root-owned path => read-only for the agent user ---
RUN curl -fsSL https://claude.ai/install.sh | bash -s "${CLAUDE_CODE_VERSION}" \
    && install -m 0755 "$(readlink -f /root/.local/bin/claude)" /usr/local/bin/claude \
    && rm -rf /root/.local/bin/claude /root/.local/share/claude /root/.claude /root/.claude.json

# --- uv (Python package manager), root-owned => read-only for the agent user ---
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /usr/local/bin/

# --- Directories owned by the agent user (volumes are mounted on top) ---
RUN mkdir -p /home/dev/.claude /commandhistory /workspace \
    && chown -R dev:dev /home/dev/.claude /commandhistory /workspace

# --- Firewall (root-owned, agent can read but not change) ---
COPY init-firewall.sh /usr/local/bin/init-firewall.sh
COPY allowed-domains.txt /etc/agent-firewall/allowed-domains.txt
RUN chmod 0755 /usr/local/bin/init-firewall.sh \
    && chmod 0644 /etc/agent-firewall/allowed-domains.txt \
    && echo "dev ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/dev-firewall \
    && chmod 0440 /etc/sudoers.d/dev-firewall \
    && visudo -cf /etc/sudoers.d/dev-firewall

USER dev

# Caches live inside the repo (gitignored), so they survive container rebuilds
ENV CLAUDE_CONFIG_DIR=/home/dev/.claude \
    DISABLE_AUTOUPDATER=1 \
    XDG_CACHE_HOME=/workspace/.cache \
    PIP_CACHE_DIR=/workspace/.cache/pip \
    UV_CACHE_DIR=/workspace/.cache/uv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PIP_REQUIRE_VIRTUALENV=true \
    HISTFILE=/commandhistory/.bash_history \
    PROMPT_COMMAND="history -a" \
    EDITOR=nano

WORKDIR /workspace
