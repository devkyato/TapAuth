# Old Raw Database Export Notes

The recovered old database files are in:

`../old/mysql_raw`

They include raw MariaDB/MySQL files, not a live SQL dump. To translate them into SQL and CSV, use a compatible MariaDB server. The safest path is:

1. Start a MariaDB server using the recovered datadir.
2. Confirm `airhub_db` opens.
3. Run `scripts/export_database.sh`.

Do not clean or overwrite `E:\` until the export folder contains:

- full `.sql` dump
- one TSV/CSV-compatible file per table
- old raw backup remains present
