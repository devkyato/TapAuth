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

    if status["database_secret_configured"] and status["realtime_database_target"]:
        print("Realtime Database legacy-secret sync is configured. Service-account JWT is not required for RTDB.")
    elif not status["admin_sdk_importable"]:
        raise SystemExit("firebase-admin is not importable. Run: .venv/bin/pip install -r requirements.txt")
    elif not status["credentials_file_exists"]:
        raise SystemExit("Service account JSON was not found at GOOGLE_APPLICATION_CREDENTIALS.")
    elif not status["credentials_private_key_present"]:
        raise SystemExit("Service account JSON is missing private_key. Download a new Firebase Admin SDK key.")

    users = get_all_users()
    logs = get_all_logs()
    result = sync_all(users[:1], logs[:1])
    print("Test sync result:", result)
    if not result.get("synced"):
        raise SystemExit(result.get("hint") or result.get("reason") or "Firebase test sync failed.")

    print("Firebase diagnostic passed.")


if __name__ == "__main__":
    main()
