#!/usr/bin/env python3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from database import get_all_logs, get_all_users
from firebase_adapter import firebase_status, sync_all


def main():
    print("System UTC time:", datetime.now(timezone.utc).isoformat())
    status = firebase_status()
    print("Firebase status:")
    for key, value in status.items():
        print(f"  {key}: {value}")

    if not status["database_url_configured"]:
        raise SystemExit("AIRHUB_FIREBASE_DATABASE_URL is missing in .env.")
    if not status["database_secret_configured"]:
        raise SystemExit("AIRHUB_FIREBASE_DATABASE_SECRET is missing in .env.")
    if not status["realtime_database_target"]:
        raise SystemExit("Realtime Database sync is not configured. Check AIRHUB_FIREBASE_ENABLED and mode.")

    users = get_all_users()
    logs = get_all_logs()
    result = sync_all(users[:1], logs[:1])
    print("Test sync result:", result)
    if not result.get("synced"):
        raise SystemExit(result.get("hint") or result.get("reason") or "Firebase test sync failed.")

    print("Firebase diagnostic passed.")


if __name__ == "__main__":
    main()
