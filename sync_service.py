from database import (
    enqueue_cloud_sync,
    get_log_by_id,
    get_pending_cloud_sync,
    get_user_by_id,
    get_reservation_by_id,
    mark_cloud_sync_done,
    mark_cloud_sync_failed,
)
from cloud_targets import configured_targets, sync_to_all, sync_to_target, target_by_name


def sync_or_queue(record_type, record):
    if not record:
        return {"synced": False, "queued": False, "reason": "Missing record."}
    result = sync_to_all(record_type, record)
    if result.get("disabled"):
        return {**result, "queued": False, "reason": "No cloud targets are configured."}
    failures = result.get("failed", [])
    for failure in failures:
        enqueue_cloud_sync(
            failure.get("target", "unknown"),
            record_type,
            record.get("id"),
            failure.get("reason", "Sync failed"),
        )
    return {**result, "queued": bool(failures)}


def sync_log_or_queue(log_record):
    return sync_or_queue("log", log_record)


def sync_user_or_queue(user_record):
    return sync_or_queue("user", user_record)


def sync_reservation_or_queue(record):
    return sync_or_queue("reservation", record)


def retry_pending(limit=100):
    summary = {"attempted": 0, "synced": 0, "failed": 0}
    if not configured_targets():
        return {**summary, "disabled": True}
    for item in get_pending_cloud_sync(limit=limit):
        summary["attempted"] += 1
        target = target_by_name(item["target"])
        if not target:
            mark_cloud_sync_failed(item["id"], "Target is not configured.")
            summary["failed"] += 1
            continue
        if item["record_type"] == "user":
            record = get_user_by_id(item["record_id"])
            result = sync_to_target(target, "user", record) if record else {"synced": False, "reason": "User not found."}
        elif item["record_type"] == "reservation":
            record = get_reservation_by_id(item["record_id"])
            result = sync_to_target(target, "reservation", record) if record else {"synced": False, "reason": "Reservation not found."}
        else:
            record = get_log_by_id(item["record_id"])
            result = sync_to_target(target, "log", record) if record else {"synced": False, "reason": "Log not found."}
        if result.get("synced"):
            mark_cloud_sync_done(item["id"])
            summary["synced"] += 1
        else:
            mark_cloud_sync_failed(item["id"], result.get("reason") or "Sync failed.")
            summary["failed"] += 1
    return summary
