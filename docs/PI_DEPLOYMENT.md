# Raspberry Pi deployment

TapAuth 2.0 treats the Raspberry Pi as the complete working system. SQLite is local, Firebase is optional, and GitHub is only used when you deliberately update.

## Fresh installation

```bash
git clone https://github.com/devkyato/TapAuth.git
cd TapAuth
cp .env.example .env
nano .env
bash scripts/setup_raspberry_pi.sh
```

Keep these defaults:

```env
AIRHUB_STORAGE=sqlite
TAPAUTH_SQLITE_PATH=
TAPAUTH_REGISTRY_PATH=
AIRHUB_FIREBASE_ENABLED=false
```

Set a private `TAPAUTH_ADMIN_CODE`. Firebase can be enabled later without changing local behavior.

## Migrating an existing MySQL kiosk

Do this once before changing `AIRHUB_STORAGE`:

```bash
cd ~/TapAuth
git pull --ff-only origin main
source .venv/bin/activate
pip install -r requirements-mysql.txt
python scripts/backup_local_data.py
python scripts/migrate_mysql_to_sqlite.py
```

Then edit `.env`:

```env
AIRHUB_STORAGE=sqlite
```

Apply the simpler service and restart:

```bash
bash scripts/setup_raspberry_pi.sh
sudo systemctl restart airhub.service
curl http://127.0.0.1:5000/system_status
```

The status response should show `"driver":"sqlite"` and `"connected":true`.

## Normal updates

```bash
cd ~/TapAuth
bash scripts/update_pi_from_github.sh
```

The updater saves the SQLite database and card registry under `backups/<timestamp>/` before pulling code. It does not run during boot.

## Recovery

Check the service:

```bash
sudo systemctl status airhub.service
journalctl -u airhub.service -n 100 --no-pager
curl http://127.0.0.1:5000/system_status
```

Check the reader:

```bash
bash scripts/diagnose_nfc.sh
```

Create a manual backup:

```bash
source .venv/bin/activate
python scripts/backup_local_data.py
```

The important local files are `data/tapauth.db`, `data/registered_cards.json`, and `uploads/models/`. They are intentionally excluded from Git.
