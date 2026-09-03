import tempfile
import unittest
from pathlib import Path

import sqlite_database as db


class SQLiteDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db.DB_PATH = Path(self.tempdir.name) / "tapauth.db"
        db._schema_ready = False

    def tearDown(self):
        self.tempdir.cleanup()

    def test_registration_attendance_and_restart_persistence(self):
        user = db.create_user(
            student_no="2026-0001",
            lastname="Santos",
            firstname="Alex",
            middlename="",
            course="BS Computer Engineering",
            project_type="Student",
            room="AIRHub",
            nfc_code="04:AA:BB:CC",
        )
        self.assertEqual(user["nfc_code"], "04AABBCC")
        self.assertFalse(db.is_user_checked_in("04-AA-BB-CC"))

        first = db.insert_log("04 AA BB CC")
        self.assertEqual(first["status"], "TAP_IN")
        self.assertTrue(db.is_user_checked_in("04AABBCC"))

        second = db.insert_log("04AABBCC")
        self.assertEqual(second["status"], "TAP_OUT")
        self.assertFalse(db.is_user_checked_in("04AABBCC"))

        db._schema_ready = False
        restored = db.get_user_by_nfc("04:AABB:CC")
        self.assertEqual(restored["student_no"], "2026-0001")
        self.assertEqual(len(db.get_logs()), 2)

    def test_printing_queue_and_teacher_reservation(self):
        common = {
            "nfc_code": "CARD-1",
            "fullname": "ALEX SANTOS",
            "student_no": "2026-0001",
            "course": "BS COMPUTER ENGINEERING",
            "reservation_date": "2026-09-04",
        }
        first = db.create_reservation(service="printing", project_name="Gear", **common)
        second = db.create_reservation(service="printing", project_name="Case", **common)
        teacher = db.create_reservation(
            service="teacher", teacher_name="Prof. Reyes", schedule_time="13:00", **common
        )

        self.assertEqual(first["queue_position"], 1)
        self.assertEqual(second["queue_position"], 2)
        self.assertIsNone(teacher["queue_position"])
        self.assertEqual(len(db.get_reservations()), 3)

    def test_each_cloud_target_has_an_independent_durable_retry(self):
        db.enqueue_cloud_sync("supabase", "user", 7, "offline")
        db.enqueue_cloud_sync("archive", "user", 7, "offline")
        self.assertEqual(db.get_cloud_queue_count(), {"pending": 2, "total": 2})
        items = db.get_pending_cloud_sync()
        supabase = next(item for item in items if item["target"] == "supabase")
        archive = next(item for item in items if item["target"] == "archive")
        db.mark_cloud_sync_failed(supabase["id"], "still offline")
        self.assertEqual(
            next(item for item in db.get_pending_cloud_sync() if item["target"] == "supabase")["attempts"],
            1,
        )
        db.mark_cloud_sync_done(archive["id"])
        self.assertEqual(db.get_cloud_queue_count(), {"pending": 1, "total": 2})


if __name__ == "__main__":
    unittest.main()
