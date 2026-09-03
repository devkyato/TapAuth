import unittest
from unittest.mock import patch

import supabase_adapter


class SupabaseAdapterTests(unittest.TestCase):
    def test_private_student_sync_omits_nfc_uid(self):
        record = {
            "id": 4, "student_no": "2026-1000", "firstname": "Alex",
            "lastname": "Santos", "fullname": "ALEX SANTOS",
            "course": "BSCPE", "nfc_code": "PRIVATE-CARD-UID",
        }
        with patch.object(supabase_adapter, "supabase_is_configured", return_value=True), \
             patch.object(supabase_adapter, "_upsert", return_value={"synced": True}) as upsert:
            result = supabase_adapter.sync_user(record)
        self.assertTrue(result["synced"])
        payload = upsert.call_args.args[1]
        self.assertNotIn("nfc_code", payload)

    def test_public_activity_omits_student_identity(self):
        record = {
            "id": 9, "student_no": "2026-1000", "fullname": "ALEX SANTOS",
            "status": "TAP_IN", "event_type": "LOGIN",
            "date_logged": "2026-09-03 08:00:00", "nfc_code": "PRIVATE",
        }
        payloads = {}

        def capture(table, payload):
            payloads[table] = payload
            return {"synced": True}

        with patch.object(supabase_adapter, "supabase_is_configured", return_value=True), \
             patch.object(supabase_adapter, "_upsert", side_effect=capture):
            result = supabase_adapter.sync_log(record)
        self.assertTrue(result["synced"])
        public = payloads["tapauth_public_activity"]
        self.assertNotIn("student_no", public)
        self.assertNotIn("fullname", public)
        self.assertNotIn("nfc_code", public)

    def test_reservation_sync_omits_local_model_path(self):
        record = {"id": 3, "service": "printing", "model_file_path": "/private/model.stl"}
        with patch.object(supabase_adapter, "supabase_is_configured", return_value=True), \
             patch.object(supabase_adapter, "_upsert", return_value={"synced": True}) as upsert:
            supabase_adapter.sync_reservation(record)
        self.assertNotIn("model_file_path", upsert.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
