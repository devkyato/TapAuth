from datetime import datetime, timezone

from config import FIREBASE_CONFIG

try:
    import firebase_admin
    from firebase_admin import credentials, db
    from firebase_admin import firestore
except ImportError:
    firebase_admin = None
    credentials = None
    db = None
    firestore = None

_app_ready = False
_firestore_client = None


def firebase_is_configured():
    return (
        FIREBASE_CONFIG["enabled"]
        and bool(FIREBASE_CONFIG["credentials_path"])
        and firebase_admin is not None
    )


def realtime_database_enabled():
    return (
        FIREBASE_CONFIG["mode"] in ("realtime_db", "both", "firestore_and_realtime_db")
        and bool(FIREBASE_CONFIG["database_url"])
        and db is not None
    )


def firestore_enabled():
    return (
        FIREBASE_CONFIG["mode"] in ("firestore", "both", "firestore_and_realtime_db", "realtime_db")
        and bool(FIREBASE_CONFIG["project_id"])
        and firestore is not None
    )


def init_firebase():
    global _app_ready
    if _app_ready:
        return True
    if not firebase_is_configured():
        return False
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_CONFIG["credentials_path"])
        options = {"projectId": FIREBASE_CONFIG["project_id"]}
        if FIREBASE_CONFIG["database_url"]:
            options["databaseURL"] = FIREBASE_CONFIG["database_url"]
        firebase_admin.initialize_app(cred, options)
    _app_ready = True
    return True


def get_firestore_client():
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = firestore.client()
    return _firestore_client


def firebase_status():
    return {
        "enabled": FIREBASE_CONFIG["enabled"],
        "mode": FIREBASE_CONFIG["mode"],
        "project_id_configured": bool(FIREBASE_CONFIG["project_id"]),
        "database_url_configured": bool(FIREBASE_CONFIG["database_url"]),
        "credentials_path_configured": bool(FIREBASE_CONFIG["credentials_path"]),
        "admin_sdk_importable": firebase_admin is not None,
        "realtime_database_target": realtime_database_enabled(),
        "firestore_target": firestore_enabled(),
    }


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
        if not init_firebase() or not log_record:
            return {"synced": False, "reason": "Firebase is not enabled/configured."}
        doc_id = str(log_record.get("id"))
        payload = public_log_payload(log_record)
        targets = []
        if realtime_database_enabled():
            db.reference(f"airhub/logs/{doc_id}").set(payload)
            targets.append(f"rtdb:airhub/logs/{doc_id}")
        if firestore_enabled():
            get_firestore_client().collection("airhub_logs").document(doc_id).set(payload)
            targets.append(f"firestore:airhub_logs/{doc_id}")
        if not targets:
            return {"synced": False, "reason": "No Firebase database target is enabled."}
        return {"synced": True, "paths": targets, "id": doc_id}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}


def sync_user(user_record):
    try:
        if not init_firebase() or not user_record:
            return {"synced": False, "reason": "Firebase is not enabled/configured."}
        doc_id = str(user_record.get("id"))
        payload = user_payload(user_record)
        targets = []
        if realtime_database_enabled():
            db.reference(f"airhub/users/{doc_id}").set(payload)
            targets.append(f"rtdb:airhub/users/{doc_id}")
        if firestore_enabled():
            get_firestore_client().collection("airhub_users").document(doc_id).set(payload)
            targets.append(f"firestore:airhub_users/{doc_id}")
        if not targets:
            return {"synced": False, "reason": "No Firebase database target is enabled."}
        return {"synced": True, "paths": targets, "id": doc_id}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}


def sync_all(users, logs):
    try:
        if not init_firebase():
            return {"synced": False, "reason": "Firebase is not enabled/configured."}
        targets = []
        if realtime_database_enabled():
            updates = {}
            for user in users:
                updates[f"airhub/users/{user.get('id')}"] = user_payload(user)
            for log in logs:
                updates[f"airhub/logs/{log.get('id')}"] = public_log_payload(log)
            if updates:
                db.reference("/").update(updates)
            targets.append("realtime_database")
        if firestore_enabled():
            client = get_firestore_client()
            batch = client.batch()
            batch_size = 0
            for user in users:
                ref = client.collection("airhub_users").document(str(user.get("id")))
                batch.set(ref, user_payload(user))
                batch_size += 1
                if batch_size == 450:
                    batch.commit()
                    batch = client.batch()
                    batch_size = 0
            for log in logs:
                ref = client.collection("airhub_logs").document(str(log.get("id")))
                batch.set(ref, public_log_payload(log))
                batch_size += 1
                if batch_size == 450:
                    batch.commit()
                    batch = client.batch()
                    batch_size = 0
            if batch_size:
                batch.commit()
            targets.append("firestore")
        if not targets:
            return {"synced": False, "reason": "No Firebase database target is enabled."}
        return {"synced": True, "users": len(users), "logs": len(logs), "targets": targets}
    except Exception as exc:
        return {"synced": False, "reason": str(exc)}
