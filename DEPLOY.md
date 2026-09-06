# Deploying to landeck.pro

One Cloudflare **Python Worker** (`wrangler.jsonc` at the repo root, Worker name
`nexus`) serves `apps/meat-and-potatoes` at `https://landeck.pro/apps/meat-and-potatoes`:

| Request | Handled by |
|---|---|
| `/apps/meat-and-potatoes/api/*`, `/docs`, `/openapi.json` | the FastAPI app (`apps/meat-and-potatoes/backend/app`), run through the Workers ASGI adapter with `root_path="/apps/meat-and-potatoes"` |
| everything else under the path | the built Vite SPA (`apps/meat-and-potatoes/frontend/dist`) via the `ASSETS` binding, with SPA fallback for client routes |

Persistence is **Cloudflare D1** (`DB` binding). The FastAPI app talks to it
through `app/d1.py` + `app/store.py` (raw SQL); there is no SQLAlchemy/SQLite
anymore. Config comes from the Worker `env` (`[vars]` + secrets), not `.env`.

`src/worker.py` is the entry point. `src/app/` is a **staged copy** of
`apps/meat-and-potatoes/backend/app` (gitignored) - the Python Worker bundler
only includes files under `src/`, so `scripts/stage-app.sh` copies it there
before every `dev`/`deploy` (wired via `[build].command`).

## Toolchain

- **Node 22** - required. `wrangler` needs Node >= 22; the Pyodide cross-build
  toolchain that `pywrangler sync` uses breaks on Node 24+ (removed
  `--experimental-wasm-stack-switching`). Node 22 is the version that satisfies
  both. `brew install node@22` and put `/opt/homebrew/opt/node@22/bin` first on
  `PATH` for wrangler commands.
- **uv** - `brew install uv` (provides `pywrangler` via the `dev` dependency group).

## One-time setup

```sh
# 1. deps (host + Worker vendor dir python_modules/)
uv sync
uv run pywrangler sync

# 2. create the D1 database, then paste the printed database_id into
#    wrangler.jsonc -> d1_databases[0].database_id
npx wrangler d1 create meat-and-potatoes

# 3. apply the schema
npx wrangler d1 migrations apply meat-and-potatoes --remote     # production
npx wrangler d1 migrations apply meat-and-potatoes --local      # local dev

# 4. build the SPA with the sub-path base
(cd apps/meat-and-potatoes/frontend && npm install && npm run build:embedded)

# 5. secrets (never commit these)
npx wrangler secret put SCRAPERAPI_KEY
#   OLLAMA_URL must point at a model host reachable from the edge; a localhost
#   Ollama will not work. Set it in [vars] (wrangler.jsonc) or as a secret.
```

## Local dev

```sh
cp .dev.vars .dev.vars.local  # already gitignored; edit values as needed
PATH="/opt/homebrew/opt/node@22/bin:$PATH" uv run pywrangler dev
# -> http://localhost:8787/apps/meat-and-potatoes/
```

## Deploy

```sh
PATH="/opt/homebrew/opt/node@22/bin:$PATH" uv run pywrangler deploy
```

Wrangler auth: `export CLOUDFLARE_API_TOKEN=...` (the token in
`apps/meat-and-potatoes/.env`). `landeck.pro` must be an active zone in the same
account for the route to attach.

## What runs where

- `mock` grocery provider (default) works fully on the Worker - but its item IDs
  are fake, so the Walmart cart link won't populate a real cart. Set
  `MAP_PROVIDER=scraperapi` + `SCRAPERAPI_KEY` for real IDs.
- `/api/plan/generate` and `/api/intake/message` need a reachable Ollama-compatible
  endpoint (`OLLAMA_URL`). Without one they return `502` and the rest of the app
  is unaffected.
