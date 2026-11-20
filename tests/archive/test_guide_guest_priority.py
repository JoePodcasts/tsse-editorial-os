"""Regression tests for Ask's guest-first evidence selection."""
import unittest
from unittest.mock import patch

from archive_guide import guest_evidence_priority, retrieve_discovery


class GuestPriorityTests(unittest.TestCase):
    def test_speaker_identification(self):
        guests = ["Maryanna Saenko"]
        cases = [
            ("Maryanna Saenko", "explicit", 1),
            ("Maryanna", "inherited", 1),
            ("Gopi Rangan", "explicit", 0),
            ("Unknown", "unknown", 0),
            (None, "unknown", 0),
            ("Another Speaker", "explicit", 0),
        ]
        for speaker, attribution, expected in cases:
            with self.subTest(speaker=speaker):
                result = guest_evidence_priority(
                    {
                        "speaker_label": speaker,
                        "speaker_attribution": attribution
                    },
                    guests
                )
                self.assertEqual(result, expected)

    def check_selection(self, speakers, expected):
        record = {
            "episode_id": "test-episode",
            "episode_number": 92,
            "remote_id": "test-remote",
            "official_title": "Test conversation",
            "episode_url": "https://podcast.sure.ventures/episodes/test",
            "summary": "Maryanna Saenko, investor, discusses startups."
        }

        class FakeArchive:
            records = [record]

            def __init__(self):
                self.passages = {}
                self.results = []
                for i, speaker in enumerate(speakers):
                    pid = f"passage-{i}"
                    item = {
                        "passage_id": pid,
                        "episode_id": record["episode_id"],
                        "text": "Relevant discussion about startups and investment. " * 4,
                        "url": f"/episodes/test-remote/transcript?passage={pid}"
                    }
                    self.results.append(item)
                    self.passages[pid] = {
                        **item,
                        "source_type": "transcript",
                        "speaker_label": speaker,
                        "speaker_attribution": "explicit" if speaker else "unknown"
                    }

            def query(self, params):
                return {"results": self.results}

            def passage(self, pid):
                return self.passages[pid]

        with patch("archive_guide.search_concepts", return_value=["investment"]):
            choices, _ = retrieve_discovery(
                FakeArchive(), "investment", "investment",
                [], False, False
            )

        actual = [e["speaker"] for e in choices[0]["evidence"]]
        self.assertEqual(actual, expected)

    def test_guest_beats_comparable_host(self):
        self.check_selection(
            ["Gopi Rangan", "Gopi Rangan", "Maryanna Saenko", None],
            ["Maryanna Saenko", "Gopi Rangan"]
        )

    def test_strong_host_remains_eligible(self):
        self.check_selection(
            ["Gopi Rangan", None, None, "Maryanna Saenko"],
            ["Gopi Rangan", "Maryanna Saenko"]
        )

    def test_unknown_attribution_remains_valid(self):
        self.check_selection(
            [None, "Gopi Rangan", None, None],
            [None, "Gopi Rangan"]
        )


if __name__ == "__main__":
    unittest.main()
