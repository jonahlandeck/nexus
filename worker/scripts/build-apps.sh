#!/usr/bin/env bash
# Build every registered app's SPA into worker/public/apps/<slug>/.
#
# Each app needs a "build:embedded" npm script that runs its bundler with the
# right sub-path base, e.g.  vite build --base=/apps/<slug>/
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo="$(cd "$here/.." && pwd)"

build_spa() {
  local slug="$1" src="$2"
  echo "==> building $slug  ($src)"
  ( cd "$repo/$src" && npm ci && npm run build:embedded )
  rm -rf "$here/public/apps/$slug"
  mkdir -p "$here/public/apps/$slug"
  cp -R "$repo/$src/dist/." "$here/public/apps/$slug/"
  echo "    -> worker/public/apps/$slug/"
}

build_spa "meat-and-potatoes" "apps/meat-and-potatoes/frontend"

echo "==> done"
