# Deploying nexus (the account console)

Self-contained **Next.js Worker** built with the OpenNext Cloudflare adapter
(`@opennextjs/cloudflare`), Worker name `nexus-console`, serving
`https://nexus.landeck.pro`. All paths below are relative to `apps/nexus/` —
`cd` here first.

| Request | Handled by |
|---|---|
| `/api/auth/*` | Auth.js route handler (`app/api/auth/[...nextauth]/route.ts`) — OIDC flow to Authentik |
| `/`, `/login`, `/dashboard`, `/admin` | App Router pages (SSR in the Worker) |
| static assets | the `ASSETS` binding (`.open-next/assets`) |

Identity is **Authentik** (`auth.landeck.pro`, on the VPS — see
[`../../authentik/README.md`](../../authentik/README.md)). nexus is just an OIDC
client. Sessions are **JWT** (no per-request D1 read); the D1 database only holds
the Auth.js `users`/`accounts` tables and the `audit_log`.

## Toolchain

- **Node 22+** and **pnpm** (`corepack enable` or `npm i -g pnpm`). This app is
  part of the repo's pnpm workspace (`pnpm-workspace.yaml`); `apps/meat-and-potatoes`
  is not.
- `wrangler` (workspace dev dep). Run `wrangler login` yourself once.

## One-time setup

```sh
# from the repo root
pnpm install

cd apps/nexus

# 1. D1 database  — DONE: db "nexus" created,
#    database_id 9203437d-ac63-462e-9afd-e2491b72c805 is already in wrangler.jsonc.
#    Migrations still need applying:
pnpm exec wrangler d1 migrations apply nexus --remote
pnpm exec wrangler d1 migrations apply nexus --local

# 2. Cloudflare Secrets Store
#    DONE: store_id 9d1ea62f351840e890235f03bee12175 (the account's
#    default_secrets_store — free tier = 1 store/account) is already in
#    wrangler.jsonc. Only the VALUES remain. `--scopes workers` is required;
#    omit `--value` for a hidden prompt; `--remote` hits the real store.
STORE=9d1ea62f351840e890235f03bee12175
pnpm exec wrangler secrets-store secret create $STORE --name nexus-auth-secret         --scopes workers --remote   # paste: openssl rand -base64 32
pnpm exec wrangler secrets-store secret create $STORE --name nexus-client-secret       --scopes workers --remote   # paste: Authentik nexus provider Client Secret
pnpm exec wrangler secrets-store secret create $STORE --name nexus-authentik-api-token --scopes workers --remote   # paste: svc-nexus token key (NOT akadmin)

# 3. DNS: nothing to do. wrangler.jsonc uses `custom_domain: true`, so
#    `pnpm deploy` creates the nexus.landeck.pro DNS record + cert itself.
#    (First deploy may take a minute for the cert to go active.)

# 4. Authentik: the nexus OAuth2 provider + application, the groups scope
#    mapping, svc-nexus + its scoped token, and the admins step-up WebAuthn
#    flow are all created by authentik/blueprints/nexus.yaml. See that runbook.
#    The provider's redirect URI must be:
#      https://nexus.landeck.pro/api/auth/callback/authentik
```

## Local dev

```sh
cd apps/nexus
cp .dev.vars.example .dev.vars    # fill AUTH_SECRET + the two Authentik values
pnpm preview                      # opennextjs build + workerd -> http://localhost:8787/
#   `pnpm dev` (plain `next dev`) also works for UI iteration; `getCloudflareContext`
#   bindings come from wrangler.jsonc via initOpenNextCloudflareForDev().
```

Local sign-in still round-trips to the real `auth.landeck.pro`, so the
Authentik `nexus` provider needs `http://localhost:8787/api/auth/callback/authentik`
added as an allowed redirect URI while developing.

## Deploy

```sh
cd apps/nexus
pnpm deploy        # opennextjs-cloudflare build && opennextjs-cloudflare deploy
```

`landeck.pro` must be an active zone in the same account. The route
`nexus.landeck.pro/*` is a distinct subdomain from the root site's
`landeck.pro/*`, so the Workers coexist.

## Free-tier notes

- **Workers Free** 100k req/day; **D1 Free** 5 GB, 5M row-reads/day,
  100k row-writes/day. JWT sessions mean D1 is touched only on
  sign-in / account-link and admin actions — well inside these limits.
- **Secrets Store Free** allows roughly 20+ secrets per account; nexus uses 3.
- **Cloudflare Tunnel** (for Authentik) is free. Authentik / Postgres / Redis
  run on the VPS and are not Cloudflare-billed.
- No R2 incremental-cache binding — nexus has no ISR pages.

## Landmines

- **Do not enable D1 read replicas here** (`d1_databases[].experimental_remote`
  / the Sessions API with `session: "auto"` or `"primary-first"`). It is
  documented as incompatible with the `global_fetch_strictly_public`
  compatibility flag that this Worker sets: the combination silently blocks the
  Sessions API and hangs SSR with no logged error. If you ever need lower read
  latency on `users`/`accounts`, budget time to work around this rather than
  discovering it as a mystery hang.
- **`global_fetch_strictly_public` is required** (OpenNext) and also wanted:
  `auth.landeck.pro` is served only through the tunnel, so subrequests to it
  must loop through Cloudflare's front door, not a (nonexistent) zone origin.
- **`AUTHENTIK_API_TOKEN` must be the scoped `svc-nexus` token**, never the
  `akadmin` bootstrap token — `/admin` exposes this token's reach to any
  signed-in admin.
- There is deliberately **no `proxy.ts` / middleware**. Next 16 runs it as
  "Node.js middleware", which OpenNext flags experimental. Every protected page
  guards itself instead (`auth()` -> redirect, `isAdmin()` -> 404). Add one back
  only if you want an edge choke point and accept that warning.
