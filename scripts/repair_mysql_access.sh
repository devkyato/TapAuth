#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
SERVICE_NAME="airhub.service"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Create it from .env.example first."
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

DB_NAME="${AIRHUB_DB_NAME:-airhub_db}"
DB_USER="${AIRHUB_DB_USER:-}"
DB_PASSWORD="${AIRHUB_DB_PASSWORD:-}"

if [[ -z "$DB_USER" || -z "$DB_PASSWORD" ]]; then
  echo "AIRHUB_DB_USER and AIRHUB_DB_PASSWORD are required in $ENV_FILE."
  exit 1
fi

if [[ "$DB_USER" == *"'"* || "$DB_PASSWORD" == *"'"* || "$DB_NAME" == *"'"* ]]; then
  echo "DB name, user, and password must not contain single quotes for this repair script."
  exit 1
fi

sudo systemctl enable --now mariadb

sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
ALTER USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL

MYSQL_PWD="$DB_PASSWORD" mysql -u "$DB_USER" "$DB_NAME" < "$PROJECT_DIR/schema.sql"

if systemctl list-unit-files | grep -q "^$SERVICE_NAME"; then
  sudo systemctl restart "$SERVICE_NAME"
fi

cat <<EOF
Database access repaired.
Database: $DB_NAME
User: $DB_USER

Check app:
  sudo systemctl status $SERVICE_NAME
  journalctl -u $SERVICE_NAME -f
EOF