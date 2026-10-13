#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! python3 -m venv /tmp/.venv-probe 2>/dev/null; then
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv
fi
rm -rf /tmp/.venv-probe

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements-dev.txt
