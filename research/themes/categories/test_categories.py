"""Validate the research dataset, its canonical joins and the review boundary."""
from collections import defaultdict
import unittest
from classify import (HERE, ROOT, archive, ArchiveApp, encoded, generate, read,
                      search, sources)
from reports import render

EXPECTED_NAMES = [
    "Fundraising & investor relationships", "Venture capital & investing",
    "Startup ideas & product-market fit", "Founder mindset & leadership",
    "Growth & go-to-market", "Artificial intelligence & emerging technologies",
    "Fintech, InsurTech & financial innovation", "Healthcare & industry transformation",
    "Entrepreneurship & startup ecosystems",
]

class CategoryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=generate()
        cls.episodes,cls.docs,cls.notes=sources()
        cls.cats=read("taxonomy.json")
        cls.rows=cls.data["associations"]
        cls.ev=cls.data["evidence"]

    def test_frozen_definitions(self):
        self.assertEqual([c["name"] for c in self.cats],EXPECTED_NAMES)
        self.assertEqual([c["id"] for c in self.cats],[f"cat-{n:02}" for n in range(1,10)])
        self.assertEqual([c["display_order"] for c in self.cats],list(range(1,10)))
        self.assertEqual(len({c["slug"] for c in self.cats}),9)
        for c in self.cats:
            self.assertRegex(c["slug"],r"^[a-z]+(?:-[a-z]+)*$")
            self.assertEqual(c["editorial_status"],"approved")
            self.assertTrue(c["scope"] and c["description"])

    def test_complete_canonical_inventory_and_associations(self):
        inv=self.data["inventory"]
        self.assertCountEqual([r["episode_id"] for r in inv],list(self.episodes))
        pairs=defaultdict(list)
        for a in self.rows:
            eid=a["episode_id"]
            pairs[eid].append(a["category_id"])
            self.assertEqual(a["episode_number"],self.episodes[eid]["episode_number"])
            self.assertIn(a["strength"],["strong","secondary"])
            self.assertEqual(a["category_name"],EXPECTED_NAMES[int(a["category_id"][4:])-1])
            self.assertTrue(a["rationale"])
        for r in inv:
            self.assertCountEqual(r["categories"],set(pairs[r["episode_id"]]))
            self.assertEqual(len(pairs[r["episode_id"]]),len(r["categories"]))
            self.assertEqual(r["outcome"],"proposed" if r["categories"] else "unclassified_for_review")
        self.assertTrue(any(len(r["categories"])>1 for r in inv))

    def test_all_references_are_local_to_the_episode_and_exact(self):
        for a in self.rows:
            eid=a["episode_id"]
            self.assertTrue(a["evidence"])
            records=[self.ev[k] for k in a["evidence"]]
            self.assertEqual(a["supporting_passage_ids"],[p["passage_id"] for p in records])
            for p in records:
                d=self.docs[p["passage_id"]]
                self.assertEqual(eid,d["episode_id"])
                self.assertEqual(eid,p["episode_id"])
                search.verify_document(ROOT/"archive",d)
                i=p["passage_offset"]
                self.assertEqual(p["excerpt"],d["text"][i:i+len(p["excerpt"])])
                self.assertEqual(p["speaker_label"],d["speaker_label"] or "unknown")
                time=archive.TIME_RE.match(p["excerpt"])
                self.assertEqual(p["start_timestamp"],time.group() if time else None)
                self.assertIsNone(p["end_timestamp"])
                self.assertEqual(p["internal_link"],ArchiveApp.episode_url(self.episodes[eid])+"/transcript?passage="+p["passage_id"])
            for pid in a["show_note_passage_ids"]:
                d=self.notes[pid]
                self.assertEqual(d["episode_id"],eid)
                search.verify_document(ROOT/"archive",d)
            self.assertEqual(a["evidence_fingerprint"],archive.digest(encoded([records,a["show_note_passage_ids"]])))

    def test_review_boundary_and_rejected_candidates(self):
        pairs={(a["episode_id"],a["category_id"]) for a in self.rows}
        for r in self.rows+read("theme-links.json"):
            self.assertEqual(r["review_status"],"proposed")
            self.assertIsNone(r["reviewed_at"])
            self.assertIsNone(r["reviewer"])
        for r in read("context-review.json"):
            self.assertEqual((r["episode_id"],r["category_id"]) in pairs,r["strength"]!="insufficient")

    def test_theme_links_preserve_selected_phase_one_evidence(self):
        themes=read("../catalogue.json")
        self.assertTrue(all(t["review_status"]=="proposed" for t in themes))
        edges=read("theme-links.json")
        self.assertCountEqual([e["theme_id"] for e in edges if e["relationship"]=="primary"],[t["id"] for t in themes])
        selected={(s["theme"],s["passage_id"]):s for s in read("../selections.json")}
        for e in edges:
            self.assertIn(e["category_id"],[c["id"] for c in self.cats])
            self.assertIn(e["relationship"],["primary","secondary"])
            self.assertTrue(e["passage_ids"])
            pinned=[selected[e["theme_id"],pid] for pid in e["passage_ids"]]
            self.assertEqual(archive.digest(encoded(pinned)),e["evidence_fingerprint"])

    def test_regeneration_and_publication_isolation(self):
        for name,value in self.data.items():
            self.assertEqual((HERE/"proposed"/(name+".json")).read_bytes(),encoded(value))
        for name,body in render(self.data).items():
            self.assertEqual((HERE/"proposed"/name).read_text(),body)
        for config in ("archive_deploy.py",".github/workflows/archive-sync.yml"):
            self.assertNotIn("research/themes/categories",(ROOT/config).read_text())

if __name__=="__main__":
    unittest.main()
