import json
import os
import shutil
import threading
from pathlib import Path

from nfc_utils import canonicalize_nfc_uid


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "registered_cards.json"
REGISTRY_PATH = Path(os.getenv("TAPAUTH_REGISTRY_PATH") or DEFAULT_REGISTRY_PATH)
REGISTRY_BACKUP_PATH = REGISTRY_PATH.with_suffix(".backup.json")
REGISTRY_LOCK = threading.RLock()
REGISTRY_FIELDS = (
    "id",
    "student_no",
    "lastname",
    "firstname",
    "middlename",
    "fullname",
    "course",
    "project_type",
    "room",
    "created_at",
)


def _empty_registry():
    return {"version": 1, "users": {}}


def _read_path(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("users"), dict):
        raise ValueError("Invalid TapAuth local registry.")
    return data


def _load_unlocked():
    for path in (REGISTRY_PATH, REGISTRY_BACKUP_PATH):
        try:
            if path.exists():
                return _read_path(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return _empty_registry()


def _write_unlocked(data):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = REGISTRY_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    try:
        os.chmod(temporary_path, 0o600)
    except OSError:
        pass
    if REGISTRY_PATH.exists():
        try:
            _read_path(REGISTRY_PATH)
            shutil.copy2(REGISTRY_PATH, REGISTRY_BACKUP_PATH)
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    os.replace(temporary_path, REGISTRY_PATH)


def local_user_payload(user, uid=None):
    canonical_uid = canonicalize_nfc_uid(uid or user.get("nfc_code"))
    if not canonical_uid:
        raise ValueError("A valid NFC UID is required for the local registry.")
    payload = {field: user.get(field) for field in REGISTRY_FIELDS}
    payload["nfc_code"] = canonical_uid
    return payload


def get_local_user(uid):
    canonical_uid = canonicalize_nfc_uid(uid)
    if not canonical_uid:
        return None
    with REGISTRY_LOCK:
        user = _load_unlocked()["users"].get(canonical_uid)
        return dict(user) if user else None


def save_local_user(user, uid=None):
    payload = local_user_payload(user, uid)
    with REGISTRY_LOCK:
        data = _load_unlocked()
        data["users"][payload["nfc_code"]] = payload
        _write_unlocked(data)
    return dict(payload)


def save_local_users(users):
    saved = 0
    with REGISTRY_LOCK:
        data = _load_unlocked()
        for user in users:
            try:
                payload = local_user_payload(user)
            except ValueError:
                continue
            data["users"][payload["nfc_code"]] = payload
            saved += 1
        if saved:
            _write_unlocked(data)
    return saved


def get_all_local_users():
    with REGISTRY_LOCK:
        return [dict(user) for user in _load_unlocked()["users"].values()]


def delete_local_user(uid):
    canonical_uid = canonicalize_nfc_uid(uid)
    if not canonical_uid:
        return False
    with REGISTRY_LOCK:
        data = _load_unlocked()
        removed = data["users"].pop(canonical_uid, None)
        if removed:
            _write_unlocked(data)
        return bool(removed)
