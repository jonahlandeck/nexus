# nexus

The motherboard for **landeck.pro** — a personal site plus a growing set of
independently deployed apps.

## Layout

```
nexus/
  wrangler.jsonc      root site: assets-only Worker "nexus", route landeck.pro/*
  site/               static files it serves
    index.html          "hello I'm Jonah" + embedded HTMLGames DownhillSki
    ads.txt             HTMLGames ad-network entries (required for the game's ads)
  package.json        wrangler, for deploying the root site

  apps/
    meat-and-potatoes/   self-contained app: its own Cloudflare Python Worker
                         (FastAPI + D1), route landeck.pro/apps/meat-and-potatoes*
                         See apps/meat-and-potatoes/DEPLOY.md
    <next app>/          same pattern
```

## Model

- **One Worker per deploy unit.** The root site is one Worker; each app under
  `apps/<slug>/` is its own Worker with its own `wrangler.jsonc`, bindings, and
  deploy. Adding or shipping an app never touches the root or the other apps.
- **Routing by specificity.** The root site claims `landeck.pro/*`. Each app
  claims a more-specific route (`landeck.pro/apps/<slug>*`), which Cloudflare
  prefers for that path — so the Workers coexist on one zone.
- Everything an app needs lives under its own directory.

## Deploy the root site

```sh
npm install                          # needs Node >= 22
export CLOUDFLARE_API_TOKEN=...       # token from apps/meat-and-potatoes/.env
npx wrangler deploy                   # -> https://landeck.pro/
```

Local preview: `npx wrangler dev` → http://localhost:8787/

## Deploy an app

See that app's own `DEPLOY.md` (e.g.
[`apps/meat-and-potatoes/DEPLOY.md`](apps/meat-and-potatoes/DEPLOY.md)).
