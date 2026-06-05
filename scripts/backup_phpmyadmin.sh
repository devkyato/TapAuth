#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$PROJECT_DIR/backups/$STAMP-phpmyadmin-and-airhub"
mkdir -p "$BACKUP_DIR"

mysqldump -u root -p --single-transaction --routines --triggers --events airhub_db > "$BACKUP_DIR/airhub_db.sql"

if mysql -u root -p -N -B -e "SHOW DATABASES LIKE 'phpmyadmin';" | grep -q phpmyadmin; then
  mysqldump -u root -p --single-transaction phpmyadmin > "$BACKUP_DIR/phpmyadmin.sql"
fi

echo "Backup written to $BACKUP_DIR"