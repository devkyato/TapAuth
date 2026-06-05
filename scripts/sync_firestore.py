#!/usr/bin/env python3
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from database import get_all_logs, get_all_users
from firebase_adapter import sync_all


def main():
    users = get_all_users()
    logs = get_all_logs()
    result = sync_all(users, logs)
    if not result.get("synced"):
        raise SystemExit(result.get("reason", "Firestore sync failed."))
    print(f"Synced {result['users']} users and {result['logs']} logs to Firestore.")


if __name__ == "__main__":
    main()