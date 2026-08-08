# Getting started with TapAuth

I use this path for a fresh Raspberry Pi deployment because it keeps the
hardware, private configuration, and service checks visible.

## Requirements

- Raspberry Pi OS and an ACR122U USB NFC reader.
- Internet access for the first setup.
- A private MySQL application account.
- Firebase credentials only when the optional synchronized copy is enabled.

The folder containing a clone can have any local name. The product and service
documented here are TapAuth.

## Install

```bash
git clone https://github.com/devkyato/TapAuth.git
cd TapAuth
cp .env.example .env
nano .env
bash scripts/setup_raspberry_pi.sh
```

Set at least `AIRHUB_DB_USER`, `AIRHUB_DB_PASSWORD`, `AIRHUB_DB_NAME`, and
`TAPAUTH_ADMIN_CODE` before setup. Never commit the resulting `.env`.

The script installs MariaDB, Python dependencies, libnfc and reader
permissions, the `airhub.service` systemd unit, and Chromium kiosk startup.
TapAuth is an application deployment; this repository does not claim to
publish an installable Python source package.

## Check the deployment

```bash
sudo systemctl status airhub.service
journalctl -u airhub.service -n 50 --no-pager
```

A running service exposes:

- kiosk: `http://127.0.0.1:5000/`
- student management: `http://127.0.0.1:5000/admin`
- system status: `http://127.0.0.1:5000/system_status`

Register a test card, tap it again, and confirm it remains recognizable. The
private local registry is stored at `data/registered_cards.json` by default;
MySQL remains the main operational database.

## Update an installed Pi

```bash
cd ~/TapAuth
git pull --ff-only origin main
bash scripts/update_pi_from_github.sh
sudo systemctl restart airhub.service
sudo systemctl status airhub.service
```

If the reader is unavailable, run `bash scripts/diagnose_nfc.sh` and inspect
the service journal. See the [operations index](README.md) for backup,
synchronization, security, and release references.
