import unittest

from scanner import NFCStandbyReader


class ScannerEventTests(unittest.TestCase):
    def test_wait_for_tap_returns_new_event_without_polling(self):
        reader = NFCStandbyReader(lambda uid: "ok")
        reader._publish_tap("CARD1", "Detected", payload={"user": {"firstname": "Alex"}})
        event = reader.wait_for_tap(0, timeout=0.01)
        self.assertEqual(event["tap_counter"], 1)
        self.assertEqual(event["uid"], "CARD1")
        self.assertEqual(event["user"]["firstname"], "Alex")


if __name__ == "__main__":
    unittest.main()
