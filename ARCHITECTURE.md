# How TapAuth works

TapAuth is Pi-first because the Raspberry Pi is the one device that must remain useful even when every hosted service is unavailable.

## A tap, from card to record

When a card is tapped, the ACR122U reader sends its UID to the Flask application. TapAuth normalizes that UID so raw reader bytes and common text formats resolve to one stable value.

The application checks the private on-device registry first:

```text
ACR122U reader
      |
      v
UID normalization
      |
      v
On-device registry
      |
      +-- known card --> check in, check out, or appointment
      |
      +-- unknown card --> short-lived registration session
```

I thought about keeping a separate MySQL service, but it added another boot dependency without adding value for one kiosk. SQLite now stores the complete operational state in one durable local file. The card registry remains an intentionally small second fallback for identity recovery.

## Where each kind of data belongs

| Data | Primary location | Other copies |
| --- | --- | --- |
| Card identity fallback | `data/registered_cards.json` | Reconciled with SQLite |
| Students | SQLite `users` | Private Firebase copy without NFC UID |
| Attendance | SQLite `user_logs` | Public-safe Firebase event copy |
| Reservations | SQLite `reservations` | Private Firebase copy |
| 3D model files | Pi-local `uploads/models` | Never copied to Firebase |

The local registry uses atomic replacement, keeps a backup copy, and applies restricted file permissions when supported. Its directory is ignored by Git.

## When something is offline

- **Internet unavailable:** all kiosk, attendance, registration, and reservation operations continue locally.
- **SQLite temporarily locked:** connections wait briefly and close after every transaction; WAL mode allows safe concurrent readers.
- **Firebase unavailable:** normal local operations continue. Failed remote writes remain in `firebase_sync_queue` for retry.
- **NFC reader disconnected:** the scanner keeps retrying instead of terminating the service.
- **Browser refreshed:** the server remains the source of truth for real NFC sessions.

The Pi owns the full operational record. Hosted services consume synchronized copies but never sit in the tap path.

## Privacy boundary

Oh! This part matters: the public activity feed never needs a student's card UID or full profile.

- Public responses contain sanitized event and timing fields.
- NFC UIDs and model-file paths are removed from public Firebase records.
- Registration must match the latest physical tap and expires after 120 seconds.
- The local management page requires `TAPAUTH_ADMIN_CODE`.
- `.env`, registry data, uploads, exports, and server credentials stay outside Git.

If Flask is exposed beyond a trusted local network, place it behind HTTPS, authentication, and a reverse proxy.

## Main extension points

The reader, database, Firebase adapter, local registry, and interface are separate modules. A hosted API, email service, or object-storage adapter can be added without rewriting the NFC interaction itself.
