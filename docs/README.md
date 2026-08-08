# TapAuth documentation and operations index

TapAuth is the product name regardless of the local checkout folder. I keep
this page as the shortest route from installation to the operational detail
needed on a real kiosk.

## Start and understand

- [Getting started](getting-started.md): Raspberry Pi requirements, setup,
  service checks, and updates.
- [Architecture](../ARCHITECTURE.md): NFC flow, local registry, MySQL, and
  optional Firebase boundaries.
- [Main README](../README.md): capabilities, configuration, commands,
  limitations, applications, and connected projects.

## Operate and recover

- `scripts/setup_raspberry_pi.sh`: first installation.
- `scripts/update_pi_from_github.sh`: update an installed Pi and reconcile the
  local registry.
- `scripts/diagnose_nfc.sh`: reader and service diagnostics.
- `scripts/sync_realtime_db.py`: explicit MySQL-to-Firebase synchronization.
- [Support](../SUPPORT.md): problem reports and diagnostic context.
- [Security](../SECURITY.md): private vulnerability reporting and data safety.

Keep `.env`, database credentials and exports, service-account files, student
records, NFC UIDs, and `data/registered_cards.json` out of version control.
Back up operational data before updates.

## Develop and release

- [Contributing](../CONTRIBUTING.md): checks and release checklist.
- [Changelog](../CHANGELOG.md): user-visible changes.
- [TapAuth 1.1.2 release notes](releases/1.1.2.md).
- [TapAuth 1.1.0 release notes](RELEASE_1.1.0.md).
- [Citation metadata](../CITATION.cff).
