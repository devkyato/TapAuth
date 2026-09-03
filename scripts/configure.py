#!/usr/bin/env python3
import getpass
import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "data" / "settings.json"
HOSTING_CONFIG = ROOT / "hosting" / "runtime-config.js"


def ask(label, current="", secret=False, required=False):
    suffix = " [configured]" if secret and current else (f" [{current}]" if current else "")
    while True:
        value = (getpass.getpass(f"{label}{suffix}: ") if secret else input(f"{label}{suffix}: ")).strip()
        if value:
            return value
        if current:
            return current
        if not required:
            return ""
        print("This value is required.")


def load_existing():
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def main():
    print("TapAuth setup\nThis creates private data/settings.json; no manual .env editing is required.\n")
    current = load_existing()
    admin_code = ask("Private admin code", current.get("TAPAUTH_ADMIN_CODE", ""), secret=True, required=True)
    device_id = ask("Device name", current.get("TAPAUTH_DEVICE_ID", "airhub-pi"), required=True)
    bucket_id = ask("Shared bucket/site name", current.get("TAPAUTH_BUCKET_ID", "airhub"), required=True)
    use_cloud = ask("Connect Supabase? (y/n)", "y" if current.get("TAPAUTH_SUPABASE_ENABLED") == "true" else "n").lower().startswith("y")

    settings = {
        **current,
        "AIRHUB_STORAGE": "sqlite",
        "TAPAUTH_ADMIN_CODE": admin_code,
        "TAPAUTH_DEVICE_ID": re.sub(r"[^a-zA-Z0-9_-]", "-", device_id),
        "TAPAUTH_BUCKET_ID": re.sub(r"[^a-zA-Z0-9_-]", "-", bucket_id),
        "TAPAUTH_SUPABASE_ENABLED": "true" if use_cloud else "false",
    }
    if use_cloud:
        settings["TAPAUTH_SUPABASE_URL"] = ask("Supabase project URL", current.get("TAPAUTH_SUPABASE_URL", ""), required=True).rstrip("/")
        settings["TAPAUTH_SUPABASE_SECRET_KEY"] = ask("Supabase secret key (Pi only)", current.get("TAPAUTH_SUPABASE_SECRET_KEY", ""), secret=True, required=True)
        settings["TAPAUTH_SUPABASE_PUBLISHABLE_KEY"] = ask("Supabase publishable key", current.get("TAPAUTH_SUPABASE_PUBLISHABLE_KEY", ""), required=True)
    webhook_url = ask("Additional custom webhook URL (optional)")
    if webhook_url:
        webhook_token = ask("Webhook bearer token (optional)", secret=True)
        settings["TAPAUTH_WEBHOOK_TARGETS"] = [{"name": "custom", "url": webhook_url, "token": webhook_token}]
    settings["AIRHUB_FIREBASE_PROJECT_ID"] = ask("Firebase Hosting project ID (optional)", current.get("AIRHUB_FIREBASE_PROJECT_ID", ""))

    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(SETTINGS_PATH, 0o600)
    except OSError:
        pass

    public_config = {
        "supabaseUrl": settings.get("TAPAUTH_SUPABASE_URL", ""),
        "supabasePublishableKey": settings.get("TAPAUTH_SUPABASE_PUBLISHABLE_KEY", ""),
        "deviceId": settings["TAPAUTH_DEVICE_ID"],
        "bucketId": settings["TAPAUTH_BUCKET_ID"],
    }
    HOSTING_CONFIG.write_text(
        "window.TAPAUTH_CLOUD_CONFIG = " + json.dumps(public_config, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"\nPrivate settings saved to {SETTINGS_PATH}")
    print(f"Browser-safe hosting settings saved to {HOSTING_CONFIG}")
    print("Neither file needs to be edited by hand. The private settings directory is ignored by Git.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(130)
