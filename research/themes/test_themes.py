"""Snapshot contract and consumer joins. Run from the repository root."""
import json
import re
import unittest
from collections import Counter
from corpus import ROOT, HERE, archive, corpus
from build import generate, read
from archive_web import ArchiveApp

class ProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.episodes, cls.docs = corpus()
        cls.inventory = read("proposed/inventory.json")
        cls.evidence = read("proposed/evidence.json")
        cls.associations = read("proposed/associations.json")
        cls.themes = read("catalogue.json")

    def test_generated_files_reproduce(self):
        for name, body in generate().items():
            with self.subTest(name=name):
                self.assertEqual((HERE/"proposed"/name).read_text(),body)

    def test_inventory_and_current_source_counts(self):
        actual = {r["episode_id"] for r in map(json.loads,(ROOT/"archive/catalogue.jsonl").read_text().splitlines()) if r["public_presence"]=="present"}
        self.assertEqual(actual, set(self.inventory))
        snapshot = read("proposed/manifest.json")
        self.assertEqual(snapshot["episodes"],len(actual))
        self.assertEqual(snapshot["transcript_passages"],len(self.docs))

    def test_unique_frozen_theme_ids_and_review_gate(self):
        # Changing an identifier breaks future bookmarks and decision history.
        frozen = set("portfolio-breadth earning-trust customer-proof financing-milestones pitch-clarity capital-geography talent-as-leverage founder-insight distribution-partners".split())
        self.assertCountEqual([t["id"] for t in self.themes], frozen)
        for theme in self.themes:
            self.assertEqual(theme["review_status"],"proposed")
            self.assertIsNone(theme["reviewer"])
            self.assertIsNone(theme["reviewed_at"])
            self.assertEqual(len(theme["opportunities"]),3)

    def test_reader_can_join_associations_and_sources(self):
        sources = read("selections.json")
        pairs = set()
        refs = set()
        for row in self.associations:
            eid, k = row["episode_id"],row["theme"]
            self.assertNotIn((eid,k),pairs)
            pairs.add((eid,k))
            self.assertIn(k,self.inventory[eid]["themes"])
            self.assertIn(row["strength"],("strong","contextual"))
            self.assertIn(row["role"],("direct_support","related_context","contrast"))
            self.assertTrue(row["passage_ids"])
            for pid in row["passage_ids"]:
                p = self.evidence[pid]
                refs.add((k,pid))
                d = self.docs[pid]
                self.assertEqual(eid,d["episode_id"])
                self.assertEqual(eid,p["episode_id"])
                a,b = p["excerpt_span"]
                loc=d["locator"]
                canonical=(ROOT/"archive"/loc["text_path"]).read_bytes().decode()
                self.assertEqual(p["excerpt"],canonical[loc["start"]+a:loc["start"]+b])
                self.assertEqual(p["internal_url"],ArchiveApp.episode_url(self.episodes[eid])+"/transcript?passage="+pid)
                self.assertEqual(p["speaker"],d["speaker_label"] or "unknown")
                time = archive.TIME_RE.match(p["excerpt"])
                self.assertEqual(p["start_timestamp"],time.group() if time else None)
                self.assertIsNone(p["end_timestamp"])
        self.assertCountEqual(refs,[(s["theme"],s["passage_id"]) for s in sources])
        self.assertEqual(pairs,{(eid,k) for eid,r in self.inventory.items() for k in r["themes"]})
        self.assertTrue(any(len(r["themes"])>1 for r in self.inventory.values()))
        self.assertTrue(all(8<=n<=15 for n in Counter(s["theme"] for s in sources).values()))
        for edge in read("relationships.json"):
            self.assertTrue(all(pair in refs for pair in zip(edge["themes"],edge["passage_ids"])))

if __name__ == "__main__":
    unittest.main()
