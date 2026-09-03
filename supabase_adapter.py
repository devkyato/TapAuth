import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from config import SUPABASE_CONFIG, SYNC_CONFIG


def supabase_is_configured():
    return bool(
        SUPABASE_CONFIG["enabled"]
        and SUPABASE_CONFIG["url"]
        and SUPABASE_CONFIG["secret_key"]
        and SUPABASE_CONFIG["device_id"]
    )


def supabase_status():
    return {
        "enabled": SUPABASE_CONFIG["enabled"],
        "configured": supabase_is_configured(),
        "url_configured": bool(SUPABASE_CONFIG["url"]),
        "secret_key_configured": bool(SUPABASE_CONFIG["secret_key"]),
        "publishable_key_configured": bool(SUPABASE_CONFIG["publishable_key"]),
        "device_id": SUPABASE_CONFIG["device_id"],
    }


def _request(table, payload=None, method="POST", query=None, timeout=10):
    base = SUPABASE_CONFIG["url"]
    url = f"{base}/rest/v1/{table}"
    if query:
        url += "?" + urllib.parse.urlencode(query, safe=",")
    key = SUPABASE_CONFIG["secret_key"]
    data = None if payload is None else json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
        "User-Agent": "TapAuth-RaspberryPi/2.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase REST error {exc.code}: {body}") from exc


def _base(record):
    return {
        "bucket_id": SYNC_CONFIG["bucket_id"],
        "device_id": SUPABASE_CONFIG["device_id"],
        "local_id": record.get("id"),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


def _upsert(table, payload):
    _request(table, payload, query={"on_conflict": "bucket_id,device_id,local_id"})
    return {"synced": True, "target": f"supabase:{table}", "id": payload.get("local_id")}


def sync_user(record):
    if not supabase_is_configured():
        return {"synced": False, "disabled": True, "reason": "Supabase sync is disabled."}
    if not record:
        return {"synced": False, "reason": "Missing user."}
    try:
        return _upsert("tapauth_students", {
            **_base(record),
            "student_no": record.get("student_no"),
            "lastname": record.get("lastname"),
            "firstname": record.get("firstname"),
            "middlename": record.get("middlename"),
            "fullname": record.get("fullname"),
            "course": record.get("course"),
            "project_type": record.get("project_type"),
            "room": record.get("room"),
            "created_at": record.get("created_at"),
        })
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}


def sync_log(record):
    if not supabase_is_configured():
        return {"synced": False, "disabled": True, "reason": "Supabase sync is disabled."}
    if not record:
        return {"synced": False, "reason": "Missing attendance record."}
    private = {
        **_base(record),
        "student_no": record.get("student_no"),
        "status": record.get("status"),
        "event_type": record.get("event_type"),
        "date_logged": record.get("date_logged"),
        "time_entered": record.get("time_entered"),
        "time_left": record.get("time_left"),
        "duration_seconds": record.get("duration_seconds"),
        "duration_label": record.get("duration_label"),
    }
    public = {key: value for key, value in private.items() if key != "student_no"}
    try:
        _upsert("tapauth_attendance", private)
        _upsert("tapauth_public_activity", public)
        return {"synced": True, "targets": ["supabase:tapauth_attendance", "supabase:tapauth_public_activity"]}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}


def sync_reservation(record):
    if not supabase_is_configured():
        return {"synced": False, "disabled": True, "reason": "Supabase sync is disabled."}
    if not record:
        return {"synced": False, "reason": "Missing reservation."}
    try:
        return _upsert("tapauth_reservations", {
            **_base(record),
            **{key: record.get(key) for key in (
                "service", "fullname", "student_no", "course", "reservation_date",
                "schedule_time", "duration_minutes", "queue_position", "teacher_name",
                "project_name", "purpose", "notes", "model_file_name", "status",
                "created_at", "updated_at",
            )},
        })
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}


def delete_user(user_id):
    if not supabase_is_configured():
        return {"synced": False, "disabled": True, "reason": "Supabase sync is disabled."}
    try:
        _request(
            "tapauth_students",
            method="DELETE",
            query={"bucket_id": f"eq.{SYNC_CONFIG['bucket_id']}", "device_id": f"eq.{SUPABASE_CONFIG['device_id']}", "local_id": f"eq.{int(user_id)}"},
        )
        return {"synced": True}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}
