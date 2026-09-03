# TapAuth

![TapAuth repository cover](docs/assets/github-cover.png)

[![Quality checks](https://github.com/devkyato/TapAuth/actions/workflows/ci.yml/badge.svg)](https://github.com/devkyato/TapAuth/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/devkyato/TapAuth)](https://github.com/devkyato/TapAuth/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-ready-C51A4A.svg)](scripts/setup_raspberry_pi.sh)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21853282.svg)](https://doi.org/10.5281/zenodo.21853282)

TapAuth is my Raspberry Pi NFC attendance and reservation system for the Asia Pacific College School of Engineering AIRHub. Version **1.1.3** is the current release: local-first card registration with durable offline recognition and optional MySQL/Firebase reconciliation. The name of a checkout folder does not define the product; this repository, application, and archive are **TapAuth**.

I started this as a straightforward tap-in and tap-out kiosk. Then I thought about what happens when the internet drops, MySQL restarts, or a newly registered card is tapped again immediately. That changed the project: the Pi now recognizes cards from its own durable registry first, keeps normal kiosk interactions fast, and reconciles data with MySQL and Firebase when those services are available.

## What it does

- Detects whether a registered NFC card should check in or check out.
- Lets an unknown card register through a short, tap-bound session.
- Keeps registered cards recognizable without depending on MySQL for every tap.
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
   +---- MySQL available? ---- sync student and attendance data
   |
   +---- Firebase available? - copy approved private/public records
```

MySQL remains the main operational database. The local registry is the recognition fallback, not a public student database. Firebase is an optional remote copy and public-safe activity source.

## Try the interface

The browser preview uses simulated taps and local browser storage:

```bash
python -m http.server 4173
```

Open `http://127.0.0.1:4173`.

The terminal output is the ordinary Python server log; a successful start includes:

```text
Serving HTTP on 0.0.0.0 port 4173 (http://0.0.0.0:4173/) ...
```

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

The setup script installs MariaDB, Python dependencies, libnfc, reader permissions, the `airhub.service` systemd unit, and Chromium kiosk startup.

After setup:

- Kiosk: `http://127.0.0.1:5000/`
- Student management: `http://127.0.0.1:5000/admin`
- System status: `http://127.0.0.1:5000/system_status`

## Configuration

Copy [.env.example](.env.example) to `.env`. At minimum, replace these values:

```env
AIRHUB_DB_USER=airhub_app
AIRHUB_DB_PASSWORD=replace-with-a-strong-password
AIRHUB_DB_NAME=airhub_db
TAPAUTH_ADMIN_CODE=replace-with-a-private-admin-code
```

`TAPAUTH_REGISTRY_PATH` may be left blank to use `data/registered_cards.json`.

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

To copy existing MySQL records:

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

The update script also reconciles MySQL students with the local card registry. If MySQL is temporarily unavailable, the existing local registry stays usable.

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
| `database.py` | MySQL students, logs, reservations, and sync queue |
| `firebase_adapter.py` | Firebase Realtime Database writer |
| `index.html`, `script.js` | Kiosk and reservation interface |
| `templates/admin.html` | Local management page |
| `hosting/` | Firebase-hosted public activity page |
| `scripts/` | Setup, update, sync, diagnostics, backup, and migration |
| `tests/` | Registration, privacy, UID, registry, and activity tests |

For a deeper technical reference, see [ARCHITECTURE.md](ARCHITECTURE.md).
For task-oriented setup, operations, security, and release notes, use the
[documentation index](docs/README.md).

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

## Limitations and deployment status

TapAuth is a personal, deployment-oriented Raspberry Pi application, not a
hosted service or a source package. Real NFC workflows require an ACR122U and
the permissions and services installed by the setup script. MySQL remains the
main operational database; the local registry only keeps card recognition
available, and Firebase is optional. Browser preview storage and simulated
taps do not reproduce hardware, service outages, or production data handling.
Keep backups and test updates on the target Pi.

## Citation

If you use this software in research or teaching, please cite the Zenodo archive / this repository:

```text
@dev.mako (devkyato). (2026). TapAuth: Raspberry Pi NFC attendance and reservation kiosk with local-first registration (Version 1.1.3).
```

See [CITATION.cff](CITATION.cff) for machine-readable metadata.

## Applications

- Attendance kiosks for schools and laboratories.
- Local-first NFC card registration and recognition.
- Maker-space equipment and appointment reservations.
- Raspberry Pi kiosk deployments with optional service reconciliation.

## Connected projects

| Project | Role |
| --- | --- |
| **[OpenNet](https://github.com/devkyato/OpenNet)** | Typed ONP/1 messaging for ESP32, Raspberry Pi, and backends |
| **[Datary](https://github.com/devkyato/Datary)** | Local-first laboratory for reproducible program and simulation evidence |
| **[Relay](https://github.com/devkyato/Relay)** | Timing-risk source review for control programs |
| **[Lowpack](https://github.com/devkyato/Lowpack)** | Local-first, application-aware lossless packing |
| **[Custom Arduino Libraries](https://github.com/devkyato/Custom-Arduino-Libraries)** | Non-blocking LED and digital-output patterns |
| **[Arduino Programs Guide](https://github.com/devkyato/Arduino-Programs-Guide)** | Safety-first, compile-checked Arduino Uno course |

## Security and contributing

This is a personal project, but focused issues and pull requests are welcome.
Source, configuration, NFC identifiers, and student data need different
handling: never commit `.env`, credentials, database exports, service-account
files, records, or UIDs. Please read [CONTRIBUTING.md](CONTRIBUTING.md), use
[SUPPORT.md](SUPPORT.md) for diagnostics, and report security problems
privately through [SECURITY.md](SECURITY.md).

## License

TapAuth is available under the [MIT License](LICENSE).
