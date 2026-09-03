import unittest
from unittest.mock import patch

import sync_service


class SyncServiceTests(unittest.TestCase):
    def test_no_cloud_targets_does_not_create_retry_noise(self):
        record = {"id": 1}
        with patch.object(sync_service, "sync_to_all", return_value={"synced": False, "disabled": True, "results": []}), \
             patch.object(sync_service, "enqueue_cloud_sync") as enqueue:
            result = sync_service.sync_user_or_queue(record)
        self.assertTrue(result["disabled"])
        self.assertFalse(result["queued"])
        enqueue.assert_not_called()

    def test_real_target_failure_is_queued(self):
        record = {"id": 2}
        failure = {"synced": False, "failed": [{"target": "supabase", "reason": "network down"}]}
        with patch.object(sync_service, "sync_to_all", return_value=failure), \
             patch.object(sync_service, "enqueue_cloud_sync") as enqueue:
            result = sync_service.sync_user_or_queue(record)
        self.assertTrue(result["queued"])
        enqueue.assert_called_once_with("supabase", "user", 2, "network down")


if __name__ == "__main__":
    unittest.main()
