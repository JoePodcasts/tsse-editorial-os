"""Read official versioned sources through the production passage segmenter."""
import collections
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("TSSE_ROOT", HERE.parents[1])).resolve()
sys.path.insert(0, str(ROOT))
import archive_search as search
import archive_sync as archive

def corpus():
    root = ROOT / "archive"
    records = archive.load_catalogue(root / "catalogue.jsonl")
    manifest = archive.read_json(root / "manifest.json")
    episodes = {}
    passages = {}
    for record in records:
        if record["public_presence"] != "present":
            continue
        eid = record["episode_id"]
        entries = manifest[eid]
        for kind in ("transcript", "show_notes"):
            entry = entries[kind]
            for version in (entry["current_version"], entry["derived_text"]):
                if archive.digest((root / version["path"]).read_bytes()) != version["sha256"]:
                    raise ValueError(f"Invalid {kind} source for {eid}")
        episodes[eid] = record
        for doc in search.source_documents(root, record, entries["transcript"], "transcript"):
            passages[doc["passage_id"]] = doc
    return episodes, passages

def sentences(doc):
    # Never span multiple turns. Keep offsets into the original passage.
    for match in re.finditer(r'[^.!?\n]+(?:[.!?]+|$)', doc["text"]):
        value = match.group().strip()
        if 50 <= len(value) <= 650 and not value.endswith("?"):
            yield value

def phrases(episodes):
    counts = collections.Counter()
    for record in episodes.values():
        words = re.findall(r"[a-z]+", record["summary"].lower())
        counts.update(set(zip(words, words[1:])))
    return counts

if __name__ == "__main__":
    episodes, passages = corpus()
    print(len(episodes), len(passages))
    print(phrases(episodes).most_common(220))
