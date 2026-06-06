import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from config import FIREBASE_CONFIG


def firebase_is_configured():
    return (
        FIREBASE_CONFIG["enabled"]
        and FIREBASE_CONFIG["mode"] == "realtime_db"
        and bool(FIREBASE_CONFIG["database_url"])
        and bool(FIREBASE_CONFIG["database_secret"])
    )


def firebase_status():
    return {
        "enabled": FIREBASE_CONFIG["enabled"],
        "mode": FIREBASE_CONFIG["mode"],
        "project_id_configured": bool(FIREBASE_CONFIG["project_id"]),
        "database_url_configured": bool(FIREBASE_CONFIG["database_url"]),
        "database_secret_configured": bool(FIREBASE_CONFIG["database_secret"]),
        "realtime_database_target": firebase_is_configured(),
    }


def firebase_error_hint(error):
    message = str(error)
    if "401" in message or "Permission denied" in message:
        return "Realtime Database rejected the legacy database secret. Check AIRHUB_FIREBASE_DATABASE_SECRET in .env."
    if "404" in message:
        return "Realtime Database URL/path was not found. Check AIRHUB_FIREBASE_DATABASE_URL in .env."
    return None


def rtdb_safe(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return value


def rtdb_rest_url(path):
    base_url = FIREBASE_CONFIG["database_url"].rstrip("/")
    clean_path = path.strip("/")
    query = urllib.parse.urlencode({"auth": FIREBASE_CONFIG["database_secret"]})
    return f"{base_url}/{clean_path}.json?{query}"


def rtdb_request(path, payload, method, timeout):
    data = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    request = urllib.request.Request(
        rtdb_rest_url(path),
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Realtime Database REST error {exc.code}: {body}") from exc


def write_rtdb(path, payload):
    rtdb_request(path, payload, "PUT", timeout=10)


def update_rtdb(updates):
    rtdb_request("/", updates, "PATCH", timeout=20)


def public_log_payload(log_record):
    fullname = log_record.get("fullname") or "Guest"
    status = log_record.get("status") or "GUEST_PENDING"
    return {
        "local_id": log_record.get("id"),
        "fullname": fullname,
        "status": status,
        "tap_type": status if status in ("TAP_IN", "TAP_OUT") else None,
        "date_logged": rtdb_safe(log_record.get("date_logged")),
        "source": "raspberry_pi",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def user_payload(user_record):
    return {
        "local_id": user_record.get("id"),
        "student_no": user_record.get("student_no"),
        "lastname": user_record.get("lastname"),
        "firstname": user_record.get("firstname"),
        "middlename": user_record.get("middlename"),
        "fullname": user_record.get("fullname"),
        "course": user_record.get("course"),
        "project_type": user_record.get("project_type"),
        "room": user_record.get("room"),
        "created_at": rtdb_safe(user_record.get("created_at")),
        "updated_at": rtdb_safe(user_record.get("updated_at")),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


def sync_log(log_record):
    try:
        if not firebase_is_configured() or not log_record:
            return {"synced": False, "reason": "Realtime Database is not enabled/configured."}
        doc_id = str(log_record.get("id"))
        write_rtdb(f"airhub/logs/{doc_id}", public_log_payload(log_record))
        return {"synced": True, "paths": [f"rtdb:airhub/logs/{doc_id}"], "id": doc_id}
    except Exception as exc:
        return {"synced": False, "reason": str(exc), "hint": firebase_error_hint(exc)}


def sync_user(user_record):
    try:
        if not firebase_is_configured() or not user_record:
            return {"synced": False, "reason": "Realtime Database is not enabled/configured."}
        doc_id = str(user_record.get("id"))
        write_rtdb(f"airhub/users/{doc_id}", user_payload(user_record))
        return {"synced": True, "paths": [f"rtdb:airhub/users/{doc_id}"], "id": doc_id}
    except Exception as exc:
        return {"synced": False, "reason": str(exc), "hint": firebase_error_hint(exc)}


def sync_all(users, logs):
    try:
        if not firebase_is_configured():
            return {"synced": False, "reason": "Realtime Database is not enabled/configured."}
        updates = {}
        for user in users:
            updates[f"airhub/users/{user.get('id')}"] = user_payload(user)
        for log in logs:
            updates[f"airhub/logs/{log.get('id')}"] = public_log_payload(log)
        if updates:
            update_rtdb(updates)
        return {"synced": True, "users": len(users), "logs": len(logs), "targets": ["realtime_database"]}
    except Exception as exc:
        return {"synced": False, "reason": str(exc), "hint": firebase_error_hint(exc)}
