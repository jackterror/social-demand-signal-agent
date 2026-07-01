#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"
if [[ ! -f runtime/company-profile.json ]]; then
  python3 scripts/signal_agent.py init
fi
python3 scripts/signal_agent.py serve
