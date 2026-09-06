#!/usr/bin/env bash
# Run the Meat And Potatoes backend (FastAPI, :8000) and frontend (Vite, :5173) together.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d backend/.venv ]]; then
  echo "==> creating backend venv"
  python3.12 -m venv backend/.venv
  backend/.venv/bin/pip -q install -U pip
  backend/.venv/bin/pip -q install -e "backend[dev]"
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "==> installing frontend deps"
  (cd frontend && npm install)
fi

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "==> backend  http://localhost:8000  (docs at /docs)"
( cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000 ) &

echo "==> frontend http://localhost:5173"
( cd frontend && npm run dev ) &

wait
