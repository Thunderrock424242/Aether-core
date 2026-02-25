#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../aether_sidecar"
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python run.py
