# Authentik email provider

Authentik's outbound email is controlled entirely by 8 `AUTHENTIK_EMAIL__*`
environment variables. They live in **one file, `authentik/mail.env`**
(gitignored), loaded by `docker-compose.yml` as an *optional* second
`env_file` on the `server` and `worker` services. Nothing else in the stack —
no blueprint object, no nexus var, no DNS record except provider-specific
SPF/DKIM — refers to the mail provider.

## The contract

Every preset in this directory defines the **same 8 keys**:

```
AUTHENTIK_EMAIL__HOST  __PORT  __USERNAME  __PASSWORD
AUTHENTIK_EMAIL__USE_TLS  __USE_SSL  __TIMEOUT  __FROM
```

Because a switch replaces the whole file, no key from the old provider can
survive one. That's the point.

## Switch provider

```sh
cd authentik
./mail/use.sh resend        # or: none | smtp2go | gmail
$EDITOR mail.env            # fill PASSWORD (+ USERNAME/FROM for gmail)
docker compose up -d        # recreates server+worker with the new env

# confirm exactly what's live (and that the old values are gone):
docker compose exec server env | grep AUTHENTIK_EMAIL
```

`use.sh` backs up the previous `mail.env` to `mail.env.bak` first.

Test delivery: **System → Settings → Email** in the admin UI, or trigger a
password reset for a test user and watch `docker compose logs -f worker`.

## Retiring a provider (do all of it)

Switching `mail.env` stops *using* the old credential. Retiring it means the
credential can no longer be used by anyone:

1. `./mail/use.sh <new-provider>` (or `none`), then `docker compose up -d` — the
   old env is gone from the running containers.
2. **Revoke the credential at its source** — this is the step that actually
   matters:
   - Gmail → Google account → App Passwords → delete that entry
   - Resend → API Keys → revoke the key
   - SMTP2GO → Sending → SMTP Users → delete that user
3. `rm mail.env.bak` (it still contains the old secret in plaintext).
4. If you ever pasted the secret into a shell, clear it from history.
5. If the retired provider had `landeck.pro` SPF/DKIM DNS records that a new
   provider doesn't need, remove them from Cloudflare DNS.

## Choosing

| preset | available | credential type | sender | notes |
|---|---|---|---|---|
| `none` | now | none | — | most secure; no sending credential on the box. Fine for bootstrap: set user passwords directly, invite via links. |
| `resend` | now | send-scoped API key, revocable on its own | `no-reply@landeck.pro` once domain verified | **current interim provider.** Could also just stay as the permanent choice. |
| `smtp2go` | ~3 days after domain registration | send-scoped SMTP user | `no-reply@landeck.pro` | the intended final provider — swap to it when the account exists, then revoke the Resend key. |
| `gmail` | now | App Password — sends as the whole account, bypasses 2FA, not send-scoped | that Gmail address | **use a dedicated throwaway Google account, never your personal one.** Last resort. |

Adding a different provider later: copy the 8-key contract into
`mail/<name>.env.example`, add `<name>` to the `case` in `use.sh`, done.
