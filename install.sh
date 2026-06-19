#!/usr/bin/env bash
# One-shot install on the homelab box. After this, just SSH in and run: gym
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
uv tool install --force .
echo "Installed. Run 'gym' to start a drill session, 'gym refill' to top up the LLM variant pool."
