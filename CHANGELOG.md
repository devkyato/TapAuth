# Changelog

All notable TapAuth changes are documented here.

## Unreleased

- Expanded Recent Logs to the latest 25 records with responsive row fitting and a See more control.
- Fixed newly registered cards appearing unregistered during the NFC cooldown window.
- Added a post-write persistence check and registration-flow regression tests.
- Added the server dependencies required by registration tests to CI.

## 1.0.0 — 2026-07-22

- Renamed the project to TapAuth.
- Added short-lived tap-bound student registration without a shared student code.
- Added local and Firebase-backed student, attendance, and reservation data.
- Added secure local 3D model storage and reservation queue positions.
- Added the student and reservation management dashboard.
- Added Raspberry Pi startup, reader recovery, update tooling, CI, and open-source documentation.
- Removed student identity from the publicly readable Firebase activity feed.
- Added automated privacy boundary tests and complete GitHub community templates.
- Removed obsolete machine-specific recovery notes and the deprecated Firestore-named sync alias.
