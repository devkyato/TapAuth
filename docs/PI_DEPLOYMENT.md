# Raspberry Pi deployment

TapAuth 2.0 treats the Raspberry Pi as the complete working system. SQLite is local, Supabase sharing is optional, Firebase only hosts the static public page, and GitHub is used when you deliberately update.

## Fresh installation

```bash
git clone https://github.com/devkyato/TapAuth.git
cd TapAuth
bash scripts/setup_raspberry_pi.sh
```

The setup script launches `scripts/configure.py` automatically on the first run. You can rerun it later without editing `.env`:

```bash
python3 scripts/configure.py
```

Private values live in `data/settings.json` with restricted permissions. The browser-safe Supabase URL and publishable key live in the ignored `hosting/runtime-config.js` file.

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

Then run `python3 scripts/configure.py`; it selects SQLite automatically.

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
