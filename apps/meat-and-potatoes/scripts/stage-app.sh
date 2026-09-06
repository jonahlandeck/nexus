#!/usr/bin/env bash
# Pre-build step for the Cloudflare Python Worker (wired via [build].command in
# wrangler.jsonc; runs before `pywrangler dev` and `pywrangler deploy`).
#
# 1. Stage the FastAPI app package into src/ - the Python Worker bundler only
#    includes files under src/ (the directory of `main`). src/app is gitignored.
#    Checksum copy (rsync -c) so a no-op run rewrites nothing, otherwise
#    `wrangler dev`'s watcher would rebuild in a loop.
# 2. Sanity-check that the SPA has been built.
set -euo pipefail
cd "$(dirname "$0")/.."   # -> apps/meat-and-potatoes

mkdir -p src/app
rsync -rc --delete --exclude='__pycache__' --exclude='*.pyc' \
  backend/app/ src/app/
echo "staged backend/app -> src/app"

if [ ! -f frontend/dist/index.html ]; then
  echo "ERROR: frontend/dist/index.html is missing." >&2
  echo "Build the SPA first:" >&2
  echo "  (cd frontend && npm install && npm run build:embedded)" >&2
  exit 1
fi
