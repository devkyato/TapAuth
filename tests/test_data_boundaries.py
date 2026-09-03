import json
import unittest
from pathlib import Path

from firebase_adapter import public_log_payload, reservation_payload, user_payload


ROOT = Path(__file__).resolve().parents[1]


class DataBoundaryTests(unittest.TestCase):
    def test_public_activity_omits_student_identity(self):
        payload = public_log_payload({
            "id": 1,
            "fullname": "Private Student",
            "firstname": "Private",
            "lastname": "Student",
            "student_no": "2026-00001",
            "nfc_code": "SECRET-UID",
            "event_type": "LOGIN",
        })
        for field in ("fullname", "firstname", "lastname", "student_no", "nfc_code"):
            self.assertNotIn(field, payload)

    def test_private_firebase_records_omit_nfc_uid_and_local_paths(self):
        user = user_payload({"id": 1, "nfc_code": "SECRET-UID"})
        reservation = reservation_payload({
            "id": 1,
            "nfc_code": "SECRET-UID",
            "model_file_path": "/private/model.stl",
        })
        self.assertNotIn("nfc_code", user)
        self.assertNotIn("nfc_code", reservation)
        self.assertNotIn("model_file_path", reservation)

    def test_database_rules_keep_private_records_private(self):
        rules = json.loads((ROOT / "database.rules.json").read_text(encoding="utf-8"))["rules"]["tapauth"]
        self.assertTrue(rules["logs"][".read"])
        self.assertFalse(rules["logs"][".write"])
        self.assertFalse(rules["users"][".read"])
        self.assertFalse(rules["reservations"][".read"])


if __name__ == "__main__":
    unittest.main()
