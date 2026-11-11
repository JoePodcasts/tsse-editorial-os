"""Compile the private proposal and verify every retained source span."""
import argparse
from collections import Counter, defaultdict
import json
import re
from corpus import HERE, ROOT, archive, corpus, search
from discover import candidates
from archive_web import ArchiveApp

def read(name):
    return json.loads((HERE / name).read_text())

def generate():
    episodes, docs = corpus()
    themes = read("catalogue.json")
    selections = read("selections.json")
    guests = read("episode-guests.json")
    edges = read("relationships.json")
    ids = [t["id"] for t in themes]
    if len(set(ids)) != len(ids) or any(not re.fullmatch("[a-z]+(?:-[a-z]+)*", k) for k in ids):
        raise ValueError("Duplicate or invalid slug")
    if any(t["review_status"] != "proposed" or t["reviewer"] or t["reviewed_at"] for t in themes):
        raise ValueError("Discovery package must contain only proposals")
    screen = Counter()
    for row in candidates():
        screen[docs[row["passage"]]["episode_id"]] += 1
    evidence = {}
    associations = defaultdict(list)
    for s in selections:
        k, pid = s["theme"], s["passage_id"]
        doc = docs[pid]
        eid = doc["episode_id"]
        start, end = s["span"]
        if not (k in ids and 0 <= start < end <= len(doc["text"])):
            raise ValueError("Invalid selection")
        search.verify_document(ROOT / "archive", doc)
        quote = doc["text"][start:end]
        # Only an explicit time at the start of this exact excerpt locates it.
        time = archive.TIME_RE.match(quote)
        evidence[pid] = dict(episode_id=eid, excerpt=quote, excerpt_span=s["span"],
                             speaker=doc["speaker_label"] or "unknown",
                             start_timestamp=time.group() if time else None, end_timestamp=None,
                             verification="exact-text-verified; audio-unverified",
                             internal_url=ArchiveApp.episode_url(episodes[eid]) + "/transcript?passage=" + pid)
        associations[k,eid].append(s)
    for edge in edges:
        if len(edge["themes"]) != 2 or len(edge["passage_ids"]) != 2 or len(set(edge["themes"])) != 2:
            raise ValueError("Invalid theme relationship")
        for k,pid in zip(edge["themes"],edge["passage_ids"]):
            if not any(s["theme"]==k and s["passage_id"]==pid for s in selections):
                raise ValueError("Unresolved relationship")
    inventory = {}
    counts = Counter()
    for eid,r in sorted(episodes.items(), key=lambda pair:pair[1]["published_at"]):
        tags = [k for k in ids if (k,eid) in associations]
        counts[len(tags)] += 1
        inventory[eid] = dict(number=r["episode_number"], title=r["official_title"], published_at=r["published_at"],
                              source_url=r["episode_url"], guest_names=guests.get(eid), themes=tags,
                              candidate_hits=screen[eid], outcome="associated" if tags else "no_retained_evidence")
    mapping = []
    for (k,eid), rows in associations.items():
        classes = {s["classification"] for s in rows}
        strengths = {s["strength"] for s in rows}
        if strengths - {"strong","contextual"} or classes - {"supporting","contrasting","qualifying"}:
            raise ValueError("Invalid association")
        strength = "strong" if "strong" in strengths else "contextual"
        role = "contrast" if "contrasting" in classes else "related_context" if strength=="contextual" else "direct_support"
        mapping.append(dict(theme=k,episode_id=eid,strength=strength,role=role,passage_ids=[s["passage_id"] for s in rows]))
    report = ["# TSSE theme catalogue for editorial review", "",
              "Proposed for discussion • 11 November 2026 • discovery 1.0", "",
              "Descriptions, annotations and connections are editorial interpretations. Blockquotes reproduce transcript text. Episode guests come from the published summaries. Only the displayed source label identifies the speaker, and all labels await audio verification.", ""]
    coverage = ["# Coverage and quality", "", f"Screened {len(inventory)} episodes and {len(docs):,} transcript passages. Retained {len(evidence)} passages in {len(mapping)} episode–theme associations. {len(inventory)-counts[0]} episodes have an association, {sum(v for k,v in counts.items() if k>1)} have multiple, and {counts[0]} have no retained evidence. Of those without a retained passage, {sum(not r['candidate_hits'] and not r['themes'] for r in inventory.values())} had no lexical hit. A screen hit alone never earns an association.", "",
                "|Theme|Strong|Contextual|Episode guests|Distinct known source labels|First to latest|","|---|---:|---:|---:|---:|---|"]
    for t in themes:
        k=t["id"]
        rows=[m for m in mapping if m["theme"]==k]
        rows.sort(key=lambda m:inventory[m["episode_id"]]["published_at"])
        related=[inventory[m["episode_id"]] for m in rows]
        total_guests=len({g for r in related for g in r["guest_names"]})
        named={evidence[pid]["speaker"] for m in rows for pid in m["passage_ids"]} - {"unknown"}
        strong=sum(m["strength"]=="strong" for m in rows)
        period=related[0]["published_at"][:10]+" to "+related[-1]["published_at"][:10]
        coverage.append(f"|{t['name']}|{strong}|{len(rows)-strong}|{total_guests}|{len(named)}|{period}|")
        report.extend([f"## {t['name']}", "", t["proposition"], "",t["description"], "",
                       t["editorial_question"], "",f"{strong} strong and {len(rows)-strong} contextual episodes · {total_guests} episode guests · {len(named)} distinct named passage labels · {period}.", "",
                       "### Conversations and evidence",""])
        for m in rows:
            r=inventory[m["episode_id"]]
            report.extend([f"**Episode {r['number']} · [{r['title'].strip()}]({r['source_url']})** — {', '.join(r['guest_names'])} · {r['published_at'][:10]} · {m['strength']}", ""])
            for s in associations[k,m["episode_id"]]:
                p=evidence[s["passage_id"]]
                report.extend(["> "+p["excerpt"], "", f"{s['classification'].capitalize()} · source label {p['speaker']} · {s['relevance']} [Open transcript passage](https://tsse-editorial-os.vercel.app{p['internal_url']})", ""])
        report.extend(["### Connections",""])
        for edge in edges:
            if k in edge["themes"]:
                refs=[str(inventory[evidence[pid]["episode_id"]]["number"]) for pid in edge["passage_ids"]]
                report.extend([edge["interpretation"]+" (Episodes "+", ".join(dict.fromkeys(refs))+")",""])
        report.extend(["### Possible assignments","", *["- "+idea for idea in t["opportunities"]], "",
                       f"Decision pending · `{k}` · proposed. Record reviewer, date and notes in a separate decision record.", ""])
    unresolved=sum(p["speaker"]=="unknown" for p in evidence.values())
    coverage.extend(["",f"{unresolved} retained excerpts have no local speaker label. All {len(mapping)} associations await editorial review. Named episode guests measure breadth of conversations, not verified voices. The lexical screen and diversity sampling limit recall. No retained evidence means no accepted selection in this version.", "",
                     "### Episodes requiring another look","",", ".join(str(r["number"]) for r in inventory.values() if not r["themes"]),""])
    usable = set()
    overtime = set()
    for doc in docs.values():
        eid = doc["episode_id"]
        duration = episodes[eid]["duration_seconds"]
        for marker in archive.TIME_RE.finditer(doc["text"]):
            h, m, sec = map(int, marker.groups())
            seconds = h * 3600 + m * 60 + sec
            if m < 60 and sec < 60 and 0 < seconds <= duration:
                usable.add(eid)
            if seconds > duration:
                overtime.add(eid)
    manifest=dict(episodes_with_in_range_time=len(usable),
                  episodes_with_out_of_duration_markers=sorted(overtime),schema_version=1,discovery_version="1.0",passage_method=search.VERSION,
                  source_fingerprint=search.source_fingerprint(ROOT/"archive"),episodes=len(episodes),
                  transcript_passages=len(docs),candidate_hits=sum(screen.values()),curated_passages=len(evidence))
    return {"review.md":"\n".join(report),"coverage.md":"\n".join(coverage),
            **{k:json.dumps(v,ensure_ascii=False,indent=2)+"\n" for k,v in {
                "inventory.json":inventory,"evidence.json":evidence,"associations.json":mapping,"manifest.json":manifest}.items()}}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    for name,body in generate().items():
        path=HERE/"proposed"/name
        if args.check:
            if path.read_text()!=body:
                raise SystemExit(f"Stale output: {name}")
        else:
            path.parent.mkdir(exist_ok=True)
            path.write_text(body)
