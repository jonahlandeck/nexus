# Authentik — identity provider for landeck.pro

Self-hosted [Authentik](https://github.com/goauthentik/authentik) (MIT). Runs on
the VPS via Docker Compose, exposed to the internet only through a **bundled
Cloudflare Tunnel** — no inbound ports on the box. Every landeck.pro app
(nexus, meat-and-potatoes, future apps) is an OIDC client of this one instance.

```
authentik/
  docker-compose.yml        postgresql + server + worker + cloudflared
  .env.example              copy to .env, fill in
  blueprints/nexus.yaml     declarative: groups, OIDC clients, svc account, WebAuthn step-up
  mail/                     swappable email presets + use.sh switcher -> mail.env
                            (none / resend / smtp2go / gmail; see mail/README.md)
```

## 1. Create the tunnel

In the Cloudflare dashboard → **Zero Trust → Networks → Tunnels → Create a
tunnel** (choose *Cloudflared*). Then:

- **Public hostname:** `auth.landeck.pro` → service `http://server:9000`
  (`server` is the compose service name; the `cloudflared` container resolves it
  on the compose network).
- Copy the tunnel **token** into `.env` as `CLOUDFLARED_TOKEN`.

DNS for `auth.landeck.pro` is created automatically by the tunnel config.

## 2. Configure and start

```sh
cd authentik
cp .env.example .env

# generate secrets
sed -i "s#^PG_PASS=.*#PG_PASS=$(openssl rand -base64 36)#"            .env
sed -i "s#^AUTHENTIK_SECRET_KEY=.*#AUTHENTIK_SECRET_KEY=$(openssl rand -base64 60)#" .env
sed -i "s#^AUTHENTIK_BOOTSTRAP_PASSWORD=.*#AUTHENTIK_BOOTSTRAP_PASSWORD=$(openssl rand -base64 24)#" .env
sed -i "s#^AUTHENTIK_BOOTSTRAP_TOKEN=.*#AUTHENTIK_BOOTSTRAP_TOKEN=$(openssl rand -hex 32)#" .env
# then fill in by hand:  CLOUDFLARED_TOKEN  (from step 1).

# email — one swappable file (see mail/README.md). Current plan: Resend now,
# SMTP2GO once that account exists (`./mail/use.sh smtp2go`, then revoke the
# Resend key).
./mail/use.sh resend
$EDITOR mail.env                      # paste the Resend API key into __PASSWORD,
                                      # set __FROM once the domain is verified
#   ./mail/use.sh none   # alternative: skip email entirely for bootstrap

docker compose pull
docker compose up -d
docker compose logs -f worker      # watch the blueprint apply
```

Authentik comes up at `https://auth.landeck.pro/` (and `http://127.0.0.1:9000/`
on the box). First login is `akadmin` + `AUTHENTIK_BOOTSTRAP_PASSWORD`.

## 3. Verify the blueprint applied

In the admin UI (`/if/admin/`):

- **Directory → Groups:** `admins`, `beta-testers`, `nexus-service` exist.
- **Applications → Providers:** `nexus` and `meat-and-potatoes` OAuth2 providers;
  each lists the `nexus groups claim` scope mapping.
- **Directory → Users:** `svc-nexus` (service account), a member of
  `nexus-service`.
- **Directory → Tokens:** `nexus-api`, owned by `svc-nexus`.
- **Flows → default-authentication-flow → Stage Bindings:**
  `nexus-admins-webauthn-validate` is bound, with the `nexus-is-admin` policy on
  the binding.

## 4. Hand secrets to nexus

Copy these into **Cloudflare Secrets Store** (see
[`../apps/nexus/DEPLOY.md`](../apps/nexus/DEPLOY.md)):

| Secrets Store name | value |
|---|---|
| `nexus-client-secret` | `nexus` provider → **Client Secret** |
| `nexus-authentik-api-token` | `nexus-api` token → **key** (Directory → Tokens → nexus-api → copy key) |
| `nexus-auth-secret` | `openssl rand -base64 32` (fresh, unrelated to Authentik) |

The `akadmin` `AUTHENTIK_BOOTSTRAP_TOKEN` is **break-glass only** — it stays in
`.env` on this box and is never given to nexus or Cloudflare.

## 5. Add yourself to `admins` — but not `akadmin`

Enroll your own named account (via an enrollment flow or an invitation) and add
it to the `admins` group. On your next login Authentik will force WebAuthn /
passkey enrolment (the step-up policy).

**Do not add `akadmin` to `admins`.** The step-up policy is bound to that group;
keeping `akadmin` outside it preserves a working recovery path if you lose your
passkey device.

## Security checks before real users

Using the **`nexus-api` token** (scoped `svc-nexus`), not `akadmin`:

```sh
AK=https://auth.landeck.pro/api/v3
T='Authorization: Bearer <nexus-api key>'

# allowed
curl -s -o /dev/null -w '%{http_code}\n' -H "$T" "$AK/core/users/"      # 200
curl -s -o /dev/null -w '%{http_code}\n' -H "$T" "$AK/core/groups/"     # 200

# must be denied (403) — reach beyond user/group management
curl -s -o /dev/null -w '%{http_code}\n' -H "$T" "$AK/providers/oauth2/"   # 403
curl -s -o /dev/null -w '%{http_code}\n' -H "$T" "$AK/core/tokens/"        # 403

# must be denied — privilege escalation paths
#   * PATCH the nexus-admin-api role's permission set
#   * POST a new permission assignment to the nexus-service group
#   * add svc-nexus (or anyone) to a superuser group ("authentik Admins")
# each of these must return 403. If any succeeds, the permission set is too
# broad: narrow the role and, if Authentik can't scope it tightly enough,
# shrink what nexus /admin does rather than shipping the wide token.
```

## Upgrades

Bump `AUTHENTIK_TAG` in `.env`, then `docker compose pull && docker compose up -d`.
Re-check `blueprints/nexus.yaml` against the
[blueprint model reference](https://docs.goauthentik.io/customize/blueprints/v1/models/)
after a major version jump.
