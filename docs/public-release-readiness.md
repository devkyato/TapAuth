# TapAuth public release readiness

TapAuth must not be promoted as production-ready until the identity, privacy, attendance, deployment, and recovery boundaries below are corrected. Discoverability is useful only after the system is safe enough for real users.

## Current release gate

Public deployment with real student, employee, or visitor data is blocked. The current design exposes tap state, relies on caller-submitted tap identifiers, uses a shared administrator code, infers attendance through tap-count parity, starts hardware and background workers during web-module import, and permits mutable boot-time updates.

## Mandatory security redesign

- Replace public NFC identity and tap-counter credentials with random one-time tap-session tokens.
- Bind each token to a kiosk or browser session, permitted action, expiry, and transactional one-time consumption.
- Never expose card UID or reusable tap state through public endpoints.
- Replace the shared administrator code with named accounts, password hashing, server-side sessions, secure cookies, CSRF protection, rate limiting, roles, and audit records.
- Require authentication and authorization for operational status, logs, reservations, retries, registration, synchronization, and administrative actions.
- Add explicit privacy classifications and retention periods for identifiers, attendance, uploads, logs, and reservations.

## Data and attendance correctness

- Replace count-parity attendance with explicit attendance sessions and transactional state transitions.
- Add idempotency keys and duplicate-event handling.
- Define timezone, midnight, manual correction, deletion, device restart, and offline reconciliation behavior.
- Replace the JSON registry with SQLite or another durable transactional local store.
- Add record versions, tombstones, conflict policy, and central/local authority rules so stale offline data cannot resurrect or overwrite newer records.
- Implement a durable outbox with retry state, dead-letter handling, auditability, and administrator recovery tools.

## Runtime architecture

Separate the NFC hardware daemon, authenticated API/web application, durable background worker, database, and reverse proxy. The web module must not start device readers or workers during import. Support health checks without exposing identities or secrets.

## Deployment hardening

- Stop sourcing `.env` files as shell programs.
- Remove SQL string interpolation from setup scripts.
- Replace device mode `0666` with a dedicated service group and least privilege.
- Run behind a production WSGI server and reverse proxy.
- Pin dependencies and release artifacts.
- Replace mutable `git pull main` boot updates with signed, versioned, rollback-capable releases.
- Add database migrations, backup verification, restore drills, and secret rotation.

## Upload safety

Validate file signatures and actual parser structure, enforce compressed and expanded size limits, isolate processing, apply quotas and rate limits, scan or reject unsupported content, use randomized storage names, and define retention and deletion jobs.

## Usability improvements after security gates

- Guided first-run setup with environment checks and no secrets in URLs.
- Role-specific dashboards for staff, administrators, and kiosk operators.
- Clear offline/online/sync status with actionable recovery steps.
- Reservation, attendance, registration, and upload workflows with confirmation and undo where safe.
- Accessibility, responsive mobile layouts, keyboard navigation, readable errors, and multilingual-ready strings.
- Export, correction, audit, privacy request, and retention-management workflows.

## Documentation site

Publish deployment architecture, threat model, privacy model, administrator guide, kiosk guide, attendance rules, offline behavior, incident response, backup and restore, API reference, hardware compatibility, troubleshooting, and release notes. Every page must state whether the build is demo-only, pilot-ready, or production-approved.

## Discoverability and publication

Do not optimize search visibility for production adoption until the mandatory security redesign passes independent review. Before that point, describe TapAuth only as an experimental NFC workflow prototype. After approval, publish versioned container images or installation bundles, signed checksums, SBOMs, administrator documentation, a public security policy, and a maintained project website.

## Required release tests

Run MySQL or the selected database, Firebase emulator or replacement sync service, simulated NFC devices, browser end-to-end tests, authentication and authorization tests, CSRF tests, concurrent tap tests, offline reconciliation tests, restart and power-loss tests, upload attack tests, migration tests, backup/restore tests, dependency scanning, and privacy boundary tests.

## Success criteria

A real user must be unable to impersonate a card from public state, administrators must have accountable sessions, attendance must remain correct under retries and concurrency, offline reconciliation must not resurrect deleted data, deployment must be reproducible and reversible, and no public endpoint may leak personal identity or reusable credentials.