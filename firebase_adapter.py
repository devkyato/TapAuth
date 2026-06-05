from config import FIREBASE_CONFIG


def firebase_is_configured():
    return (
        FIREBASE_CONFIG["enabled"]
        and bool(FIREBASE_CONFIG["credentials_path"])
        and bool(FIREBASE_CONFIG["project_id"])
    )


def sync_log_placeholder(log_record):
    if not firebase_is_configured():
        return {"synced": False, "reason": "Firebase is configured as a future storage target."}

    return {"synced": False, "reason": "Firebase adapter is ready for implementation."}
