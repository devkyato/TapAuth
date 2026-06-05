#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

DB_NAME="${AIRHUB_DB_NAME:-airhub_db}"
DB_USER="${AIRHUB_DB_USER:-root}"
DB_PASSWORD="${AIRHUB_DB_PASSWORD:-}"
EXPORT_DIR="$PROJECT_DIR/exports"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$EXPORT_DIR/$STAMP"
MYSQL_AUTH=(-u "$DB_USER")

if [[ -n "$DB_PASSWORD" ]]; then
  export MYSQL_PWD="$DB_PASSWORD"
fi

mkdir -p "$RUN_DIR/csv"

mysqldump --single-transaction --routines --triggers --events "${MYSQL_AUTH[@]}" "$DB_NAME" > "$RUN_DIR/${DB_NAME}.sql"

mysql "${MYSQL_AUTH[@]}" -N -B -e "SHOW FULL TABLES IN \`$DB_NAME\` WHERE Table_type = 'BASE TABLE';" |
while IFS=$'\t' read -r table _; do
  mysql "${MYSQL_AUTH[@]}" -B -e "SELECT * FROM \`$DB_NAME\`.\`$table\`;" > "$RUN_DIR/csv/${table}.tsv"
done

cat > "$RUN_DIR/README.txt" <<EOF
Database export created: $STAMP
Database: $DB_NAME

SQL dump:
${DB_NAME}.sql

CSV-compatible table copies:
csv/*.tsv
EOF

echo "Export complete: $RUN_DIR"