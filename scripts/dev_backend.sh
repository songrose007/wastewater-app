#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/backend"
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
