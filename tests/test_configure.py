import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import configure


class ConfigureTests(unittest.TestCase):
    def test_wizard_separates_private_and_browser_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "data" / "settings.json"
            hosting = root / "hosting" / "runtime-config.js"
            hosting.parent.mkdir(parents=True)
            answers = iter([
                "pi-main", "engineering", "y", "https://demo.supabase.co",
                "sb_publishable_public", "", "firebase-project",
            ])
            secrets = iter(["admin-code", "sb_secret_private"])
            with patch.object(configure, "SETTINGS_PATH", settings), \
                 patch.object(configure, "HOSTING_CONFIG", hosting), \
                 patch("builtins.input", side_effect=lambda _prompt: next(answers)), \
                 patch.object(configure.getpass, "getpass", side_effect=lambda _prompt: next(secrets)):
                configure.main()

            private = json.loads(settings.read_text(encoding="utf-8"))
            public = hosting.read_text(encoding="utf-8")
            self.assertEqual(private["TAPAUTH_BUCKET_ID"], "engineering")
            self.assertEqual(private["TAPAUTH_SUPABASE_SECRET_KEY"], "sb_secret_private")
            self.assertNotIn("sb_secret_private", public)
            self.assertIn("sb_publishable_public", public)


if __name__ == "__main__":
    unittest.main()
