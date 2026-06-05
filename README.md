# loginsys_airhub

APC Airhub NFC registration and logging system.

This folder contains the rebuilt NFC registration and logging system.

## Main Files

- `app.py`: Flask routes and scanner/database wiring
- `config.py`: local MySQL, Wi-Fi, and Firebase-ready placeholder config
- `database.py`: local MySQL/phpMyAdmin data access
- `scanner.py`: ACR122U NFC scanner handling
- `firebase_adapter.py`: future Firebase integration placeholder
- `schema.sql`: local MySQL schema for phpMyAdmin import
- `templates`: white themed registration and logs UI
- `static`: UI CSS and APC seal logo
- `scripts`: Raspberry Pi setup and database export helpers

Use this folder as the active system going forward.

## Environment

Copy `.env.example` to `.env` on each machine and fill in local values there. `.env` is ignored by Git and should not be uploaded.

## Raspberry Pi Setup

Run from this folder on the Raspberry Pi:

```bash
bash scripts/setup_raspberry_pi.sh
```

To export every table from the local `airhub_db` database into SQL and CSV-compatible copies:

```bash
bash scripts/export_database.sh
```

Exports are written to `exports/`.
