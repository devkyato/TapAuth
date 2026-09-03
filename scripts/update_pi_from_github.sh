#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
SERVICE_NAME="airhub.service"
GIT_BRANCH="${TAPAUTH_GIT_BRANCH:-main}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Copy .env.example to .env and fill it first."
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

DB_NAME="${AIRHUB_DB_NAME:-airhub_db}"
DB_USER="${AIRHUB_DB_USER:-}"
DB_PASSWORD="${AIRHUB_DB_PASSWORD:-}"
STORAGE="${AIRHUB_STORAGE:-sqlite}"

if [[ "$STORAGE" == "mysql" && ( -z "$DB_USER" || -z "$DB_PASSWORD" ) ]]; then
  echo "AIRHUB_DB_USER and AIRHUB_DB_PASSWORD are required in $ENV_FILE."
  exit 1
fi

cd "$PROJECT_DIR"

if [[ -x ".venv/bin/python" ]]; then
  .venv/bin/python scripts/backup_local_data.py || echo "Warning: pre-update backup failed; update will continue."
fi

git fetch origin "$GIT_BRANCH"
git checkout "$GIT_BRANCH"
git pull --ff-only origin "$GIT_BRANCH"

sudo timedatectl set-ntp true || true
sudo systemctl restart systemd-timesyncd || true
for _ in 1 2 3 4 5; do
  if timedatectl show -p NTPSynchronized --value 2>/dev/null | grep -q yes; then
    break
  fi
  sleep 2
done
if ! timedatectl show -p NTPSynchronized --value 2>/dev/null | grep -q yes; then
  echo "Warning: system clock is not NTP synchronized yet. Firebase may reject JWT auth until time sync completes."
fi

if [[ -d ".venv" ]]; then
  .venv/bin/pip install -r requirements.txt
else
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
fi

if [[ "$STORAGE" == "mysql" ]]; then
  .venv/bin/pip install -r requirements-mysql.txt
  sudo systemctl enable --now mariadb
  sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL
  MYSQL_PWD="$DB_PASSWORD" mysql -u "$DB_USER" "$DB_NAME" < schema.sql
fi
.venv/bin/python scripts/sync_local_registry.py || echo "Warning: registry reconciliation failed; the existing local NFC registry remains available."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
if [[ "${AIRHUB_SKIP_SERVICE_RESTART:-0}" != "1" ]]; then
  sudo systemctl restart "$SERVICE_NAME"
fi

if [[ "${AIRHUB_FIREBASE_ENABLED:-false}" == "true" ]]; then
  .venv/bin/python scripts/sync_realtime_db.py
fi

echo "Update complete. Service status: sudo systemctl status $SERVICE_NAME"
