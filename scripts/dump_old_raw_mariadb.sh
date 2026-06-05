#!/usr/bin/env bash
set -euo pipefail

RAW_DATADIR="${1:-}"
OUT_SQL="${2:-$PWD/old_airhub_real_dump.sql}"
WORK_DIR="${3:-$PWD/old_mariadb_recovery_work}"
DB_NAME="${OLD_AIRHUB_DB_NAME:-airhub_db}"
SOCKET="$WORK_DIR/mariadb-recovery.sock"
PID_FILE="$WORK_DIR/mariadb-recovery.pid"
LOG_FILE="$WORK_DIR/mariadb-recovery.log"
PORT="${OLD_AIRHUB_RECOVERY_PORT:-33307}"

if [[ -z "$RAW_DATADIR" || ! -d "$RAW_DATADIR" ]]; then
  cat <<EOF
Usage:
  bash scripts/dump_old_raw_mariadb.sh /path/to/raw/mysql/datadir /path/to/old_airhub_real_dump.sql

Example:
  bash scripts/dump_old_raw_mariadb.sh /home/mako-airhub/old_sql_export/mysql_raw_from_E_var_var_lib_mysql /home/mako-airhub/old_airhub_real_dump.sql
EOF
  exit 1
fi

for cmd in mariadbd mariadb mariadb-admin mysqldump rsync; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd"
    echo "Install MariaDB tools first: sudo apt-get install -y mariadb-server mariadb-client rsync"
    exit 1
  fi
done

mkdir -p "$WORK_DIR"
rm -f "$SOCKET" "$PID_FILE" "$LOG_FILE"

RECOVERY_DATADIR="$WORK_DIR/datadir"
rm -rf "$RECOVERY_DATADIR"
mkdir -p "$RECOVERY_DATADIR"
rsync -a --delete "$RAW_DATADIR"/ "$RECOVERY_DATADIR"/

cleanup() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      mariadb-admin --protocol=socket --socket="$SOCKET" shutdown >/dev/null 2>&1 || kill "$pid" >/dev/null 2>&1 || true
    fi
  fi
}
trap cleanup EXIT

start_server() {
  local force_recovery="$1"
  rm -f "$SOCKET" "$PID_FILE"
  mariadbd \
    --datadir="$RECOVERY_DATADIR" \
    --socket="$SOCKET" \
    --pid-file="$PID_FILE" \
    --port="$PORT" \
    --skip-networking=0 \
    --bind-address=127.0.0.1 \
    --skip-grant-tables \
    --innodb-force-recovery="$force_recovery" \
    --log-error="$LOG_FILE" \
    --user="$(id -un)" &

  for _ in $(seq 1 60); do
    if [[ -S "$SOCKET" ]] && mariadb --protocol=socket --socket="$SOCKET" -e "SELECT 1" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

started=0
for recovery in 0 1 2 3 4 5 6; do
  echo "Trying MariaDB recovery mode $recovery..."
  if start_server "$recovery"; then
    started=1
    echo "Started old MariaDB datadir with innodb_force_recovery=$recovery"
    break
  fi
  cleanup
  sleep 1
done

if [[ "$started" != "1" ]]; then
  echo "Could not start the old MariaDB datadir. Last log:"
  tail -n 80 "$LOG_FILE" || true
  exit 1
fi

mkdir -p "$(dirname "$OUT_SQL")"
mysqldump \
  --protocol=socket \
  --socket="$SOCKET" \
  --single-transaction \
  --skip-lock-tables \
  --routines \
  --triggers \
  --events \
  "$DB_NAME" > "$OUT_SQL"

cat <<EOF
Old database dump complete:
  $OUT_SQL

Next import into the active Airhub DB:
  bash scripts/migrate_old_sql.sh $OUT_SQL

Then upload MySQL/phpMyAdmin data to Firestore:
  source .venv/bin/activate
  python scripts/sync_firestore.py
EOF