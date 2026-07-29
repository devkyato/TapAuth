# TapAuth 1.1.0 — The local-first registration release

I thought registration was finished once a student record reached MySQL. Real usage showed the missing part: the same card still has to be recognized immediately, even during a slow query, a database restart, or an internet outage.

So, this release gives the Raspberry Pi its own durable card registry.

A registration is written locally first, with atomic replacement and a backup copy. TapAuth can recognize that card after a service restart without asking MySQL on every tap. When MySQL is available, the local record is reconciled automatically. Firebase remains an optional synchronized copy rather than a requirement for using the kiosk.

This release also:

- normalizes NFC UIDs from different ACR122U representations;
- repairs compatible legacy card records during lookup;
- distinguishes an unavailable database from a genuinely unknown card;
- keeps the latest 25 activity entries available behind **See more**;
- adds regression tests for local persistence, backup recovery, and offline registration;
- refreshes the project documentation in a more direct, personal voice.

## Updating a Raspberry Pi

```bash
cd ~/TapAuth
git pull --ff-only origin main
bash scripts/update_pi_from_github.sh
sudo systemctl restart airhub.service
```

The update script imports existing MySQL students into the local registry. If MySQL is temporarily unavailable during the update, the registry already on the Pi remains intact.

## Verification

TapAuth 1.1.0 is checked with Python compilation, JavaScript syntax checks, Firebase JSON validation, shell syntax checks, and the complete unit-test suite.
