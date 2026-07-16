# Production architecture

## User flows

### Teacher appointment

1. A student taps a registered school ID at the Raspberry Pi kiosk.
2. The Pi sends a signed tap event to the Vercel API.
3. The API creates a short-lived, single-use NFC session and returns only public-safe profile fields to the kiosk.
4. The student selects a teacher, date, time, and appointment purpose.
5. Firebase stores the request as `pending` in a transaction that prevents a duplicate time slot.
6. The teacher receives approve/reject links by email.
7. The student receives the decision by email.

### 3D printing

1. The same NFC verification unlocks the print request.
2. The model is uploaded through a controlled storage URL; the server verifies the extension, size, and stored object metadata.
3. Firebase stores private request data separately from the public-safe queue projection.
4. Laboratory personnel approve or reject the file and schedule.
5. The server assigns `now`, `next`, and `upcoming` positions. Clients cannot write queue positions.
6. The student receives submission and decision emails.

## Raspberry Pi tap behavior

Airhub attendance and reservation identity are separate event types:

- Attendance tap 1: `CHECK_IN`
- Attendance tap 2: `EXIT`
- Attendance tap 3: `RETURN`
- Attendance tap 4: `EXIT`
- Reservation tap: creates an expiring reservation session and must not alter attendance state

The current attendance implementation alternates odd/even same-day taps. Before production it should explicitly store event types, lengthen the reader cooldown, handle sessions that cross midnight, and keep reservation taps from changing occupancy.

## Data boundaries

- Public: project label, scheduled time, and queue status only.
- Personnel: requester identity, description, notes, model metadata, and review state.
- Restricted: raw NFC identifiers, device secrets, Firebase credentials, and email provider keys.

Raw NFC identifiers must never be returned by a public browser endpoint. Device requests require HTTPS, a device ID, timestamp, nonce, and HMAC signature. NFC sessions expire quickly and are consumed atomically with reservation creation.

## Environment ownership

- Raspberry Pi `.env`: reader device credentials, local MySQL, and outbound API configuration.
- Vercel environment: Firebase Admin credentials, email provider key, Turnstile secret, signing keys, and personnel email configuration.
- Browser: public Firebase configuration and Turnstile site key only.
