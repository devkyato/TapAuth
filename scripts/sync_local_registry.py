#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import create_user, get_all_users
from local_registry import REGISTRY_PATH, get_all_local_users, save_local_users


def main():
    restored = 0
    for user in get_all_local_users():
        create_user(
            student_no=str(user.get("student_no") or ""),
            lastname=str(user.get("lastname") or ""),
            firstname=str(user.get("firstname") or ""),
            middlename=str(user.get("middlename") or ""),
            course=str(user.get("course") or ""),
            project_type=str(user.get("project_type") or "STUDENT"),
            room=str(user.get("room") or "AIRHUB"),
            nfc_code=str(user.get("nfc_code") or ""),
        )
        restored += 1
    users = get_all_users()
    saved = save_local_users(users)
    print(
        f"Local NFC registry ready: {saved} student(s) cached, "
        f"{restored} local record(s) reconciled at {REGISTRY_PATH}"
    )


if __name__ == "__main__":
    main()
