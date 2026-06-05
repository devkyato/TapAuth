from datetime import datetime, timezone

from config import FIREBASE_CONFIG

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    firebase_admin = None
    credentials = None
    db = None

_app_ready = False


def firebase_is_configured():
    return (
        FIREBASE_CONFIG["enabled"]
        and FIREBASE_CONFIG["mode"] == "realtime_db"
        and bool(FIREBASE_CONFIG["database_url"])
        and bool(FIREBASE_CONFIG["credentials_path"])
        and firebase_admin is not None
    )


def init_firebase():
    global _app_ready
    if _app_ready:
        return True
    if not firebase_is_configured():
        return False
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CONFIG["credentials_path"])
        firebase_admin.initialize_app(cred, {
            "databaseURL": FIREBASE_CONFIG["database_url"],
            "projectId": FIREBASE_CONFIG["project_id"],
        })
    _app_ready = True
    return True


def rtdb_safe(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return value


def public_log_payload(log_record):
    fullname = log_record.get("fullname") or "Guest"
    status = log_record.get("status") or "GUEST_PENDING"
    return {
        "local_id": log_record.get("id"),
        "fullname": fullname,
        "status": status,
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
        if not init_firebase() or not log_record:
            return {"synced": False, "reason": "Realtime Database is not enabled/configured."}
        doc_id = str(log_record.get("id"))
        db.reference(f"airhub/logs/{doc_id}").set(public_log_payload(log_record))
        return {"synced": True, "path": f"airhub/logs/{doc_id}", "id": doc_id}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}


def sync_user(user_record):
    try:
        if not init_firebase() or not user_record:
            return {"synced": False, "reason": "Realtime Database is not enabled/configured."}
        doc_id = str(user_record.get("id"))
        db.reference(f"airhub/users/{doc_id}").set(user_payload(user_record))
        return {"synced": True, "path": f"airhub/users/{doc_id}", "id": doc_id}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}


def sync_all(users, logs):
    try:
        if not init_firebase():
            return {"synced": False, "reason": "Realtime Database is not enabled/configured."}
        updates = {}
        for user in users:
            updates[f"airhub/users/{user.get('id')}"] = user_payload(user)
        for log in logs:
            updates[f"airhub/logs/{log.get('id')}"] = public_log_payload(log)
        if updates:
            db.reference("/").update(updates)
        return {"synced": True, "users": len(users), "logs": len(logs)}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}