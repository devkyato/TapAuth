import json
import urllib.request
from datetime import datetime, timezone

from config import SUPABASE_CONFIG, SYNC_CONFIG
import supabase_adapter


PRIVATE_FIELDS = {"nfc_code", "model_file_path"}


def configured_targets():
    targets = []
    if supabase_adapter.supabase_is_configured():
        targets.append({"name": "supabase", "kind": "supabase"})
    for index, target in enumerate(SYNC_CONFIG["webhook_targets"]):
        if isinstance(target, dict) and target.get("url"):
            targets.append({
                "name": target.get("name") or f"webhook-{index + 1}",
                "kind": "webhook",
                **target,
            })
    return targets


def target_by_name(name):
    return next((target for target in configured_targets() if target["name"] == name), None)


def _safe_record(record_type, record):
    payload = {key: value for key, value in record.items() if key not in PRIVATE_FIELDS}
    if record_type == "log":
        payload.pop("fullname", None)
        payload.pop("firstname", None)
        payload.pop("lastname", None)
    return payload


def _webhook_sync(target, record_type, record):
    body = json.dumps({
        "bucket_id": SYNC_CONFIG["bucket_id"],
        "source": SUPABASE_CONFIG["device_id"],
        "type": record_type,
        "record": _safe_record(record_type, record),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }, separators=(",", ":"), default=str).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "TapAuth-RaspberryPi/2.0"}
    if target.get("token"):
        headers["Authorization"] = f"Bearer {target['token']}"
    request = urllib.request.Request(target["url"], data=body, method="POST", headers=headers)
    with urllib.request.urlopen(request, timeout=int(target.get("timeout", 10))) as response:
        response.read()
    return {"synced": True, "target": target["name"]}


def sync_to_target(target, record_type, record):
    try:
        if target["kind"] == "supabase":
            writer = {
                "user": supabase_adapter.sync_user,
                "log": supabase_adapter.sync_log,
                "reservation": supabase_adapter.sync_reservation,
            }[record_type]
            return writer(record)
        return _webhook_sync(target, record_type, record)
    except Exception as exc:
        return {"synced": False, "target": target["name"], "reason": str(exc)}


def sync_to_all(record_type, record):
    targets = configured_targets()
    if not targets:
        return {"synced": False, "disabled": True, "results": []}
    results = [sync_to_target(target, record_type, record) for target in targets]
    return {
        "synced": all(result.get("synced") for result in results),
        "results": results,
        "failed": [result for result in results if not result.get("synced")],
    }
