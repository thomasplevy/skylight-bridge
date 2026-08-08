#!/usr/bin/env bash
# Import secrets from the repo-root .env into the Fly app.
# Usage (from anywhere):
#   ./sync/set-fly-secrets.sh
#   ./sync/set-fly-secrets.sh /path/to/.env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${1:-$REPO_ROOT/.env}"
APP_NAME="${FLY_APP:-skylight-keep-sync}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

if ! command -v fly >/dev/null 2>&1; then
  echo "fly CLI not found on PATH" >&2
  exit 1
fi

# Strip comments/blank lines; require KEY=VALUE with a non-empty value.
# fly secrets import reads KEY=VALUE lines from stdin.
filtered="$(mktemp)"
trap 'rm -f "$filtered"' EXIT

grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE" \
  | grep -v -E '^[A-Za-z_][A-Za-z0-9_]*=\s*$' \
  > "$filtered"

if [[ ! -s "$filtered" ]]; then
  echo "No KEY=VALUE secrets found in $ENV_FILE" >&2
  exit 1
fi

echo "Importing $(wc -l < "$filtered") secrets from $ENV_FILE → app $APP_NAME"
fly secrets import --app "$APP_NAME" < "$filtered"
echo "Done."
