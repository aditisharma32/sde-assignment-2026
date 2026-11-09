#!/usr/bin/env bash
# Outcome-First Agent Loop Controller
# Contract: ./run.sh <SIM_URL> runs until the scenario finishes.
set -euo pipefail

SIM_URL="${1:?usage: ./run.sh <SIM_URL>}"
shift || true

# Find appropriate python binary
PYTHON="python3"
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
    PYTHON="${VIRTUAL_ENV}/bin/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
fi

exec "$PYTHON" -m controller.main --url "$SIM_URL" "$@"
