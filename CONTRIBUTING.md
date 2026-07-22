# Contributing to TapAuth

Thanks for helping improve TapAuth.

1. Fork the repository and create a focused branch.
2. Keep the kiosk lightweight and usable at 1366×700.
3. Never commit `.env`, database exports, NFC identifiers, or Firebase server credentials.
4. Run the checks documented in the README.
5. Explain hardware, schema, and UI behavior changes in the pull request.

For NFC changes, include the reader model and Raspberry Pi OS version used for testing. For database changes, make `schema.sql` safe to run against an existing installation.
