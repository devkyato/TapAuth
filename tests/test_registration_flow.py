import unittest
from unittest.mock import patch

import app as app_module
from scanner import NFCStandbyReader


class RegistrationFlowTests(unittest.TestCase):
    def setUp(self):
        with app_module.registration_cache_lock:
            app_module.recent_registration_cache.clear()

    def test_reader_cache_becomes_registered_immediately(self):
        reader = NFCStandbyReader(on_tap=lambda _uid: {"message": "School ID detected"})
        reader._last_uid = "CARD-1"
        reader._last_payload = None
        reader._cooldown["CARD-1"] = 1

        updated = reader.cache_registered_user("CARD-1", {
            "firstname": "Alex",
            "fullname": "ALEX SANTOS",
            "student_no": "2026-00001",
            "course": "BS COMPUTER ENGINEERING",
        })

        self.assertTrue(updated)
        self.assertEqual(reader.latest_tap(-1)["user"]["student_no"], "2026-00001")
        self.assertNotIn("CARD-1", reader._cooldown)

    @patch.object(app_module, "enqueue_sync")
    @patch.object(app_module.nfc_reader, "cache_registered_user")
    @patch.object(app_module, "create_user")
    @patch.object(app_module, "get_user_by_nfc", return_value=None)
    @patch.object(app_module, "valid_latest_tap", return_value={"uid": "CARD-1", "tap_counter": 7})
    def test_registration_response_is_immediately_usable(
        self,
        _valid_tap,
        _get_user,
        create_user,
        cache_registered_user,
        enqueue_sync,
    ):
        create_user.return_value = {
            "id": 12,
            "firstname": "ALEX",
            "fullname": "ALEX SANTOS",
            "student_no": "2026-00001",
            "course": "BS COMPUTER ENGINEERING",
            "nfc_code": "CARD-1",
        }
        client = app_module.app.test_client()

        response = client.post("/register_from_tap", json={
            "uid": "CARD-1",
            "tap_counter": 7,
            "firstname": "Alex",
            "lastname": "Santos",
            "student_no": "2026-00001",
            "course": "BS Computer Engineering",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertEqual(response.get_json()["user"]["student_no"], "2026-00001")
        cache_registered_user.assert_called_once()
        enqueue_sync.assert_called_once()

    @patch.object(app_module, "is_user_checked_in", return_value=False)
    @patch.object(app_module.nfc_reader, "cache_registered_user")
    @patch.object(app_module, "get_user_by_nfc")
    @patch.object(app_module, "valid_latest_tap", return_value={"uid": "CARD-1", "tap_counter": 8})
    def test_registration_retry_recovers_existing_card(
        self,
        _valid_tap,
        get_user,
        cache_registered_user,
        _checked_in,
    ):
        get_user.return_value = {
            "id": 12,
            "firstname": "ALEX",
            "fullname": "ALEX SANTOS",
            "student_no": "2026-00001",
            "course": "BS COMPUTER ENGINEERING",
            "nfc_code": "CARD-1",
        }
        client = app_module.app.test_client()

        response = client.post("/register_from_tap", json={
            "uid": "CARD-1",
            "tap_counter": 8,
            "firstname": "Alex",
            "lastname": "Santos",
            "student_no": "2026-00001",
            "course": "BS Computer Engineering",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["message"], "This card is already registered.")
        cache_registered_user.assert_called_once()

    @patch.object(app_module, "is_user_checked_in", return_value=False)
    @patch.object(app_module, "get_user_by_nfc", side_effect=RuntimeError("database offline"))
    def test_recent_registration_cache_survives_temporary_database_failure(
        self,
        _get_user,
        _checked_in,
    ):
        app_module.cache_registered_user("04:A1:B2:C3", {
            "firstname": "ALEX",
            "fullname": "ALEX SANTOS",
            "student_no": "2026-00001",
            "course": "BS COMPUTER ENGINEERING",
        })

        result = app_module.handle_tap("04-A1-B2-C3")

        self.assertEqual(result["payload"]["user"]["student_no"], "2026-00001")

    @patch.object(app_module, "get_user_by_nfc", side_effect=RuntimeError("database offline"))
    def test_database_failure_is_not_reported_as_unregistered(self, _get_user):
        result = app_module.handle_tap("04:A1:B2:C3")

        self.assertTrue(result["payload"]["lookup_unavailable"])
        self.assertNotIn("user", result["payload"])


if __name__ == "__main__":
    unittest.main()
