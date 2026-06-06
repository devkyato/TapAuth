#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE_ROOT="$(cd "$PROJECT_DIR/.." && pwd)"
RAW_DATADIR="${1:-}"
OUT_SQL="${2:-$PROJECT_DIR/old_airhub_real_dump.sql}"

if [[ -z "$RAW_DATADIR" ]]; then
  for candidate in \
    "$WORKSPACE_ROOT/old_sql_export/mysql_raw_from_E_var_var_lib_mysql" \
    "$WORKSPACE_ROOT/old_mysql_raw_backup/mysql_raw_from_E_var_var_lib_mysql" \
    "$WORKSPACE_ROOT/old data/mysql_raw_from_E_var_var_lib_mysql" \
    "$PROJECT_DIR/../old_sql_export/mysql_raw_from_E_var_var_lib_mysql"; do
    if [[ -d "$candidate/airhub_db" && -f "$candidate/ibdata1" ]]; then
      RAW_DATADIR="$candidate"
      break
    fi
  done
fi

if [[ -z "$RAW_DATADIR" || ! -d "$RAW_DATADIR" ]]; then
  cat <<EOF
Could not find the old raw MariaDB datadir automatically.

Usage:
  bash scripts/recover_import_old_data.sh /path/to/mysql_raw_from_E_var_var_lib_mysql

Checked near:
  $WORKSPACE_ROOT
EOF
  exit 1
fi

echo "Using old raw MariaDB datadir:"
echo "  $RAW_DATADIR"

bash "$PROJECT_DIR/scripts/dump_old_raw_mariadb.sh" "$RAW_DATADIR" "$OUT_SQL" "$PROJECT_DIR/old_mariadb_recovery_work"
bash "$PROJECT_DIR/scripts/migrate_old_sql.sh" "$OUT_SQL"

if [[ -d "$PROJECT_DIR/.venv" ]]; then
  "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/sync_realtime_db.py" || true
else
  python3 "$PROJECT_DIR/scripts/sync_realtime_db.py" || true
fi

cat <<EOF
Old data recovery/import finished.

Dump:
  $OUT_SQL

Verify locally:
  http://127.0.0.1:5000/
  http://127.0.0.1/phpmyadmin
EOF
