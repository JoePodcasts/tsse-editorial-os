"""Build the review-only category proposal from versioned official sources."""
import argparse
from collections import defaultdict
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from corpus import ROOT, archive, corpus, search
from archive_web import ArchiveApp

VERSION = "1B.1"
PROPOSAL = dict(review_status="proposed", reviewer=None, reviewed_at=None, review_notes="")
SPAN = re.compile(r"[^.!?\n]+(?:[.!?]+|$)")
NOTE_END = re.compile(r"^\s*(?:#+\s*)?(?:about (?:the |our )?(?:guest|[A-Z])|next week|non.?profit|subscribe)",re.I)
BOILER = re.compile(r"welcome to (?:the )?sure shot|in this episode you|next week.s episode|subscribe to|my guest today|today.s guest",re.I)

def read(path):
    return json.loads((HERE/path).read_text())

def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+"\n").encode()

def compile_rules():
    return {cat:[(label,re.compile(r"\b(?:"+anchor+")",re.I),re.compile(r"\b(?:"+context+")",re.I))
                 for label,(anchor,context) in facets.items()]
            for cat,facets in read("signals.json").items()}

def spans(text):
    for m in SPAN.finditer(text):
        q = m.group().strip()
        if 65 <= len(q) <= 700 and not q.endswith("?") and not BOILER.search(q):
            yield text.index(q,m.start()),q

def hits(doc, rules):
    for start,quote in spans(doc["text"]):
        for cat,facets in rules.items():
            for label,anchor,context in facets:
                if not anchor.search(quote):
                    continue
                detail = set(m.group().lower() for m in context.finditer(anchor.sub("",quote)))
                if detail:
                    yield cat, dict(pid=doc["passage_id"], start=start, quote=quote, facet=label,
                                    pos=doc["locator"]["start"]+start,
                                    rank=min(len(detail),4) + int(len(quote)>130))

def separated(items):
    chosen=[]
    for h in sorted(items,key=lambda h:(-h["rank"],h["pos"],h["pid"])):
        if all(h["pid"]!=o["pid"] and abs(h["pos"]-o["pos"])>=800 for o in chosen):
            chosen.append(h)
    return chosen

def sources():
    eps,transcripts=corpus()
    manifest=archive.read_json(ROOT/"archive/manifest.json")
    notes={}
    for eid,r in eps.items():
        for d in search.source_documents(ROOT/"archive",r,manifest[eid]["show_notes"],"show_notes"):
            notes[d["passage_id"]]=d
    return eps,transcripts,notes

def evidence_record(h,d,record):
    pos=h["start"]
    quote=h["quote"]
    if d["text"][pos:pos+len(quote)]!=quote:
        raise ValueError(f"Excerpt mismatch: {h['pid']}")
    time=archive.TIME_RE.match(quote)
    return dict(passage_id=h["pid"],episode_id=d["episode_id"],excerpt=quote,passage_offset=pos,
                speaker_label=d.get("speaker_label") or "unknown",
                start_timestamp=time.group() if time else None,end_timestamp=None,
                internal_link=ArchiveApp.episode_url(record)+"/transcript?passage="+h["pid"],
                verification="canonical_text_verified_audio_unverified")

