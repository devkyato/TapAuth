# loginsys_airhub

APC Airhub NFC tap-in, registration, local MySQL, and Firebase Hosting system.

The Raspberry Pi is the source of truth for physical card taps. It records every tap into local MySQL/MariaDB for phpMyAdmin, then optionally syncs public-safe data to Firestore. Firebase Hosting reads Firestore and shows the live public tap-in screen.

## Main Files

- `app.py`: Flask routes and NFC scanner wiring
- `database.py`: local MySQL/phpMyAdmin data access
- `firebase_adapter.py`: Raspberry Pi to Firestore sync
- `schema.sql`: local MySQL schema and public log view
- `templates/login.html`: local Raspberry Pi tap-in kiosk
- `templates/index.html`: hidden registration page at `/airhub-register`
- `hosting/`: Firebase Hosting public app backed by Firestore
- `scripts/setup_raspberry_pi.sh`: Raspberry Pi setup/service installer
- `scripts/migrate_old_sql.sh`: safe old SQL import into the active MySQL DB
- `scripts/sync_firestore.py`: full MySQL to Firestore backfill
- `scripts/export_database.sh`: SQL and CSV-compatible local exports

## Environment

Copy `.env.example` to `.env` on each machine and fill in local values there. `.env` is ignored by Git and should not be uploaded.

For Firestore sync on the Raspberry Pi, set:

```env
AIRHUB_FIREBASE_ENABLED=true
AIRHUB_FIREBASE_MODE=firestore
AIRHUB_FIREBASE_PROJECT_ID=airhub-login
GOOGLE_APPLICATION_CREDENTIALS=/home/mako-airhub/loginsys_airhub/firebase-service-account.json
```

The service account JSON must stay on the Raspberry Pi and must not be committed.

## Raspberry Pi Setup

Run from this folder on the Raspberry Pi:

```bash
bash scripts/setup_raspberry_pi.sh
```

After pulling updates, apply the current schema/view safely:

```bash
MYSQL_PWD="$AIRHUB_DB_PASSWORD" mysql -u "$AIRHUB_DB_USER" "$AIRHUB_DB_NAME" < schema.sql
sudo systemctl restart airhub.service
```

Hidden registration uses the Pi-local code:

```text
http://<pi-ip>:5000/airhub-register?code=<AIRHUB_REGISTRATION_CODE>
```

## Old Data

Import the old SQL without wiping current data:

```bash
bash scripts/migrate_old_sql.sh /path/to/old_airhub.sql
```

Then copy all current MySQL users/logs to Firestore:

```bash
source .venv/bin/activate
python scripts/sync_firestore.py
```

Old registrations stay active because NFC matching still uses the local MySQL `users.nfc_code` field.

## Firebase Hosting

The hosting app lives in `hosting/` and reads from Firestore collection `airhub_logs`. It does not show NFC codes.

Deploy hosting and Firestore rules:

```bash
firebase deploy --only hosting,firestore:rules
```

Firestore public reads are allowed only for `airhub_logs`. Writes are blocked from the browser; the Raspberry Pi writes using the Firebase Admin service account.

## Local Backups

To export every table from local `airhub_db` into SQL and CSV-compatible copies:

```bash
bash scripts/export_database.sh
```

Exports are written to `exports/`.