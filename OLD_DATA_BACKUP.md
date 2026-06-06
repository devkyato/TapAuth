# Old Data Backup

The old Raspberry Pi SD-card data was copied locally from `E:\` into:

```text
C:\Users\kyama\OneDrive\Desktop\nfc-system-original-files\old data
```

The copy intentionally keeps old personal/database files local instead of committing them to GitHub. GitHub stores the new system and the repeatable copy/migration scripts only.

Copied areas:

- `E:\home` -> `old data\home`
- `E:\etc\systemd\system` -> `old data\etc_systemd_system`
- `E:\var\rootfs\home` -> `old data\nested_rootfs_home`
- `E:\var\rootfs\etc\mysql` -> `old data\nested_rootfs_etc_mysql`
- `E:\var\rootfs\etc\nfc` -> `old data\nested_rootfs_etc_nfc`
- `E:\var\rootfs\etc\systemd\system` -> `old data\nested_rootfs_etc_systemd_system`

The backup folder includes `COPY_MANIFEST.txt` with copied/missing source paths.

After extracting an old SQL dump, import it safely into MySQL:

```bash
bash scripts/migrate_old_sql.sh /path/to/old_airhub.sql
```

Then upload all active MySQL data to Realtime Database:

```bash
source .venv/bin/activate
python scripts/sync_realtime_db.py
```
## Dump Raw MariaDB Files To Real SQL

If the old raw MariaDB folder is available on a Raspberry Pi/Linux machine, create a real SQL dump with:

```bash
bash scripts/dump_old_raw_mariadb.sh /path/to/mysql_raw_from_E_var_var_lib_mysql /path/to/old_airhub_real_dump.sql
```

Then merge and upload:

```bash
bash scripts/migrate_old_sql.sh /path/to/old_airhub_real_dump.sql
source .venv/bin/activate
python scripts/sync_realtime_db.py
```

The recovery script starts the old MariaDB data directory in an isolated temporary socket/port and does not overwrite the current Airhub database.
