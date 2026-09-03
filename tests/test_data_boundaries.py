import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DataBoundaryTests(unittest.TestCase):
    def test_supabase_schema_keeps_private_tables_private(self):
        schema = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8").lower()
        for table in ("tapauth_students", "tapauth_attendance", "tapauth_reservations"):
            self.assertIn(f"alter table public.{table} enable row level security", schema)
            self.assertIn(f"revoke all on public.{table} from anon, authenticated", schema)
        self.assertIn("grant select on public.tapauth_public_activity to anon, authenticated", schema)

    def test_browser_config_example_contains_no_secret_key(self):
        config = (ROOT / "hosting" / "runtime-config.example.js").read_text(encoding="utf-8")
        self.assertIn("supabasePublishableKey", config)
        self.assertNotIn("secretKey", config)
        self.assertNotIn("sb_secret_", config)


if __name__ == "__main__":
    unittest.main()
