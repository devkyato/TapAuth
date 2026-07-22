# TapAuth support

Before opening an issue:

1. Run `bash scripts/diagnose_nfc.sh` for reader problems.
2. Check `sudo systemctl status airhub.service` and `journalctl -u airhub.service -n 100`.
3. Open `/system_status` on the Raspberry Pi.
4. Run `python scripts/diagnose_firebase.py` for sync problems.

When filing a public issue, share error messages and versions, but remove student information, NFC UIDs, passwords, tokens, and `.env` values.
