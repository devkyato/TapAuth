import unittest
from unittest.mock import patch

import sync_service


class SyncServiceTests(unittest.TestCase):
    def test_disabled_firebase_does_not_create_retry_noise(self):
        record = {"id": 1}
        with patch.object(sync_service, "firebase_is_configured", return_value=False), \
             patch.object(sync_service, "enqueue_firebase_sync") as enqueue:
            result = sync_service.sync_user_or_queue(record)
        self.assertTrue(result["disabled"])
        self.assertFalse(result["queued"])
        enqueue.assert_not_called()

    def test_real_firebase_failure_is_queued(self):
        record = {"id": 2}
        with patch.object(sync_service, "firebase_is_configured", return_value=True), \
             patch.object(sync_service, "sync_user", return_value={"synced": False, "reason": "network down"}), \
             patch.object(sync_service, "enqueue_firebase_sync") as enqueue:
            result = sync_service.sync_user_or_queue(record)
        self.assertTrue(result["queued"])
        enqueue.assert_called_once_with("user", 2, "network down")


if __name__ == "__main__":
    unittest.main()
