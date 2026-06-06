#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
OLD_SQL="${1:-}"

if [[ -z "$OLD_SQL" || ! -f "$OLD_SQL" ]]; then
  echo "Usage: bash scripts/migrate_old_sql.sh /path/to/airhub_db_old.sql"
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

DB_NAME="${AIRHUB_DB_NAME:-airhub_db}"
DB_USER="${AIRHUB_DB_USER:-root}"
DB_PASSWORD="${AIRHUB_DB_PASSWORD:-}"
LEGACY_DB="${DB_NAME}_legacy_import_$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$PROJECT_DIR/backups/$(date +%Y%m%d-%H%M%S)-before-old-import"
SANITIZED_SQL="$BACKUP_DIR/old_import_without_create_or_use.sql"
MYSQL_AUTH=(-u "$DB_USER")

if [[ -n "$DB_PASSWORD" ]]; then
  export MYSQL_PWD="$DB_PASSWORD"
fi

mkdir -p "$BACKUP_DIR"
mysqldump --single-transaction --routines --triggers --events "${MYSQL_AUTH[@]}" "$DB_NAME" > "$BACKUP_DIR/${DB_NAME}_before_import.sql"

mysql "${MYSQL_AUTH[@]}" -e "CREATE DATABASE \`$LEGACY_DB\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sed -E '/^(CREATE DATABASE|USE |\/\*!.*CREATE DATABASE|\/\*!.*USE )/Id' "$OLD_SQL" > "$SANITIZED_SQL"
mysql "${MYSQL_AUTH[@]}" "$LEGACY_DB" < "$SANITIZED_SQL"

mysql "${MYSQL_AUTH[@]}" <<SQL
ALTER TABLE \`$LEGACY_DB\`.users ADD COLUMN IF NOT EXISTS middlename VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE \`$LEGACY_DB\`.users ADD COLUMN IF NOT EXISTS fullname VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE \`$LEGACY_DB\`.users ADD COLUMN IF NOT EXISTS course VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE \`$LEGACY_DB\`.users ADD COLUMN IF NOT EXISTS project_type VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE \`$LEGACY_DB\`.users ADD COLUMN IF NOT EXISTS room VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE \`$LEGACY_DB\`.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE \`$LEGACY_DB\`.user_logs ADD COLUMN IF NOT EXISTS date_logged TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

INSERT INTO \`$DB_NAME\`.users
(student_no, lastname, firstname, middlename, fullname, course, project_type, room, nfc_code, created_at)
SELECT
  COALESCE(NULLIF(student_no, ''), CONCAT('OLD-', id)),
  COALESCE(lastname, ''),
  COALESCE(firstname, ''),
  COALESCE(middlename, ''),
  COALESCE(NULLIF(fullname, ''), TRIM(CONCAT(COALESCE(firstname, ''), ' ', COALESCE(middlename, ''), ' ', COALESCE(lastname, '')))),
  COALESCE(course, ''),
  COALESCE(project_type, ''),
  COALESCE(room, ''),
  nfc_code,
  COALESCE(created_at, CURRENT_TIMESTAMP)
FROM \`$LEGACY_DB\`.users
WHERE nfc_code IS NOT NULL AND nfc_code <> ''
ON DUPLICATE KEY UPDATE
  student_no=VALUES(student_no),
  lastname=VALUES(lastname),
  firstname=VALUES(firstname),
  middlename=VALUES(middlename),
  fullname=VALUES(fullname),
  course=VALUES(course),
  project_type=VALUES(project_type),
  room=VALUES(room);

INSERT INTO \`$DB_NAME\`.user_logs (nfc_code, date_logged)
SELECT l.nfc_code, l.date_logged
FROM \`$LEGACY_DB\`.user_logs l
WHERE l.nfc_code IS NOT NULL AND l.nfc_code <> ''
  AND NOT EXISTS (
    SELECT 1
    FROM \`$DB_NAME\`.user_logs existing
    WHERE existing.nfc_code = l.nfc_code
      AND existing.date_logged = l.date_logged
  );
SQL

mysql "${MYSQL_AUTH[@]}" -e "DROP DATABASE \`$LEGACY_DB\`;"

cat <<EOF
Old data migration complete.
Backup before import:
  $BACKUP_DIR/${DB_NAME}_before_import.sql

Merged:
  old users by nfc_code
  old logs by nfc_code + date_logged
EOF
