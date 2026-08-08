import os
from pathlib import Path

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
    "version": "1.1.1",
    "environment": os.getenv("AIRHUB_ENV", "local"),
    "active_storage": os.getenv("AIRHUB_STORAGE", "mysql"),
    "firebase_ready": True,
    "debug": os.getenv("AIRHUB_DEBUG", "false").lower() == "true",
}

WIFI_CONFIG = {
    "ssid": os.getenv("AIRHUB_WIFI_SSID", ""),
    "password": os.getenv("AIRHUB_WIFI_PASSWORD", ""),
}

MYSQL_CONFIG = {
    "host": os.getenv("AIRHUB_DB_HOST", "localhost"),
    "user": os.getenv("AIRHUB_DB_USER", ""),
    "password": os.getenv("AIRHUB_DB_PASSWORD", ""),
    "database": os.getenv("AIRHUB_DB_NAME", "airhub_db"),
}

FIREBASE_CONFIG = {
    "enabled": os.getenv("AIRHUB_FIREBASE_ENABLED", "false").lower() == "true",
    "mode": os.getenv("AIRHUB_FIREBASE_MODE", "realtime_db"),
    "database_url": os.getenv("AIRHUB_FIREBASE_DATABASE_URL", ""),
    "database_secret": os.getenv("AIRHUB_FIREBASE_DATABASE_SECRET", ""),
    "project_id": os.getenv("AIRHUB_FIREBASE_PROJECT_ID", ""),
    "root": os.getenv("AIRHUB_FIREBASE_ROOT", "tapauth").strip("/") or "tapauth",
}
ACCESS_CONFIG = {
    "admin_code": os.getenv("TAPAUTH_ADMIN_CODE", os.getenv("AIRHUB_REGISTRATION_CODE", "")),
}
