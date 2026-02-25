#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SIDECAR_DIR="$ROOT_DIR/aether_sidecar"
VENV_DIR="$SIDECAR_DIR/.venv"

cd "$SIDECAR_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  python -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -e '.[dev]'

HOST="${AETHER_HOST:-127.0.0.1}"
PORT="${AETHER_PORT:-8765}"
RELOAD="${AETHER_DEV_RELOAD:-true}"

if [[ "$RELOAD" == "true" ]]; then
  python -m uvicorn aether_sidecar.app:app --host "$HOST" --port "$PORT" --reload
else
  python run.py
fi
