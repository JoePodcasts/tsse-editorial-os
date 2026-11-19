"""Phase 3C.1B: evidence-grounded follow-up regressions."""
import unittest
from pathlib import Path

import archive_guide as guide
from archive_public import PublicArchiveApp

ROOT = Path(__file__).resolve().parents[2]
PID = "5f1fdc059bbb5ef1d599d67ddc1750f5a02d44b5c66b61aa479d5170a8fb1792"


class EvidenceFollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = PublicArchiveApp(ROOT / "vercel_runtime/archive")
        cls.record = next(
            r for r in cls.app.records
            if r["episode_number"] == 110
        )
        cls.identity = cls.record["episode_id"]

    def choices(self):
        passage = self.app.passage(PID)
        return [{
            **guide.metadata(self.record),
            "evidence": [{
                "id": PID,
                "text": passage["text"],
                "context": passage["context"]["text"],
                "url": "/episodes/" + self.record["remote_id"]
                       + "/transcript?passage=" + PID,
                "speaker": passage["speaker_label"],
                "speaker_attribution": passage.get("speaker_attribution")
            }]
        }]

    def test_accepts_verified_evidence(self):
        response = {
            "answer": {
                "text": "David Thacker associates integrity with ethical conduct and a desire to improve lives.",
                "passage_ids": [PID]
            }
        }
        answer = guide.grounded_answer(
            self.app, response, self.choices()
        )
        self.assertIsNotNone(answer)
        self.assertEqual(answer["sources"][0]["id"], PID)
        verified = self.app.passage(PID)

        self.assertEqual(
            answer["sources"][0]["speaker"],
            verified.get("speaker_label")
        )
        self.assertEqual(
            answer["sources"][0]["attribution"],
            verified.get("speaker_attribution", "unknown")
        )

    def test_rejects_fabricated_passage(self):
        response = {
            "answer": {
                "text": "An unsupported answer.",
                "passage_ids": ["0" * 64]
            }
        }
        self.assertIsNone(
            guide.grounded_answer(
                self.app, response, self.choices()
            )
        )

    def test_rejects_answer_without_evidence(self):
        response = {
            "answer": {
                "text": "A claim without supporting evidence.",
                "passage_ids": []
            }
        }
        self.assertIsNone(
            guide.grounded_answer(
                self.app, response, self.choices()
            )
        )

    def test_followup_retrieval_preserves_previous_passage(self):
        choices, _ = guide.retrieve_discovery(
            self.app,
            "Can you give me an example?",
            "What do investors look for in founders?",
            [self.identity],
            True,
            False,
            [PID]
        )
        cited = [
            evidence["id"]
            for choice in choices
            for evidence in choice["evidence"]
        ]
        self.assertIn(PID, cited)


    def test_natural_followups_and_topic_switch(self):
        from unittest.mock import patch

        state = {
            "topic": "What do investors look for in startup founders?",
            "episode_ids": [self.identity],
            "passage_ids": [PID]
        }

        scenarios = [
            ("What signs indicate a founder has high integrity?", "follow-up"),
            ("Can you give me an example?", "follow-up"),
            ("Actually, I want to explore artificial intelligence startups.", "discover"),
        ]

        with patch.dict("os.environ", {"TSSE_CHAT_MODE": "mock"}):
            for question, expected in scenarios:
                with self.subTest(question=question):
                    reply = guide.answer(self.app, {
                        "question": question,
                        "state": state
                    })
                    self.assertEqual(
                        reply["state"]["intent"], expected
                    )
                    if expected == "follow-up":
                        self.assertEqual(
                            reply["topic"], state["topic"]
                        )


    def test_example_retrieval_includes_ava_mission(self):
        choices, _ = guide.retrieve_discovery(
            self.app,
            "Can you give me an example?",
            "What do investors look for in startup founders?",
            [self.identity],
            True,
            False,
            [PID]
        )

        evidence = [
            e for c in choices
            if c["episode"] == 110
            for e in c["evidence"]
        ]

        self.assertIn(PID, [e["id"] for e in evidence])
        self.assertTrue(any(
            "Ava" in e["text"]
            and "mission" in e["text"].lower()
            for e in evidence
        ))
        self.assertLessEqual(len(evidence), 4)


    def test_three_turn_evidence_continuity(self):
        from unittest.mock import patch

        ava = (
            "00fa654dc64155213aca464c8aa73b2e3adc1f6fb86ce5ae8dc06b477e0b014a"
        )

        questions = [
            "What do investors look for in startup founders?",
            "What signs indicate a founder has high integrity?",
            "Can you give me an example?"
        ]

        def fake_model(instructions, data, token_limit):
            number = questions.index(data["question"])

            offered = {
                evidence["id"]
                for candidate in data["candidates"]
                if candidate["episode_id"] == self.identity
                for evidence in candidate["evidence"]
            }

            self.assertIn(PID, offered)

            if number == 0:
                return {
                    "answer": {
                        "text": "",
                        "passage_ids": []
                    },
                    "recommendations": [{
                        "episode_id": self.identity,
                        "passage_ids": [PID],
                        "description": "This conversation discusses how investors evaluate founders."
                    }],
                    "suggestions": [questions[1]]
                }

            if number == 1:
                return {
                    "answer": {
                        "text": "Integrity involves ethical conduct and wanting to improve lives.",
                        "passage_ids": [PID]
                    },
                    "recommendations": [],
                    "suggestions": [questions[2]]
                }

            self.assertIn(ava, offered)

            return {
                "answer": {
                    "text": "Ava illustrates mission-driven investing, not proof of founder integrity.",
                    "passage_ids": [PID, ava]
                },
                "recommendations": [],
                "suggestions": []
            }

        state = {}
        history = []

        with (
            patch.dict("os.environ", {"TSSE_CHAT_MODE": "live"}),
            patch.object(guide.limits, "rate"),
            patch.object(guide, "complete", side_effect=fake_model) as model
        ):
            for number, question in enumerate(questions):
                reply = guide.answer(self.app, {
                    "question": question,
                    "history": history,
                    "state": state
                })

                state = reply["state"]
                history.append({"question": question})

                self.assertEqual(
                    state["intent"],
                    "discover" if number == 0 else "follow-up"
                )
                self.assertIn(self.identity, state["episode_ids"])

                if number > 0:
                    self.assertIsNotNone(reply["answer"])
                    self.assertFalse(reply["recommendations"])

            self.assertEqual(model.call_count, 3)

        self.assertIn(PID, state["passage_ids"])
        self.assertIn(ava, state["passage_ids"])


if __name__ == "__main__":
    unittest.main()
