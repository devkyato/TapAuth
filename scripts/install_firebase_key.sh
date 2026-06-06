#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
SOURCE_KEY="${1:-}"
DEST_KEY="$PROJECT_DIR/firebase-service-account.json"

if [[ -z "$SOURCE_KEY" || ! -f "$SOURCE_KEY" ]]; then
  echo "Usage: bash scripts/install_firebase_key.sh /path/to/service-account.json"
  exit 1
fi

cp "$SOURCE_KEY" "$DEST_KEY"
chmod 600 "$DEST_KEY"

if [[ -f "$ENV_FILE" ]]; then
  if grep -q '^GOOGLE_APPLICATION_CREDENTIALS=' "$ENV_FILE"; then
    sed -i "s|^GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=$DEST_KEY|" "$ENV_FILE"
  else
    printf '\nGOOGLE_APPLICATION_CREDENTIALS=%s\n' "$DEST_KEY" >> "$ENV_FILE"
  fi
  if grep -q '^AIRHUB_FIREBASE_DATABASE_URL=' "$ENV_FILE"; then
    sed -i 's|^AIRHUB_FIREBASE_DATABASE_URL=.*|AIRHUB_FIREBASE_DATABASE_URL=https://airhub-login-default-rtdb.asia-southeast1.firebasedatabase.app|' "$ENV_FILE"
  else
    printf '\nAIRHUB_FIREBASE_DATABASE_URL=https://airhub-login-default-rtdb.asia-southeast1.firebasedatabase.app\n' >> "$ENV_FILE"
  fi
fi

echo "Installed Firebase service account locally:"
echo "  $DEST_KEY"
echo "The key is intentionally ignored by Git."
