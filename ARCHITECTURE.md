# TapAuth architecture

TapAuth is a local-first NFC attendance and reservation kiosk designed for a Raspberry Pi. Local MySQL is the source of truth; Firebase Realtime Database is an optional, retryable copy for remote visibility.

## Runtime flow

```text
ACR122U NFC reader
        |
        v
Raspberry Pi / Flask ----> MySQL
        |                    |
        |                    +---- durable Firebase retry queue
        v
Firebase Realtime Database ----> public-safe activity page
```

The reader runs continuously and reconnects after hardware interruptions. A card tap creates a short-lived session. A registered card may check in/out or request an appointment; an unknown card may register only while its matching physical tap session remains valid.

## Data ownership

- `users`: private student profile and card association in MySQL; mirrored to private Firebase data without the NFC UID.
- `logs`: complete local attendance record; mirrored to the public path with event and timing fields only.
- `reservations`: requester and request details in MySQL; mirrored to private Firebase data without NFC UIDs or local file paths.
- `uploads/models`: Pi-local 3D files; ignored by Git and never copied to Realtime Database.

Firebase paths live below the configurable `tapauth` root. Database rules allow public reads only for `tapauth/logs`; browsers cannot write any path.

## Availability model

Attendance and reservations complete against local MySQL even when Firebase is unavailable. Failed cloud writes enter `firebase_sync_queue`, and the background worker retries them without blocking the kiosk.

## Security boundary

- Student registration must match the latest NFC UID and tap counter and expires after 120 seconds.
- The management dashboard requires `TAPAUTH_ADMIN_CODE` and is intended for a trusted local network.
- Public API responses remove NFC UIDs and model storage paths.
- `.env`, database exports, uploaded models, Firebase secrets, and service-account files are excluded from Git.
- The Firebase browser key identifies the public web application; it is not an administrator credential.

For an internet-facing deployment, place the Flask service behind HTTPS, network authentication, and a reverse proxy rather than exposing port 5000 directly.

## Extension points

Database access, Firebase synchronization, NFC reading, and presentation are separated into modules. A future hosted API, email provider, or object-storage adapter can be added without changing the kiosk interaction model.
