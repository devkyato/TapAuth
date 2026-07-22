#!/usr/bin/env python3
import sys
import os
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from config import MYSQL_CONFIG
from database import get_all_logs, get_all_users, get_reservations
from firebase_adapter import firebase_status, sync_all


def apply_schema():
    password = MYSQL_CONFIG.get("password") or ""
    env = os.environ.copy()
    if password:
        env["MYSQL_PWD"] = password
    subprocess.run(
        [
            "mysql",
            "-h",
            MYSQL_CONFIG.get("host") or "localhost",
            "-u",
            MYSQL_CONFIG.get("user") or "root",
            MYSQL_CONFIG.get("database") or "airhub_db",
        ],
        input=(PROJECT_DIR / "schema.sql").read_text(),
        text=True,
        env=env,
        check=True,
    )


def main():
    apply_schema()
    users = get_all_users()
    logs = get_all_logs()
    reservations = get_reservations(limit=100000)
    result = sync_all(users, logs, reservations)
    if not result.get("synced"):
        print(f"Firebase status: {firebase_status()}")
        raise SystemExit(result.get("hint") or result.get("reason", "Realtime Database sync failed."))
    print(
        f"Synced {result['users']} users, {result['logs']} logs, and "
        f"{result['reservations']} reservations to Realtime Database."
    )


if __name__ == "__main__":
    main()
