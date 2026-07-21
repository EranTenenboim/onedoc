#!/usr/bin/env bash
# Deploy / run Medical Expert AI Chat without Docker.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"

if [[ ! -d .venv ]]; then
  echo "Creating Python 3.13 virtualenv..."
  if command -v uv >/dev/null 2>&1; then
    uv python install 3.13 >/dev/null
    uv venv --python 3.13 .venv
  elif command -v python3.13 >/dev/null 2>&1; then
    python3.13 -m venv .venv
  else
    echo "Python 3.13 is required. Install with: uv python install 3.13" >&2
    exit 1
  fi
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if command -v uv >/dev/null 2>&1; then
  uv pip install -e .
else
  pip install -e .
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example (edit for production LLM keys)."
fi

mkdir -p logs

PORT="$(grep -E '^SERVER_PORT=' .env 2>/dev/null | cut -d= -f2- || true)"
PORT="${PORT:-8000}"

echo "Starting Medical Expert AI Chat on port ${PORT}..."
exec medical-chat
