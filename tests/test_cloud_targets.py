import unittest
from unittest.mock import patch

import cloud_targets


class CloudTargetTests(unittest.TestCase):
    def test_multiple_targets_are_fanned_out(self):
        targets = [
            {"name": "supabase", "kind": "supabase"},
            {"name": "archive", "kind": "webhook", "url": "https://example.test"},
        ]
        with patch.object(cloud_targets, "configured_targets", return_value=targets), \
             patch.object(cloud_targets, "sync_to_target", side_effect=[
                 {"synced": True, "target": "supabase"},
                 {"synced": True, "target": "archive"},
             ]) as writer:
            result = cloud_targets.sync_to_all("log", {"id": 1})
        self.assertTrue(result["synced"])
        self.assertEqual(writer.call_count, 2)

    def test_custom_log_payload_removes_identity_and_nfc(self):
        safe = cloud_targets._safe_record("log", {
            "id": 1, "student_no": "2026-1", "fullname": "Private Student",
            "nfc_code": "SECRET", "event_type": "LOGIN",
        })
        self.assertNotIn("nfc_code", safe)
        self.assertNotIn("fullname", safe)
        self.assertEqual(safe["event_type"], "LOGIN")


if __name__ == "__main__":
    unittest.main()
