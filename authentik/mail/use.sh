#!/usr/bin/env bash
# Switch Authentik's email provider by replacing ../mail.env wholesale from a
# preset. A total replacement — no keys from the previous provider survive.
#
#   ./mail/use.sh none
#   ./mail/use.sh resend        # then edit mail.env, set the API key
#   ./mail/use.sh smtp2go
#   ./mail/use.sh gmail
#
# After switching:
#   docker compose up -d
#   docker compose exec server env | grep AUTHENTIK_EMAIL   # confirm what's live

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target="${here}/../mail.env"
name="${1:-}"
src="${here}/${name}.env.example"

case "$name" in
  gmail|resend|smtp2go|none) ;;
  *) echo "usage: mail/use.sh <gmail|resend|smtp2go|none>" >&2; exit 2 ;;
esac
[ -f "$src" ] || { echo "missing preset: $src" >&2; exit 2; }

if [ -f "$target" ]; then
  cp "$target" "${target}.bak"
  echo "existing mail.env backed up -> mail.env.bak"
fi
cp "$src" "$target"
echo "mail.env <- ${name} preset"

if [ "$name" != "none" ] && grep -qE '^AUTHENTIK_EMAIL__PASSWORD=[[:space:]]*(#.*)?$' "$target"; then
  echo "  next: edit mail.env and set AUTHENTIK_EMAIL__PASSWORD (and USERNAME/FROM for gmail)"
fi
echo "  then: docker compose up -d"
if [ "$name" = "none" ]; then
  echo "  retiring a real provider? also revoke its credential at the source"
  echo "  (Google App Password / Resend API key / SMTP2GO SMTP user)."
fi