def generate():
    eps,docs,notes=sources()
    categories=read("taxonomy.json")
    category_names={c["id"]:c["name"] for c in categories}
    rules=compile_rules()
    links=read("theme-links.json")
    prev=read("../selections.json")
    if set(rules)!=set(category_names) or any(c["editorial_status"]!="approved" for c in categories):
        raise ValueError("Invalid taxonomy inputs")
    phase1={(s["theme"],s["passage_id"]):s for s in prev}
    for edge in links:
        refs=[phase1[edge["theme_id"],pid] for pid in edge["passage_ids"]]
        if (not refs or edge["category_id"] not in rules or edge["review_status"]!="proposed"
                or archive.digest(encoded(refs))!=edge["evidence_fingerprint"]):
            raise ValueError("Invalid category–theme proposal")
    grouped=defaultdict(list)
    for d in docs.values():
        grouped[d["episode_id"]].append(d)
    by_note=defaultdict(list)
    for d in notes.values():
        by_note[d["episode_id"]].append(d)
    existing=defaultdict(list)
    for edge in links:
        for s in prev:
            if s["theme"]!=edge["theme_id"] or s["passage_id"] not in edge["passage_ids"]:
                continue
            pid=s["passage_id"]
            d=docs[pid]
            a,b=s["span"]
            existing[d["episode_id"],edge["category_id"]].append(dict(
                pid=pid,start=a,quote=d["text"][a:b],pos=d["locator"]["start"]+a,
                rank=10,facet=edge["facet"],reason=s["relevance"]))
    overrides={(r["episode_id"],r["category_id"]):r for r in read("context-review.json")}
    if len(overrides)!=len(read("context-review.json")):
        raise ValueError("Duplicate contextual decision")
    for (eid,cat),row in overrides.items():
        if eid not in eps or cat not in category_names or row["strength"] not in {"strong","secondary","insufficient"}:
            raise ValueError("Invalid contextual decision")
    assignments=[]
    evidence={}
    inventory=[]
    for eid,ep in sorted(eps.items(),key=lambda p:p[1]["episode_number"]):
        candidates=defaultdict(list)
        editorial=defaultdict(list)
        for d in sorted(by_note[eid],key=lambda d:d["locator"]["start"]):
            if NOTE_END.match(d["text"].strip()):
                break
            for cat,facets in rules.items():
                if any(a.search(d["text"]) for _,a,_ in facets):
                    editorial[cat].append(d["passage_id"])
        length=max(d["locator"]["end"] for d in grouped[eid])
        for d in grouped[eid]:
            if d["locator"]["end"] < max(350,length*.06) or d["locator"]["start"] > length*.96:
                continue
            for cat,h in hits(d,rules):
                candidates[cat].append(h)
        assigned=[]
        for cat,facets in rules.items():
            prior=existing[eid,cat]
            matched=separated(candidates[cat])
            topical=bool(editorial[cat]) or any(a.search(ep["official_title"]) for _,a,_ in facets)
            strong=topical and len(matched)>=3
            override=overrides.get((eid,cat))
            qualifies=strong or (topical and len(matched)>=2) or len(matched)>=7 or prior
            if override:
                qualifies=override["strength"]!="insufficient"
            if not qualifies:
                continue
            pool=prior+matched
            if override and "passage_id" in override:
                d=docs[override["passage_id"]]
                start,end=override["span"]
                if d["episode_id"]!=eid or not 0<=start<end<=len(d["text"]):
                    raise ValueError("Stale contextual evidence")
                pool=[dict(pid=d["passage_id"],start=start,quote=d["text"][start:end],
                           pos=d["locator"]["start"]+start,rank=20,facet=override["reason"])]+pool
            chosen=separated(pool)[:2]
            if not chosen:
                raise ValueError(f"Unsupported decision {eid} {cat}")
            if override and "reviewed_passage_ids" in override and override["reviewed_passage_ids"]!=[h["pid"] for h in chosen]:
                raise ValueError(f"Contextual interpretation needs re-review: {eid} {cat}")
            strength=override["strength"] if override else "strong" if strong else "secondary"
            refs=[]
            for h in chosen:
                p=evidence_record(h,docs[h["pid"]],ep)
                key=f"{h['pid']}@{h['start']}+{len(h['quote'])}"
                evidence[key]=p
                refs.append(key)
            reason=chosen[0].get("reason") or "The cited discussion covers "+" and ".join(dict.fromkeys(h["facet"] for h in chosen))+"."
            if override:
                reason=override["reason"]
            # Prefer note references that share content words with the actual evidence.
            words=set(re.findall(r"[a-z]{5,}"," ".join(h["quote"] for h in chosen).lower()))
            note_ids=sorted(editorial[cat],key=lambda pid: -len(words.intersection(
                re.findall(r"[a-z]{5,}",notes[pid]["text"].lower()))))[:2]
            assigned.append(cat)
            assignments.append(dict(episode_id=eid,episode_number=ep["episode_number"],category_id=cat,
                category_name=category_names[cat],strength=strength,rationale=reason,
                evidence=refs,supporting_passage_ids=[h["pid"] for h in chosen],
                show_note_passage_ids=note_ids,independent_windows=len(matched),
                prior_theme_evidence=bool(prior),context_review=bool(override),
                evidence_classification="supporting",verification_status="source_verified_relevance_proposed",
                classification_version=VERSION,evidence_fingerprint=archive.digest(encoded([[evidence[k] for k in refs],note_ids])),
                **PROPOSAL))
        inventory.append(dict(episode_id=eid,episode_number=ep["episode_number"],title=ep["official_title"].strip(),
                              source_url=ep["episode_url"],categories=assigned,outcome="proposed" if assigned else "unclassified_for_review"))
    snapshot=dict(classification_version=VERSION,archive_fingerprint=search.source_fingerprint(ROOT/"archive"),
                  episodes=len(eps),official_transcripts=len(grouped),published_show_notes=len(by_note),
                  transcript_passages=len(docs),show_note_passages=len(notes))
    return dict(inventory=inventory,associations=assignments,evidence=evidence,manifest=snapshot)

if __name__=="__main__":
    from reports import render
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    data=generate()
    files={k+".json":encoded(v) for k,v in data.items()}
    files.update({k:v.encode() for k,v in render(data).items()})
    for name,body in files.items():
        path=HERE/"proposed"/name
        if args.check:
            if path.read_bytes()!=body:
                raise SystemExit("Stale classification file: "+name)
        else:
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(body)
