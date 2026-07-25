import unittest

from nfc_utils import canonicalize_nfc_uid


class NfcUidTests(unittest.TestCase):
    def test_common_text_formats_share_one_uid(self):
        expected = "04A1B2C3D4"
        for value in ("04:A1:B2:C3:D4", "04-A1-B2-C3-D4", "04 a1 b2 c3 d4", "0x04A1B2C3D4"):
            self.assertEqual(canonicalize_nfc_uid(value), expected)

    def test_ascii_uid_bytes_are_canonicalized(self):
        self.assertEqual(canonicalize_nfc_uid(b"04:A1:B2:C3"), "04A1B2C3")

    def test_raw_uid_bytes_are_hex_encoded(self):
        self.assertEqual(canonicalize_nfc_uid(bytes([0x04, 0xA1, 0xB2, 0xC3])), "04A1B2C3")


if __name__ == "__main__":
    unittest.main()
