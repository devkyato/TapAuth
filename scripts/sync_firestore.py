#!/usr/bin/env python3
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from database import get_all_logs, get_all_users
from firebase_adapter import firebase_status, sync_all


def main():
    users = get_all_users()
    logs = get_all_logs()
    result = sync_all(users, logs)
    if not result.get("synced"):
        print(f"Firebase status: {firebase_status()}")
        raise SystemExit(result.get("reason", "Firebase sync failed."))
    targets = ", ".join(result.get("targets", ["firebase"]))
    print(f"Synced {result['users']} users and {result['logs']} logs to {targets}.")


if __name__ == "__main__":
    main()
