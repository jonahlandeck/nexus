# nexus

The motherboard for **landeck.pro** — a personal site plus a growing set of
independently deployed apps.

## Layout

```
nexus/
  wrangler.jsonc      root site: assets-only Worker "nexus", route landeck.pro/*
  site/               static files it serves
    index.html          WebGL Milkdrop visualizer (Butterchurn): preset
                        cycling/shuffle, local-audio + mic input, fullscreen,
                        keyboard shortcuts
    vendor/butterchurn/  vendored Butterchurn lib + preset packs (base, MD1,
                        extra, extra2), MIT-licensed, loaded as plain <script>s
  package.json        wrangler, for deploying the root site
  pnpm-workspace.yaml  JS workspace: apps/nexus + packages/* (NOT meat-and-potatoes)

  packages/
    auth-config/         @nexus/auth — shared Auth.js (Authentik OIDC) config,
                         group helpers, app registry, Authentik REST client

  apps/
    nexus/               the account console at nexus.landeck.pro: Next.js on
                         Cloudflare Workers (OpenNext), Auth.js + D1.
                         /login /dashboard /admin.  See apps/nexus/DEPLOY.md
    meat-and-potatoes/   self-contained app: its own Cloudflare Python Worker
                         (FastAPI + D1), route landeck.pro/apps/meat-and-potatoes*
                         See apps/meat-and-potatoes/DEPLOY.md
    <next app>/          same pattern

  authentik/            self-hosted identity provider (Docker Compose on the VPS,
                        behind a Cloudflare Tunnel). See authentik/README.md
```

## Model

- **One Worker per deploy unit.** The root site is one Worker; each app under
  `apps/<slug>/` is its own Worker with its own `wrangler.jsonc`, bindings, and
  deploy. Adding or shipping an app never touches the root or the other apps.
- **Routing by specificity.** The root site claims `landeck.pro/*`. Each app
  claims a more-specific route (`landeck.pro/apps/<slug>*`), or its own
  subdomain (`nexus.landeck.pro/*`) — so the Workers coexist on one zone.
- Everything an app needs lives under its own directory.

## Accounts / SSO

One login across every landeck.pro app. **Authentik** is the identity provider,
self-hosted on the VPS (`authentik/`) and reachable only through a Cloudflare
Tunnel at `auth.landeck.pro`. Each app is a separate OIDC client of that one
instance — no app has its own username/password signup. `nexus.landeck.pro`
(`apps/nexus/`) is the console: sign-in, an app launcher, and `/admin` (gated by
the Authentik `admins` group, not a shared login) for managing users and group
access. "One login" comes from Authentik silently reauthorizing apps once a
session exists — not from shared cookies.

Start here: [`authentik/README.md`](authentik/README.md), then
[`apps/nexus/DEPLOY.md`](apps/nexus/DEPLOY.md).

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
