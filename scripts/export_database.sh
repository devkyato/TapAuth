#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${AIRHUB_DB_NAME:-airhub_db}"
DB_USER="${AIRHUB_DB_USER:-root}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPORT_DIR="$PROJECT_DIR/exports"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$EXPORT_DIR/$STAMP"

mkdir -p "$RUN_DIR/csv"

mysqldump --single-transaction --routines --triggers --events -u "$DB_USER" -p "$DB_NAME" > "$RUN_DIR/${DB_NAME}.sql"

mysql -u "$DB_USER" -p -N -B -e "SHOW FULL TABLES IN \`$DB_NAME\` WHERE Table_type = 'BASE TABLE';" |
while IFS=$'\t' read -r table _; do
  mysql -u "$DB_USER" -p -B -e "SELECT * FROM \`$DB_NAME\`.\`$table\`;" > "$RUN_DIR/csv/${table}.tsv"
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
