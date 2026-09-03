# Getting TapAuth unstuck

I would check the system in this order:

1. Open `/system_status` on the Raspberry Pi.
2. Run `sudo systemctl status airhub.service`.
3. Read the latest service output with `journalctl -u airhub.service -n 100`.
4. For reader problems, run `bash scripts/diagnose_nfc.sh`.
5. For sharing problems, open `/cloud_sync_status` and run `python scripts/sync_supabase.py`.
6. Restart cleanly with `sudo systemctl restart airhub.service`.

If you open a public issue, include the error, Raspberry Pi OS version, Python version, and reader model. Remove student information, NFC UIDs, passwords, tokens, and `.env` values first.
