from database import (
    enqueue_firebase_sync,
    get_log_by_id,
    get_pending_firebase_sync,
    get_user_by_id,
    mark_firebase_sync_done,
    mark_firebase_sync_failed,
)
from firebase_adapter import sync_log, sync_user


def sync_or_queue(record_type, record):
    if not record:
        return {"synced": False, "queued": False, "reason": "Missing record."}
    result = sync_log(record) if record_type == "log" else sync_user(record)
    if result.get("synced"):
        return {**result, "queued": False}
    enqueue_firebase_sync(record_type, record.get("id"), result.get("reason"))
    return {**result, "queued": True}


def sync_log_or_queue(log_record):
    return sync_or_queue("log", log_record)


def sync_user_or_queue(user_record):
    return sync_or_queue("user", user_record)


def retry_pending(limit=100):
    summary = {"attempted": 0, "synced": 0, "failed": 0}
    for item in get_pending_firebase_sync(limit=limit):
        summary["attempted"] += 1
        if item["record_type"] == "user":
            record = get_user_by_id(item["record_id"])
            result = sync_user(record) if record else {"synced": False, "reason": "User not found."}
        else:
            record = get_log_by_id(item["record_id"])
            result = sync_log(record) if record else {"synced": False, "reason": "Log not found."}
        if result.get("synced"):
            mark_firebase_sync_done(item["id"])
            summary["synced"] += 1
        else:
            mark_firebase_sync_failed(item["id"], result.get("reason", "Sync failed."))
            summary["failed"] += 1
    return summary