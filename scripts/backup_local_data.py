#!/usr/bin/env python3
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import SQLITE_CONFIG


SOURCE = Path(SQLITE_CONFIG["path"]).expanduser().resolve()
BACKUP_ROOT = ROOT / "backups"


def main():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = BACKUP_ROOT / stamp
    destination.mkdir(parents=True, exist_ok=False)

    if SOURCE.exists():
        with sqlite3.connect(SOURCE) as source, sqlite3.connect(destination / "tapauth.db") as target:
            source.backup(target)

    for name in ("registered_cards.json", "registered_cards.backup.json"):
        candidate = ROOT / "data" / name
        if candidate.exists():
            shutil.copy2(candidate, destination / name)

    print(f"Backup created at {destination}")


if __name__ == "__main__":
    main()
