#!/bin/zsh
set -euo pipefail
cd "${0:A:h}"
python3 scripts/signal_agent.py demo --reset
python3 scripts/signal_agent.py serve
