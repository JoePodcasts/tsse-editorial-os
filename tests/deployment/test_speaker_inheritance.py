"""Regression tests for multi-paragraph transcript speaker attribution."""
import json
import unittest
from pathlib import Path

import archive_search as search
import archive_sync as sync

ROOT = Path(__file__).resolve().parents[2]


class SpeakerInheritanceTests(unittest.TestCase):

    def test_inherits_until_next_speaker(self):
        text = (
            "David Thacker: First observation.\n\n"
            "Second observation.\n\n"
            "Finally, founders need high integrity.\n\n"
            "Gopi Rangan: Another question.\n\n"
            "Next paragraph from Gopi."
        )
        spans = list(search.attributed_spans(text))
        actual = [
            (text[start:end].strip(), speaker, attribution)
            for start, end, speaker, attribution in spans
        ]
        self.assertEqual(
            [(speaker, attribution) for _, speaker, attribution in actual],
            [
                ("David Thacker", "explicit"),
                ("David Thacker", "inherited"),
                ("David Thacker", "inherited"),
                ("Gopi Rangan", "explicit"),
                ("Gopi Rangan", "inherited"),
            ],
        )

    def test_paragraph_before_first_label_is_unknown(self):
        text = (
            "Unattributed introduction.\n\n"
            "David Thacker: First labeled paragraph."
        )
        spans = list(search.attributed_spans(text))
        self.assertIsNone(spans[0][2])
        self.assertEqual(spans[0][3], "unknown")
        self.assertEqual(spans[1][2], "David Thacker")
        self.assertEqual(spans[1][3], "explicit")

    def test_no_change_to_passage_boundaries(self):
        text = (
            "Introduction.\n\n"
            "David Thacker: Discusses founders.\n\n"
            "Continues discussing integrity.\n\n"
            "Gopi Rangan: Next topic."
        )
        original = list(search.natural_spans(text))
        attributed = [
            (start, end)
            for start, end, _, _ in search.attributed_spans(text)
        ]
        self.assertEqual(attributed, original)

    def test_episode_110_integrity_and_stable_identity(self):
        archive = ROOT / "archive"
        records = sync.load_catalogue(archive / "catalogue.jsonl")
        record = next(
            r for r in records if r["episode_number"] == 110
        )
        manifest = json.loads(
            (archive / "manifest.json").read_text()
        )
        entry = manifest[record["episode_id"]]["transcript"]

        documents = list(
            search.source_documents(
                archive, record, entry, "transcript"
            )
        )
        target = next(
            doc for doc in documents
            if "Finally, look for founders that have super high integrity"
            in doc["text"]
        )

        self.assertEqual(target["speaker_label"], "David Thacker")
        self.assertEqual(
            target["speaker_attribution"], "inherited"
        )
        self.assertEqual(
            target["passage_id"],
            "5f1fdc059bbb5ef1d599d67ddc1750f5a02d44b5c66b61aa479d5170a8fb1792"
        )
        self.assertTrue(search.verify_document(archive, target))


if __name__ == "__main__":
    unittest.main()
