# nexus-console

`nexus.landeck.pro` — one sign-in, an app launcher, and the admin console for
landeck.pro apps.

- **`/`** — no content. Redirects to `/dashboard` (session) or `/login`.
- **`/login`** — kicks off the Auth.js OIDC flow to Authentik. Authentik renders
  the real login/signup UI on `auth.landeck.pro`.
- **`/dashboard`** — launcher showing only the apps the user can access
  (`accessibleApps()` from `@nexus/auth`).
- **`/admin`** — gated by the `admins` Authentik group (a claim check, not a
  separate login). Calls the Authentik REST API via the scoped `svc-nexus`
  token to manage group membership. Every action writes an `audit_log` row.

## Stack

Next.js (App Router) → Cloudflare Workers via `@opennextjs/cloudflare`.
Auth.js v5 with the built-in Authentik provider and the `@auth/d1-adapter`
(JWT sessions; D1 persists users/accounts + the audit log). Shared identity
code lives in [`../../packages/auth-config`](../../packages/auth-config)
(`@nexus/auth`).

Setup, secrets, and deploy: [`DEPLOY.md`](./DEPLOY.md).
