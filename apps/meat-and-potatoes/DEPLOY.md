# Deploying meat-and-potatoes

Self-contained Cloudflare **Python Worker** (`wrangler.jsonc` in this directory,
Worker name `nexus-meat-and-potatoes`) serving the app at
`https://landeck.pro/apps/meat-and-potatoes`. All paths below are relative to
`apps/meat-and-potatoes/` — `cd` here first.

| Request | Handled by |
|---|---|
| `/apps/meat-and-potatoes/api/*`, `/docs`, `/openapi.json` | the FastAPI app (`backend/app`), run through the Workers ASGI adapter with `root_path="/apps/meat-and-potatoes"` |
| everything else under the path | the built Vite SPA (`frontend/dist`) via the `ASSETS` binding, with SPA fallback for client routes |

Persistence is **Cloudflare D1** (`DB` binding). The FastAPI app talks to it
through `backend/app/d1.py` + `backend/app/store.py` (raw SQL) — no
SQLAlchemy/SQLite. Config comes from the Worker `env` (`[vars]` + secrets).

`src/worker.py` is the entry point. `src/app/` is a **staged copy** of
`backend/app` (gitignored) — the Python Worker bundler only includes files under
`src/`, so `scripts/stage-app.sh` copies it there before every `dev`/`deploy`
(wired via `[build].command`). It also checks that `frontend/dist` was built.

## Toolchain

- **Node 22** — required. `wrangler` needs Node >= 22; the Pyodide cross-build
  toolchain that `pywrangler sync` uses breaks on Node 24+ (removed
  `--experimental-wasm-stack-switching`). Node 22 satisfies both.
  `brew install node@22`, then prefix commands with
  `PATH="/opt/homebrew/opt/node@22/bin:$PATH"`.
- **uv** — `brew install uv` (provides `pywrangler` via the `dev` dependency group).

## One-time setup

```sh
cd apps/meat-and-potatoes

uv sync
uv run pywrangler sync

# create D1, then paste the printed database_id into
# wrangler.jsonc -> d1_databases[0].database_id
npx wrangler d1 create meat-and-potatoes
npx wrangler d1 migrations apply meat-and-potatoes --remote   # production
npx wrangler d1 migrations apply meat-and-potatoes --local    # local dev

# build the SPA with the sub-path base
(cd frontend && npm install && npm run build:embedded)

# secrets (never commit)
npx wrangler secret put SCRAPERAPI_KEY
#   OLLAMA_URL must be a model host reachable from the edge (localhost Ollama
#   won't work); set it in [vars] or as a secret.
```

## Local dev

```sh
cd apps/meat-and-potatoes
# .dev.vars holds local secrets (gitignored)
PATH="/opt/homebrew/opt/node@22/bin:$PATH" uv run pywrangler dev
# -> http://localhost:8787/apps/meat-and-potatoes/
```

## Deploy

```sh
cd apps/meat-and-potatoes
export CLOUDFLARE_API_TOKEN=...        # token from .env
PATH="/opt/homebrew/opt/node@22/bin:$PATH" uv run pywrangler deploy
```

`landeck.pro` must be an active zone in the same account for the route to attach.
This route (`landeck.pro/apps/meat-and-potatoes*`) is more specific than the root
site's `landeck.pro/*`, so the two Workers coexist.

## What runs where

- `mock` grocery provider (default) works fully on the Worker — but its item IDs
  are fake, so the Walmart cart link won't populate a real cart. Set
  `MAP_PROVIDER=scraperapi` + `SCRAPERAPI_KEY` for real IDs.
- `/api/plan/generate` and `/api/intake/message` need a reachable
  Ollama-compatible endpoint (`OLLAMA_URL`). Without one they return `502`; the
  rest of the app is unaffected.
