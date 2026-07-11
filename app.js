#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../services/api"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8787 --reload
