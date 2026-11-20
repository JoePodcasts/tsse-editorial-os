"""Ensure the public archive adapter supports Ask's records property."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from archive_public import PublicArchiveApp


class PublicRecordsCompatibilityTests(unittest.TestCase):
    def test_public_app_initializes_with_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            (root / "catalogue.jsonl").write_text(
                json.dumps({
                    "episode_id": "test-episode",
                    "episode_number": 1,
                    "remote_id": "test-remote",
                    "public_presence": "present"
                }) + "\n"
            )
            (root / "manifest.json").write_text("{}")
            (root / "export-inventory.json").write_text(
                json.dumps({"files": [{"remote_id": "test-remote"}]})
            )
            (root / "sync-status.json").write_text("{}")

            with patch("archive_public.PublicStatus"):
                app = PublicArchiveApp(root)

            self.assertEqual(len(app.records), 1)
            self.assertEqual(app.records[0]["episode_number"], 1)
            self.assertEqual(app.snapshot()[0], app.records)


if __name__ == "__main__":
    unittest.main()
