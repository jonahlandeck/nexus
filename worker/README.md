# nexus worker

The Cloudflare Worker that serves **`landeck.pro/apps/*`**.

It hosts each app as a static single-page app out of `public/apps/<slug>/`, and
for apps that need one it stubs the backend with canned data so the UI works
with nothing else running.

```
worker/
  src/index.ts       routing: sub-path mount, /api/* stubs, SPA fallback
  src/demo-data.ts    fixtures for the Meat & Potatoes demo
  scripts/build-apps.sh   builds each app's SPA into public/apps/<slug>/
  public/apps/<slug>/    build output (gitignored)
  wrangler.jsonc
```

## Registered apps

| Path | App | Backend |
|------|-----|---------|
| `/apps/meat-and-potatoes` | `apps/meat-and-potatoes` frontend | stubbed — `src/demo-data.ts` |

`meat-and-potatoes` is a **demo**: the real app is a local FastAPI + Ollama +
SQLite stack that can't run on Workers, so `src/index.ts` answers every
`/apps/meat-and-potatoes/api/*` call from `src/demo-data.ts`. The intake chat is
scripted (three turns, then the plan unlocks). It's **stateless** — a pantry
item you add comes back on the next reload, edited profiles aren't saved.

## Develop

```sh
cd worker
npm install
npm run build      # builds the app SPAs into public/apps/
npm run dev        # wrangler dev at http://localhost:8787
```

Open <http://localhost:8787/apps/meat-and-potatoes/>.

`npm run typecheck` type-checks the Worker.

## Deploy

Auth wrangler with an API token (Workers Scripts: Edit + the landeck.pro zone):

```sh
export CLOUDFLARE_API_TOKEN=cfk_...          # the token from apps/meat-and-potatoes/.env
export CLOUDFLARE_ACCOUNT_ID=...             # only if the token spans >1 account
cd worker
npm run deploy                                # build + wrangler deploy
```

### One-time: match the dashboard Worker

You created a Worker for this in the Cloudflare dashboard. Open
[`wrangler.jsonc`](wrangler.jsonc) and set `"name"` to that Worker's **exact
name** so `wrangler deploy` updates it in place and moves the `landeck.pro/apps*`
routes onto it. (Or delete the dashboard Worker and keep `name: "nexus"`.)

`landeck.pro` must be an active zone in the same Cloudflare account for the
`routes` in `wrangler.jsonc` to attach.

## Add another app

1. Give the app a `build:embedded` script that builds with `--base=/apps/<slug>/`.
2. Add a `build_spa "<slug>" "<path/to/frontend>"` line to `scripts/build-apps.sh`.
3. Add the slug to `APPS` in `src/index.ts` (and an `/api/*` stub if it needs one).
