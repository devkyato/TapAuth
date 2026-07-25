import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import local_registry


class LocalRegistryTests(unittest.TestCase):
    def test_registry_survives_memory_and_process_state(self):
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "registered_cards.json"
            backup_path = Path(directory) / "registered_cards.backup.json"
            with (
                patch.object(local_registry, "REGISTRY_PATH", registry_path),
                patch.object(local_registry, "REGISTRY_BACKUP_PATH", backup_path),
            ):
                local_registry.save_local_user({
                    "firstname": "ALEX",
                    "lastname": "SANTOS",
                    "fullname": "ALEX SANTOS",
                    "student_no": "2026-00001",
                    "course": "BS COMPUTER ENGINEERING",
                    "nfc_code": "04:A1:B2:C3",
                })

                loaded = local_registry.get_local_user("04-A1-B2-C3")

                self.assertEqual(loaded["student_no"], "2026-00001")
                self.assertEqual(loaded["nfc_code"], "04A1B2C3")

    def test_backup_is_used_if_primary_registry_is_corrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "registered_cards.json"
            backup_path = Path(directory) / "registered_cards.backup.json"
            backup_path.write_text(
                '{"version":1,"users":{"CARD1":{"nfc_code":"CARD1","student_no":"2026-1"}}}',
                encoding="utf-8",
            )
            registry_path.write_text("{not-json", encoding="utf-8")
            with (
                patch.object(local_registry, "REGISTRY_PATH", registry_path),
                patch.object(local_registry, "REGISTRY_BACKUP_PATH", backup_path),
            ):
                loaded = local_registry.get_local_user("CARD1")

                self.assertEqual(loaded["student_no"], "2026-1")


if __name__ == "__main__":
    unittest.main()
