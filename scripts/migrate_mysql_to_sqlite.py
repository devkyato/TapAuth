#!/usr/bin/env python3
"""One-time importer for an existing TapAuth MySQL installation."""

import sys
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import MYSQL_CONFIG
import sqlite_database as sqlite


def fetch_all(connection, query):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()


def main():
    source = mysql.connector.connect(**MYSQL_CONFIG)
    imported = {"users": 0, "logs": 0, "reservations": 0, "sync_queue": 0}
    try:
        users = fetch_all(source, "SELECT * FROM users ORDER BY id")
        logs = fetch_all(source, "SELECT * FROM user_logs ORDER BY id")
        reservations = fetch_all(source, "SELECT * FROM reservations ORDER BY id")
        try:
            sync_items = fetch_all(source, "SELECT * FROM firebase_sync_queue ORDER BY id")
        except Exception:
            sync_items = []

        with sqlite._connect() as target:
            for user in users:
                target.execute("""
                    INSERT INTO users(id,student_no,lastname,firstname,middlename,fullname,course,
                      project_type,room,nfc_code,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(nfc_code) DO UPDATE SET student_no=excluded.student_no,
                      lastname=excluded.lastname,firstname=excluded.firstname,
                      middlename=excluded.middlename,fullname=excluded.fullname,
                      course=excluded.course,project_type=excluded.project_type,room=excluded.room
                """, tuple(str(user.get(key) or "") for key in sqlite.USER_COLUMNS))
                imported["users"] += 1

            for log in logs:
                target.execute(
                    "INSERT OR IGNORE INTO user_logs(id,nfc_code,date_logged) VALUES(?,?,?)",
                    (log["id"], str(log.get("nfc_code") or ""), str(log.get("date_logged") or "")),
                )
                imported["logs"] += 1

            for item in reservations:
                values = []
                for key in sqlite.RESERVATION_COLUMNS:
                    value = item.get(key)
                    values.append(None if value is None else str(value))
                target.execute(
                    f"INSERT OR IGNORE INTO reservations({','.join(sqlite.RESERVATION_COLUMNS)}) "
                    f"VALUES({','.join('?' for _ in sqlite.RESERVATION_COLUMNS)})",
                    values,
                )
                imported["reservations"] += 1

            for item in sync_items:
                target.execute("""
                    INSERT OR IGNORE INTO cloud_sync_queue
                      (target,record_type,record_id,attempts,last_error,created_at,updated_at,synced_at)
                    VALUES(?,?,?,?,?,?,?,?)
                """, ("supabase",) + tuple(item.get(key) for key in (
                    "record_type", "record_id", "attempts", "last_error",
                    "created_at", "updated_at", "synced_at",
                )))
                imported["sync_queue"] += 1
    finally:
        source.close()

    print(f"MySQL migration complete: {imported}")
    print(f"SQLite database: {sqlite.DB_PATH}")


if __name__ == "__main__":
    main()
