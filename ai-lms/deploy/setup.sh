#!/bin/sh
# Writes ai-lms/deploy/.env with new random passwords and secrets.
# Run once before the first start:   sh ai-lms/deploy/setup.sh
# For a demo on a public server:     sh ai-lms/deploy/setup.sh --public-demo
set -eu

here=$(cd "$(dirname "$0")" && pwd)
env_file="$here/.env"

public_demo=false
case "${1:-}" in
  "") ;;
  --public-demo) public_demo=true ;;
  *) echo "Unknown option: $1 (the only option is --public-demo)" >&2; exit 2 ;;
esac

random_hex() {
  # $1 bytes of randomness from the operating system, as hexadecimal.
  od -An -N"$1" -tx1 /dev/urandom | tr -d ' \n'
}

if [ -e "$env_file" ]; then
  # A file from an earlier version may lack a newer setting: add it, change nothing else.
  if ! grep -q '^APP_DB_PASSWORD=' "$env_file"; then
    printf 'APP_DB_PASSWORD=%s\n' "$(random_hex 24)" >> "$env_file"
    echo "Added the new setting APP_DB_PASSWORD to $env_file; nothing else was changed."
    exit 0
  fi
  echo "$env_file already exists, so nothing was changed."
  echo "It holds the passwords for your existing data. To start again from nothing, see"
  echo "\"Wipe everything\" in ai-lms/docs/guide.md."
  exit 1
fi

if [ "$public_demo" = true ]; then
  access_code=$(random_hex 6)
  signup_open=false
else
  access_code=
  signup_open=true
fi

umask 077
cat > "$env_file" <<EOF
# Written by setup.sh. Keep this file private and never commit it.
# Deleting it does not delete your data, but the data cannot be opened without it.
POSTGRES_PASSWORD=$(random_hex 24)
APP_DB_PASSWORD=$(random_hex 24)
SECRET_KEY=$(random_hex 32)
OBJECTSTORE_ACCESS_KEY=ailms$(random_hex 8)
OBJECTSTORE_SECRET_KEY=$(random_hex 24)

# Demo mode: entry as the demo accounts without an email code (never for real students).
DEMO_MODE=true
PUBLIC_DEMO=$public_demo
DEMO_ACCESS_CODE=$access_code
SIGNUP_OPEN=$signup_open
EOF

echo "Wrote $env_file"
if [ "$public_demo" = true ]; then
  echo "Public demo access code: $access_code  (also kept in that file)"
fi
echo "Next: docker compose -p ailms -f ai-lms/deploy/compose.yaml up -d"
