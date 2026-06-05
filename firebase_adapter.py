from datetime import datetime, timezone

from config import FIREBASE_CONFIG

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    firebase_admin = None
    credentials = None
    firestore = None

_client = None


def firebase_is_configured():
    return (
        FIREBASE_CONFIG["enabled"]
        and FIREBASE_CONFIG["mode"] == "firestore"
        and bool(FIREBASE_CONFIG["credentials_path"])
        and bool(FIREBASE_CONFIG["project_id"])
        and firebase_admin is not None
    )


def get_client():
    global _client
    if _client is not None:
        return _client
    if not firebase_is_configured():
        return None

    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CONFIG["credentials_path"])
        firebase_admin.initialize_app(cred, {"projectId": FIREBASE_CONFIG["project_id"]})
    _client = firestore.client()
    return _client


def firestore_safe(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return value


def public_log_payload(log_record):
    fullname = log_record.get("fullname") or "Name required"
    status = log_record.get("status") or "GUEST"
    if status == "GUEST" and fullname.lower() == "guest":
        fullname = "Name required"

    return {
        "local_id": log_record.get("id"),
        "fullname": fullname,
        "status": status,
        "date_logged": firestore_safe(log_record.get("date_logged")),
        "source": "raspberry_pi",
        "updated_at": datetime.now(timezone.utc),
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
        "created_at": firestore_safe(user_record.get("created_at")),
        "updated_at": firestore_safe(user_record.get("updated_at")),
        "synced_at": datetime.now(timezone.utc),
    }


def sync_log(log_record):
    try:
        client = get_client()
        if client is None or not log_record:
            return {"synced": False, "reason": "Firestore is not enabled/configured."}

        doc_id = str(log_record.get("id"))
        client.collection("airhub_logs").document(doc_id).set(public_log_payload(log_record), merge=True)
        return {"synced": True, "collection": "airhub_logs", "id": doc_id}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}


def sync_user(user_record):
    try:
        client = get_client()
        if client is None or not user_record:
            return {"synced": False, "reason": "Firestore is not enabled/configured."}

        doc_id = str(user_record.get("id"))
        client.collection("airhub_users").document(doc_id).set(user_payload(user_record), merge=True)
        return {"synced": True, "collection": "airhub_users", "id": doc_id}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}


def sync_all(users, logs):
    try:
        client = get_client()
        if client is None:
            return {"synced": False, "reason": "Firestore is not enabled/configured."}

        user_count = 0
        log_count = 0
        batch = client.batch()
        pending = 0

        def flush_if_needed(force=False):
            nonlocal batch, pending
            if pending >= 400 or (force and pending):
                batch.commit()
                batch = client.batch()
                pending = 0

        for user in users:
            ref = client.collection("airhub_users").document(str(user.get("id")))
            batch.set(ref, user_payload(user), merge=True)
            user_count += 1
            pending += 1
            flush_if_needed()

        for log in logs:
            ref = client.collection("airhub_logs").document(str(log.get("id")))
            batch.set(ref, public_log_payload(log), merge=True)
            log_count += 1
            pending += 1
            flush_if_needed()

        flush_if_needed(force=True)
        return {"synced": True, "users": user_count, "logs": log_count}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}