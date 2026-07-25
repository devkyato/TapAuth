# TapAuth architecture

TapAuth is a local-first NFC attendance and reservation kiosk designed for a Raspberry Pi. A private on-device registry keeps card identity available without MySQL; MySQL stores the complete operational records, and Firebase Realtime Database is an optional, retryable remote copy.

## Runtime flow

```text
ACR122U NFC reader
        |
        v
Raspberry Pi / Flask ----> MySQL
        |              \----> private on-device NFC registry
        |                    |
        |                    +---- durable Firebase retry queue
        v
Firebase Realtime Database ----> public-safe activity page
```

The reader runs continuously and reconnects after hardware interruptions. A card tap creates a short-lived session. Card identity is checked against the durable local registry first, so an assigned card remains recognized through service restarts and MySQL outages. Registry records reconcile back to MySQL when it becomes available.

## Data ownership

- `users`: private student profile and card association in MySQL; mirrored to private Firebase data without the NFC UID.
- `data/registered_cards.json`: private Pi-local identity fallback with restricted file permissions, atomic replacement, and a backup copy; ignored by Git.
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
