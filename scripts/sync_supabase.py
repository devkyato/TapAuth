#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import get_all_logs, get_all_users, get_reservations
from supabase_adapter import supabase_status, sync_log, sync_reservation, sync_user


def main():
    status = supabase_status()
    if not status["configured"]:
        raise SystemExit("Supabase is not configured. Run: python3 scripts/configure.py")
    summary = {"users": 0, "logs": 0, "reservations": 0, "failed": 0}
    for name, records, writer in (
        ("users", get_all_users(), sync_user),
        ("logs", get_all_logs(), sync_log),
        ("reservations", get_reservations(limit=100000), sync_reservation),
    ):
        for record in records:
            result = writer(record)
            if result.get("synced"):
                summary[name] += 1
            else:
                summary["failed"] += 1
                print(f"Failed {name} local id {record.get('id')}: {result.get('reason')}")
    print(f"Supabase sync complete: {summary}")
    if summary["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
