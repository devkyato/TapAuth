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
| Students | SQLite `users` | Private Supabase table without NFC UID |
| Attendance | SQLite `user_logs` | Private and sanitized Supabase tables |
| Reservations | SQLite `reservations` | Private Supabase table |
| 3D model files | Pi-local `uploads/models` | Never copied to Supabase |

The local registry uses atomic replacement, keeps a backup copy, and applies restricted file permissions when supported. Its directory is ignored by Git.

## When something is offline

- **Internet unavailable:** all kiosk, attendance, registration, and reservation operations continue locally.
- **SQLite temporarily locked:** connections wait briefly and close after every transaction; WAL mode allows safe concurrent readers.
- **One remote destination unavailable:** normal local operations continue. Only that destination gets a durable retry entry; successful destinations are not repeated.
- **Firebase Hosting unavailable:** only the shared public page is affected; the kiosk keeps running.
- **NFC reader disconnected:** the scanner keeps retrying instead of terminating the service.
- **Browser refreshed:** the server remains the source of truth for real NFC sessions.

The Pi owns the full operational record. Hosted services consume synchronized copies but never sit in the tap path. A bucket ID groups related installations, while a device ID identifies the originating kiosk.

## Fast interface updates

The scanner publishes a small server-sent event when a card is read. The browser updates only the tap-dependent parts of the page instead of continuously rendering the whole interface. If the event stream is unavailable, it falls back to a modest polling interval. There is no frontend framework or build bundle in the kiosk path.

## Multiple destinations

`cloud_targets.py` is the fan-out boundary. Supabase is the built-in shared database, and optional HTTPS webhooks can feed another storage service or campus integration. Private device-only fields such as NFC UIDs and uploaded model paths are removed before webhook delivery. Retry state is stored independently per target, record type, and local record ID.

## Privacy boundary

Oh! This part matters: the public activity feed never needs a student's card UID or full profile.

- Public responses contain sanitized event and timing fields.
- NFC UIDs and model-file paths are never sent to the public Supabase table.
- Registration must match the latest physical tap and expires after 120 seconds.
- The local management page requires `TAPAUTH_ADMIN_CODE`.
- `data/settings.json`, `.env`, registry data, uploads, exports, and secret keys stay outside Git.

If Flask is exposed beyond a trusted local network, place it behind HTTPS, authentication, and a reverse proxy.

## Main extension points

The reader, SQLite database, target adapters, local registry, and interface are separate modules. Firebase Hosting serves static files only, so hosting changes cannot break the NFC interaction.
