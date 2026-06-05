import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).with_name(".env"))

APP_CONFIG = {
    "name": "APC Airhub",
    "environment": os.getenv("AIRHUB_ENV", "local"),
    "active_storage": os.getenv("AIRHUB_STORAGE", "mysql"),
    "firebase_ready": True,
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
    "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
    "project_id": os.getenv("AIRHUB_FIREBASE_PROJECT_ID", ""),
}