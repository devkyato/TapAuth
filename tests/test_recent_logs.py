import unittest
from unittest.mock import patch

import app as app_module


class RecentLogsTests(unittest.TestCase):
    @patch.object(app_module, "get_logs", return_value=[])
    def test_recent_logs_endpoint_requests_twenty_five_rows(self, get_logs):
        response = app_module.app.test_client().get("/user_logs_info")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])
        get_logs.assert_called_once_with(limit=25)


if __name__ == "__main__":
    unittest.main()
