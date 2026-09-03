import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = Path(os.getenv("TAPAUTH_SETTINGS_PATH", "") or ROOT / "data" / "settings.json")
try:
    LOCAL_SETTINGS = json.loads(SETTINGS_PATH.read_text(encoding="utf-8")) if SETTINGS_PATH.exists() else {}
except (OSError, json.JSONDecodeError):
    LOCAL_SETTINGS = {}


def setting(name, default=""):
    return os.getenv(name, LOCAL_SETTINGS.get(name, default))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).with_name(".env"))
else:
    env_path = Path(__file__).with_name(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

APP_CONFIG = {
    "name": "TapAuth",
    "version": "2.0.0",
    "environment": setting("AIRHUB_ENV", "local"),
    "active_storage": setting("AIRHUB_STORAGE", "sqlite").strip().lower(),
    "cloud_ready": True,
    "debug": str(setting("AIRHUB_DEBUG", "false")).lower() == "true",
}

WIFI_CONFIG = {
    "ssid": setting("AIRHUB_WIFI_SSID", ""),
    "password": setting("AIRHUB_WIFI_PASSWORD", ""),
}

MYSQL_CONFIG = {
    "host": setting("AIRHUB_DB_HOST", "localhost"),
    "user": setting("AIRHUB_DB_USER", ""),
    "password": setting("AIRHUB_DB_PASSWORD", ""),
    "database": setting("AIRHUB_DB_NAME", "airhub_db"),
}

SQLITE_CONFIG = {
    "path": str(setting("TAPAUTH_SQLITE_PATH", "")).strip()
    or str(Path(__file__).with_name("data") / "tapauth.db"),
}

FIREBASE_CONFIG = {
    "project_id": setting("AIRHUB_FIREBASE_PROJECT_ID", ""),
}
SUPABASE_CONFIG = {
    "enabled": str(setting("TAPAUTH_SUPABASE_ENABLED", "false")).lower() == "true",
    "url": str(setting("TAPAUTH_SUPABASE_URL", "")).rstrip("/"),
    "secret_key": setting("TAPAUTH_SUPABASE_SECRET_KEY", ""),
    "publishable_key": setting("TAPAUTH_SUPABASE_PUBLISHABLE_KEY", ""),
    "device_id": setting("TAPAUTH_DEVICE_ID", "airhub-pi"),
}
_webhooks = setting("TAPAUTH_WEBHOOK_TARGETS", [])
if isinstance(_webhooks, str):
    try:
        _webhooks = json.loads(_webhooks) if _webhooks.strip() else []
    except json.JSONDecodeError:
        _webhooks = []
SYNC_CONFIG = {
    "bucket_id": setting("TAPAUTH_BUCKET_ID", "airhub"),
    "webhook_targets": _webhooks if isinstance(_webhooks, list) else [],
}
ACCESS_CONFIG = {
    "admin_code": setting("TAPAUTH_ADMIN_CODE", setting("AIRHUB_REGISTRATION_CODE", "")),
}
