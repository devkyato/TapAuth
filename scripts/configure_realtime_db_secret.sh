#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
DATABASE_URL="${1:-https://airhub-login-default-rtdb.asia-southeast1.firebasedatabase.app/}"
DATABASE_SECRET="${2:-}"

if [[ -z "$DATABASE_SECRET" ]]; then
  echo "Usage: bash scripts/configure_realtime_db_secret.sh [database-url] <legacy-database-secret>"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
fi

set_env_value() {
  local key="$1"
  local value="$2"
  if grep -q "^$key=" "$ENV_FILE"; then
    sed -i "s|^$key=.*|$key=$value|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

set_env_value AIRHUB_FIREBASE_ENABLED true
set_env_value AIRHUB_FIREBASE_MODE realtime_db
set_env_value AIRHUB_FIREBASE_DATABASE_URL "${DATABASE_URL%/}"
set_env_value AIRHUB_FIREBASE_DATABASE_SECRET "$DATABASE_SECRET"

echo "Configured Realtime Database legacy-secret sync in $ENV_FILE."
echo "Restart the app, then run:"
echo "  source .venv/bin/activate"
echo "  python scripts/sync_firestore.py"
