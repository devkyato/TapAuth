# Changelog

This file records the changes I would want to know about before updating an installed TapAuth kiosk.

## 2.0.0 — 2026-09-03

This is the Pi-first release. I removed the separate database service from the default runtime because the kiosk should not need internet, GitHub, Firebase, or MariaDB to open and do its job.

- Made SQLite the default database for students, attendance, reservations, and Firebase retry jobs.
- Kept MySQL as an explicit legacy backend for existing deployments.
- Added a one-time MySQL-to-SQLite migration tool.
- Added automatic local backups before manual updates.
- Removed GitHub updates from the boot dependency chain.
- Simplified the systemd service so it starts after the local filesystem, not the network.
- Added end-to-end SQLite tests for registration, tap state, queue order, persistence, and retry jobs.
- Added a focused Raspberry Pi deployment and recovery guide.

## 1.1.0 — 2026-07-29

I kept running into one uncomfortable edge case: a student could finish registration, tap again, and still look unregistered if MySQL was slow or unavailable. This release makes card recognition local-first.

### Changed

- Added a durable on-device NFC registry with atomic writes and backup recovery.
- Allowed student registration and recognition to continue without an active MySQL connection.
- Added automatic reconciliation between the local registry and MySQL.
- Normalized ACR122U UIDs across raw bytes and common text formats.
- Added legacy-record self-healing, database retries, and a recent-registration cache.
- Expanded Recent Logs to the latest 25 records with a responsive **See more** control.
- Added the server dependencies needed by registration tests in CI.
- Reworked the public documentation around the actual project story and runtime flow.

### Fixed

- Fixed newly registered cards appearing unregistered during the NFC cooldown window.
- Fixed database outages being reported as though a card had never been registered.
- Added post-write persistence checks and regression coverage for offline registration.

## 1.0.0 — 2026-07-22

This was the first public TapAuth release: the point where the AIRHub NFC prototype became a reusable Raspberry Pi project.

- Renamed the project to TapAuth.
- Added tap-bound registration without a shared student registration code.
- Added NFC attendance, 3D printing requests, and teacher appointments.
- Added MySQL storage and Firebase-backed private/public data boundaries.
- Added secure local 3D model storage and reservation queue positions.
- Added student and reservation management.
- Added Raspberry Pi startup, reader recovery, update tools, CI, and community files.
- Removed student identity from the publicly readable Firebase activity feed.
