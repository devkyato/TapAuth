# TapAuth

![TapAuth repository cover](docs/assets/github-cover.png)

[![Quality checks](https://github.com/devkyato/TapAuth/actions/workflows/ci.yml/badge.svg)](https://github.com/devkyato/TapAuth/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/devkyato/TapAuth)](https://github.com/devkyato/TapAuth/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-ready-C51A4A.svg)](scripts/setup_raspberry_pi.sh)

TapAuth is my Raspberry Pi NFC attendance and reservation system for the Asia Pacific College School of Engineering AIRHub.

I started this as a straightforward tap-in and tap-out kiosk. Then I thought about what happens when the internet drops, a database service restarts, or a newly registered card is tapped again immediately. That changed the project: the Pi now owns the complete working database and the hosted side is optional.

## What it does

- Detects whether a registered NFC card should check in or check out.
- Lets an unknown card register through a short, tap-bound session.
- Stores students, attendance, reservations, and retry jobs in a local SQLite database.
- Supports 3D printing requests and teacher appointments.
- Shows the latest 25 activity records, with a compact **See more** view.
- Provides a private student and reservation management page.
- Mirrors safe activity data to Firebase without exposing NFC identifiers.
- Runs without a frontend build step: Flask, Python, HTML, CSS, and JavaScript.

## The part I wanted to get right

Oh! On card registration, saving a student once is not enough if the next lookup depends entirely on a database connection. TapAuth stores a private copy at `data/registered_cards.json` on the Pi. The write is atomic, a backup is kept, and the directory is ignored by Git.

The tap flow is:

```text
NFC card
   |
   v
Local card registry ---- recognized immediately
   |
   +---- SQLite ------------ students, logs, and reservations
   |
   +---- Firebase available? - copy approved private/public records
```

SQLite is the operational database and is built into Python, so the kiosk does not wait for a separate database service. The small card registry remains a second recognition fallback. Firebase is an optional remote copy and public-safe activity source. Existing MySQL installations can still opt into the legacy backend.

## Try the interface

The browser preview uses simulated taps and local browser storage:

```bash
python -m http.server 4173
```

Open `http://127.0.0.1:4173`.

For the real NFC flow, run the Flask application on a Raspberry Pi with an ACR122U reader.

## Install on a Raspberry Pi

You need Raspberry Pi OS, an ACR122U USB NFC reader, and internet access for the first installation. Firebase is optional.

```bash
git clone https://github.com/devkyato/TapAuth.git
cd TapAuth
cp .env.example .env
nano .env
bash scripts/setup_raspberry_pi.sh
```

The setup script installs Python dependencies, libnfc, reader permissions, the `airhub.service` systemd unit, and Chromium kiosk startup. It does not require MariaDB or internet access after installation.

After setup:

- Kiosk: `http://127.0.0.1:5000/`
- Student management: `http://127.0.0.1:5000/admin`
- System status: `http://127.0.0.1:5000/system_status`

## Configuration

Copy [.env.example](.env.example) to `.env`. At minimum, replace these values:

```env
AIRHUB_STORAGE=sqlite
TAPAUTH_SQLITE_PATH=
TAPAUTH_ADMIN_CODE=replace-with-a-private-admin-code
```

`TAPAUTH_SQLITE_PATH` may be left blank to use `data/tapauth.db`. `TAPAUTH_REGISTRY_PATH` may be left blank to use `data/registered_cards.json`.

To enable Firebase:

```env
AIRHUB_FIREBASE_ENABLED=true
AIRHUB_FIREBASE_MODE=realtime_db
AIRHUB_FIREBASE_DATABASE_URL=https://your-project-default-rtdb.region.firebasedatabase.app
AIRHUB_FIREBASE_DATABASE_SECRET=your-server-side-database-secret
AIRHUB_FIREBASE_PROJECT_ID=your-project-id
AIRHUB_FIREBASE_ROOT=tapauth
```

The Firebase browser `apiKey` identifies the web app; it is not an administrator secret. Never commit `.env`, database secrets, service-account files, student records, or NFC UIDs.

## Firebase copy

I treated Firebase as a synchronized view, not as a requirement for tapping a card. This keeps the kiosk usable on the local network even when cloud access is interrupted.

```bash
npm install -g firebase-tools
firebase login --no-localhost
firebase use your-project-id
firebase deploy --only database,hosting
```

To copy existing local records to Firebase:

```bash
source .venv/bin/activate
python scripts/sync_realtime_db.py
```

Private users and reservations live below `tapauth/users` and `tapauth/reservations`. Only sanitized event and timing fields under `tapauth/logs` are publicly readable.

## Update an installed Pi

```bash
cd ~/TapAuth
git pull --ff-only origin main
bash scripts/update_pi_from_github.sh
sudo systemctl restart airhub.service
sudo systemctl status airhub.service
```

The update script creates a timestamped SQLite and card-registry backup before changing code. Updates are manual by design, so a GitHub or internet outage cannot delay kiosk startup.

## Moving an existing Pi from MySQL

Read [docs/PI_DEPLOYMENT.md](docs/PI_DEPLOYMENT.md) before switching an installed kiosk. The one-time migration preserves students, logs, reservations, and pending Firebase jobs.

## If the reader is not responding

```bash
bash scripts/diagnose_nfc.sh
sudo systemctl restart airhub.service
journalctl -u airhub.service -f
```

TapAuth retries disconnected readers automatically. The setup disables `pcscd` because it can claim the ACR122U before libnfc.

## Project guide

| Path | Purpose |
| --- | --- |
| `app.py` | Flask API, tap sessions, registration, attendance, and admin routes |
| `scanner.py` | ACR122U reader loop and reconnection |
| `nfc_utils.py` | Stable UID normalization |
| `local_registry.py` | Durable card-recognition fallback |
| `sqlite_database.py` | Default Pi database for students, logs, reservations, and retry jobs |
| `database.py` | Storage selector and legacy MySQL backend |
| `firebase_adapter.py` | Firebase Realtime Database writer |
| `index.html`, `script.js` | Kiosk and reservation interface |
| `templates/admin.html` | Local management page |
| `hosting/` | Firebase-hosted public activity page |
| `scripts/` | Setup, update, sync, diagnostics, backup, and migration |
| `tests/` | Registration, privacy, UID, registry, and activity tests |

For a deeper technical reference, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Check everything

```bash
python -m compileall -q .
node --check script.js
node --check hosting/app.js
node --check hosting/firebase-config.js
python -m json.tool firebase.json
python -m json.tool database.rules.json
python -m unittest discover -s tests -v
```

## Contributing

This is a personal project, but focused issues and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md), use [SUPPORT.md](SUPPORT.md) for diagnostics, and report security problems privately through [SECURITY.md](SECURITY.md).

## License

TapAuth is available under the [MIT License](LICENSE).
