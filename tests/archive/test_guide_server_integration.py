"""Verify the normal archive server supplies records required by Ask."""
import unittest
from pathlib import Path
from unittest.mock import patch

from archive_web import ArchiveApp
from archive_guide import answer


ROOT = Path(__file__).resolve().parents[2]


class GuideServerIntegrationTests(unittest.TestCase):

    @unittest.skipUnless(
        (ROOT / "archive/search/archive.sqlite3").exists(),
        "Full archive index is not materialized"
    )
    def test_normal_archive_app_supports_ask(self):
        app = ArchiveApp(ROOT / "archive")

        records, _ = app.snapshot()
        self.assertEqual(app.records, records)
        self.assertTrue(records)

        with patch.dict("os.environ", {"TSSE_CHAT_MODE": "mock"}):
            result = answer(
                app,
                {"question": "What do investors look for in founders?"},
                client="local"
            )

        self.assertEqual(result["mode"], "mock")
        self.assertTrue(result["recommendations"])
        self.assertTrue(
            all(item["sources"] for item in result["recommendations"])
        )


if __name__ == "__main__":
    unittest.main()
