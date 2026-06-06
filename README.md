# loginsys_airhub

APC Airhub NFC tap-in/tap-out, registration, local MySQL, and Firebase Hosting system.

The Raspberry Pi is the source of truth for physical card taps. It records every tap into local MySQL/MariaDB for phpMyAdmin, then optionally syncs public-safe data to Firestore. Firebase Hosting reads Firestore and shows the live public tap-in/tap-out screen.

## Main Files

- `app.py`: Flask routes and NFC scanner wiring
- `database.py`: local MySQL/phpMyAdmin data access
- `firebase_adapter.py`: Raspberry Pi to Firestore sync
- `schema.sql`: local MySQL schema and public log view
- `templates/login.html`: local Raspberry Pi tap-in/tap-out kiosk
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


## GitHub CLI Raspberry Pi Flow

Fresh Pi clone/sync with GitHub CLI:

```bash
sudo apt-get update
sudo apt-get install -y gh
gh auth login
bash <(curl -fsSL https://raw.githubusercontent.com/devkyato/loginsys_airhub/main/scripts/bootstrap_from_github.sh)
```

If the repo is already on the Pi:

```bash
cd /home/mako-airhub/loginsys_airhub
bash scripts/update_pi_from_github.sh
```

That update script pulls `main`, installs Python requirements, creates/updates the MySQL database, applies `schema.sql`, restarts the auto-run service, and uploads MySQL data to Firestore when `AIRHUB_FIREBASE_ENABLED=true`.

## MySQL Database Setup

Create `.env` on the Raspberry Pi only:

```bash
cd /home/mako-airhub/loginsys_airhub
cp .env.example .env
nano .env
```

Set the new local database values there:

```env
AIRHUB_DB_NAME=airhub_db
AIRHUB_DB_USER=userigga
AIRHUB_DB_PASSWORD=<your_mysql_password>
```

Do not commit `.env`. The setup scripts create the database/user if they do not exist.

## Auto-Run On Power-On

`bash scripts/setup_raspberry_pi.sh` installs `airhub.service` as a systemd service:

```bash
sudo systemctl enable airhub.service
sudo systemctl restart airhub.service
sudo systemctl status airhub.service
```

That means the tap-in/tap-out app starts automatically whenever the Raspberry Pi powers on. Setup also creates a desktop autostart entry that opens Chromium in kiosk mode at `http://127.0.0.1:5000/`.

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

Short registration link for laptops/iPhones on the same Wi-Fi:

```text
http://<pi-ip>:5000/registration?code=<AIRHUB_REGISTRATION_CODE>
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

If Firebase prints `Invalid JWT Signature`, first sync the Raspberry Pi clock and then run the Firebase diagnostic:

```bash
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
timedatectl
source .venv/bin/activate
python scripts/diagnose_firebase.py
```

If the diagnostic still reports `Invalid JWT Signature` after NTP is synchronized, download a fresh Firebase Admin SDK service-account JSON from the `airhub-login` Firebase project and replace the file pointed to by `GOOGLE_APPLICATION_CREDENTIALS`.

Old registrations stay active because NFC matching still uses the local MySQL `users.nfc_code` field. Import old data before registering new cards so previously registered cards are recognized immediately by the kiosk.

## Firebase Hosting

The hosting app lives in `hosting/` and reads from Firestore collection `airhub_logs`. It does not show NFC codes.

Deploy hosting and Firestore rules. On Raspberry Pi, install Firebase CLI with npm, not pip:

```bash
sudo apt-get install -y nodejs npm
sudo npm install -g firebase-tools
firebase login --no-localhost
firebase deploy --only hosting,firestore:rules
```

Firestore public reads are allowed only for `airhub_logs`. Writes are blocked from the browser; the Raspberry Pi writes using the Firebase Admin service account.

## Local Backups

To export every table from local `airhub_db` into SQL and CSV-compatible copies:

```bash
bash scripts/export_database.sh
```

Exports are written to `exports/`.
## Where To View Data

Local Raspberry Pi kiosk:

```text
http://127.0.0.1:5000/
```

Hidden registration dashboard:

```text
http://127.0.0.1:5000/airhub-register?code=airhub123
http://127.0.0.1:5000/registration?code=airhub123
```

Local database/phpMyAdmin:

```text
http://127.0.0.1/phpmyadmin
```

Firebase Realtime Database:

```text
https://console.firebase.google.com/project/airhub-login/database/airhub-login-default-rtdb/data
```

Firebase Hosting deploy:

```bash
firebase deploy --only hosting,database
```

## Refresh After Pull

On the Raspberry Pi after pulling GitHub:

```bash
cd /home/mako-airhub/loginsys_airhub
git pull
bash scripts/update_pi_from_github.sh
sudo systemctl restart airhub.service
```

If NFC is not detected:

```bash
bash scripts/diagnose_nfc.sh
sudo systemctl stop pcscd
sudo systemctl disable pcscd
sudo systemctl restart airhub.service
```

## Old Data Recovery From E Drive

The original old MariaDB files were found at:

```text
E:\var\var\lib\mysql\airhub_db
```

Copy the raw folder made on the laptop to the Pi, then dump it:

```bash
bash scripts/dump_old_raw_mariadb.sh \
  /home/mako-airhub/old_sql_export/mysql_raw_from_E_var_var_lib_mysql \
  /home/mako-airhub/old_airhub_real_dump.sql
```

Merge into active MySQL/phpMyAdmin and upload to Realtime Database:

```bash
bash scripts/migrate_old_sql.sh /home/mako-airhub/old_airhub_real_dump.sql
source .venv/bin/activate
python scripts/sync_firestore.py
```
