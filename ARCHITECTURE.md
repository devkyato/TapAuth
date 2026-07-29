# How TapAuth works

TapAuth is local-first because the Raspberry Pi is the one device that should remain useful even when another service is unavailable.

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

I thought about relying only on MySQL here, but that makes a registered card appear unknown whenever the connection has a temporary problem. The registry avoids that. A successful database lookup or registration refreshes the local copy, and a background worker reconciles locally saved students when MySQL returns.

## Where each kind of data belongs

| Data | Primary location | Other copies |
| --- | --- | --- |
| Card identity fallback | `data/registered_cards.json` | Reconciled with MySQL |
| Students | MySQL `users` | Private Firebase copy without NFC UID |
| Attendance | MySQL `logs` | Public-safe Firebase event copy |
| Reservations | MySQL `reservations` | Private Firebase copy |
| 3D model files | Pi-local `uploads/models` | Never copied to Firebase |

The local registry uses atomic replacement, keeps a backup copy, and applies restricted file permissions when supported. Its directory is ignored by Git.

## When something is offline

- **MySQL unavailable:** known cards are still recognized and new registrations can be saved locally. Local identities are queued for reconciliation.
- **Firebase unavailable:** normal local operations continue. Failed remote writes remain in `firebase_sync_queue` for retry.
- **NFC reader disconnected:** the scanner keeps retrying instead of terminating the service.
- **Browser refreshed:** the server remains the source of truth for real NFC sessions.

MySQL still owns complete attendance and reservation operations. The registry specifically removes MySQL as a single point of failure for card recognition and registration.

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
