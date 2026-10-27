#!/usr/bin/env python3
"""Offline lexical retrieval with exact source passages. No semantic ranking."""
import argparse
import hashlib
import json
import re
import sqlite3
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path

import archive_sync as a

VERSION = 'lexical-v2'
LABEL = r"[A-Z\u00c0-\u00de][A-Za-z .’\u00c0-\u017f\-]{0,79}"
TURN = re.compile(r'(?m)^[ \t]*(?:\[\d{2}:\d{2}:\d{2}\]\s*)?('+LABEL+r'):|\[\d{2}:\d{2}:\d{2}\]\s*('+LABEL+r'):')
BOOST = {'episode_title':20,'episode_number':20,'speaker_labels':15,'short_description':8,
         'published_at':8,'show_notes':5,'transcript':2}


def turns(text):
    for match in TURN.finditer(text):
        if a.plausible_label(match.group(1) or match.group(2)):
            yield match


def natural_spans(text, max_length=1800):
    boundaries={0,len(text)}
    boundaries.update(m.end() for m in re.finditer(r'\n\s*\n',text))
    boundaries.update(m.start() for m in turns(text))
    points=sorted(boundaries)
    for left,right in zip(points,points[1:]):
        # Long unlabeled source blocks get sentence-boundary fallbacks. A single
        # oversized sentence falls back to whitespace; no text is rewritten.
        while right-left>max_length:
            candidates=[m.end() for m in re.finditer(r'[.!?][\s]+',text[left:left+max_length])]
            cut=left+candidates[-1] if candidates else text.rfind(' ',left,left+max_length)
            if cut<=left:cut=min(left+max_length,right)
            if text[left:cut].strip():yield left,cut
            left=cut
        if text[left:right].strip():yield left,right


class Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.depth=0;self.parts=[];self.blocks=[]
    def handle_starttag(self,tag,attrs):
        if tag=='p':
            if self.depth==0:self.parts=[]
            self.depth+=1
        if tag=='br' and self.depth:self.parts.append('\n')
    def handle_data(self,data):
        if self.depth:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='p' and self.depth:
            self.depth-=1
            if self.depth==0:self.blocks.append(''.join(self.parts))


def structure(html,text):
    labels=list(turns(text));parser=Paragraphs();parser.feed(html);parser.close()
    multiple=any(len(list(turns(p)))>1 for p in parser.blocks)
    source_labels={(m.group(1) or m.group(2)).strip() for m in labels}
    candidates=list(re.finditer(r'(?m)^\s*(?:\[\d{2}:\d{2}:\d{2}\]\s*)?([^\n:\[\]]{1,80}):|\[\d{2}:\d{2}:\d{2}\]\s*([^\n:\[\]]{1,80}):',text))
    unknown_candidates=sorted({(m.group(1) or m.group(2)).strip() for m in candidates}-source_labels)
    line_labels=set(a.segments(text)[1]['speaker_labels']['raw_labels'])
    short_labels=sorted(label for label in source_labels if ' ' not in label.strip())
    return {'has_timestamps':bool(a.TIME_RE.search(text)), 'has_labels':bool(labels),
            'labels_parseable':bool(labels), 'raw_labels':sorted(source_labels),
            'all_colon_candidates_name_like':bool(candidates) and not unknown_candidates,
            'unparsed_label_candidates':unknown_candidates,
            'possible_label_candidates':len(candidates), 'short_source_labels':short_labels,
            'label_accuracy':'unverified', 'line_parser_missed_labels':sorted(source_labels-line_labels),
            'multiple_turns_single_paragraph':multiple,
            'unusual':multiple or not labels or source_labels!=line_labels or bool(short_labels) or max((len(p) for p in parser.blocks),default=0)>10000,
            'html_paragraphs':len(parser.blocks), 'source_turn_labels':len(labels),
            'untimed':not bool(a.TIME_RE.search(text))}


def source_documents(root,record,entry,kind):
    if not a.available(entry):return
    text=(root/entry['derived_text']['path']).read_bytes().decode('utf-8')
    source=entry['current_version']
    for start,end in natural_spans(text):
        excerpt=text[start:end]
        label=TURN.match(excerpt) if kind=='transcript' else None
        if label and not a.plausible_label(label.group(1) or label.group(2)):
            label=None
        times=list(a.TIME_RE.finditer(excerpt))
        locator={'source_id':entry['source_id'],'source_path':source['path'],'source_sha256':source['sha256'],
                 'source_field':entry['source_field'],'text_path':entry['derived_text']['path'],
                 'text_sha256':entry['derived_text']['sha256'],'start':start,'end':end,
                 'offset_unit':'unicode_codepoints','end_convention':'exclusive'}
        pid=a.digest(a.encoded([VERSION,record['episode_id'],kind,locator]))
        yield {'passage_id':pid,'episode_id':record['episode_id'],'episode_number':record['episode_number'],
               'title':record['official_title'],'episode_url':record['episode_url'],'source_type':kind,
               'text':excerpt,'locator':locator,'source_url':entry['source_url'],
               'timestamp':times[0].group() if times else None,
               'speaker_label':(label.group(1) or label.group(2)).strip() if label else None,
               'speaker_accuracy':'unverified' if kind=='transcript' else 'not_applicable','passage_method':VERSION}


def metadata_documents(root,record,entries):
    version=entries['metadata']['current_version']
    fields=[('episode_title','official_title','/title'),('episode_number','episode_number','/number'),
            ('published_at','published_at','/published_at'),('short_description','summary','/description')]
    for kind,key,field in fields:
        value=record[key]
        if value is None:continue
        yield {'passage_id':a.digest(a.encoded([VERSION,record['episode_id'],kind,version['sha256']])),
               'episode_id':record['episode_id'],'episode_number':record['episode_number'],
               'title':record['official_title'],'episode_url':record['episode_url'],'source_type':kind,
               'text':str(value),'locator':{'source_path':version['path'],'source_sha256':version['sha256'],
                                            'source_field':field},'speaker_label':None,'timestamp':None}
    t=entries['transcript']
    if a.available(t):
        transcript_text=(root/t['derived_text']['path']).read_bytes().decode('utf-8')
        labels=sorted({(m.group(1) or m.group(2)).strip() for m in turns(transcript_text)})
        if labels:
            yield {'passage_id':a.digest(a.encoded([VERSION,record['episode_id'],'speaker_labels',t['current_version']['sha256']])),
                   'episode_id':record['episode_id'],'episode_number':record['episode_number'],'title':record['official_title'],
                   'episode_url':record['episode_url'],'source_type':'speaker_labels','text':'\n'.join(labels),
                   'locator':{'source_path':t['current_version']['path'],'source_sha256':t['current_version']['sha256'],
                              'source_field':'/transcription','derivation':'syntactically_detected_source_labels'},
                   'speaker_label':None,'timestamp':None,'speaker_accuracy':'unverified'}


def source_fingerprint(root):
    return a.digest(a.encoded([VERSION,a.digest((root/'catalogue.jsonl').read_bytes()),
                              a.digest((root/'manifest.json').read_bytes())]))


def verify_document(root,doc):
    loc=doc['locator'];path=root/loc['source_path']
    if not path.resolve().is_relative_to(root.resolve()) or a.digest(path.read_bytes())!=loc['source_sha256']:
        raise ValueError('Search source hash/path mismatch')
    if 'text_path' in loc:
        path=root/loc['text_path'];raw=path.read_bytes()
        if not path.resolve().is_relative_to(root.resolve()) or a.digest(raw)!=loc['text_sha256']:
            raise ValueError('Search text projection hash/path mismatch')
        text=raw.decode('utf-8')
        if text[loc['start']:loc['end']]!=doc['text']:raise ValueError('Search passage source span mismatch')
    elif doc['source_type'] != 'speaker_labels':
        data=json.loads(path.read_bytes())
        field=loc['source_field'].lstrip('/')
        if str(data[field])!=doc['text']:raise ValueError('Search metadata field mismatch')
    return True


def rebuild(root):
    root=Path(root).resolve();started=time.perf_counter()
    with a.lock(root):
        a.validate(root)
        records=a.load_catalogue(root/'catalogue.jsonl');manifest=a.read_json(root/'manifest.json')
        documents=[];passages=[]
        for record in records:
            if record['public_presence']!='present':continue
            entries=manifest[record['episode_id']]
            documents.extend(metadata_documents(root,record,entries))
            for kind in ('show_notes','transcript'):
                passages.extend(source_documents(root,record,entries[kind],kind))
        documents.extend(passages);documents.sort(key=lambda d:d['passage_id']);passages.sort(key=lambda d:d['passage_id'])
        for doc in documents:verify_document(root,doc)
        payload=''.join(json.dumps(d,ensure_ascii=False,sort_keys=True)+'\n' for d in documents)
        a.write(root/'derived/search-documents.jsonl',payload)
        a.write(root/'derived/passages.jsonl',''.join(json.dumps(d,ensure_ascii=False,sort_keys=True)+'\n' for d in passages))
        fingerprint=source_fingerprint(root)
        corpus_hash=a.digest(payload.encode('utf-8'))
        index=root/'search/archive.sqlite3';index.parent.mkdir(exist_ok=True)
        old_report=a.read_json(root/'reports/search-index.json',{})
        unchanged=(old_report.get('input_fingerprint')==fingerprint and old_report.get('corpus_sha256')==corpus_hash
                   and index.exists() and a.digest(index.read_bytes())==old_report.get('index_sha256'))
        if not unchanged:
            with tempfile.TemporaryDirectory(dir=index.parent) as tmp:
                path=Path(tmp)/'index.sqlite3';db=sqlite3.connect(path)
                db.execute('PRAGMA page_size=4096')
                db.execute('CREATE TABLE documents (id INTEGER PRIMARY KEY, passage_id TEXT UNIQUE NOT NULL, episode_id TEXT NOT NULL, episode_number INTEGER, source_type TEXT NOT NULL, payload TEXT NOT NULL)')
                db.execute("CREATE VIRTUAL TABLE lexicon USING fts5(text, tokenize='unicode61 remove_diacritics 2')")
                for i,doc in enumerate(documents,1):
                    db.execute('INSERT INTO documents VALUES (?,?,?,?,?,?)',(i,doc['passage_id'],doc['episode_id'],doc['episode_number'],doc['source_type'],json.dumps(doc,ensure_ascii=False,sort_keys=True)))
                    db.execute('INSERT INTO lexicon(rowid,text) VALUES (?,?)',(i,doc['text']))
                db.execute('CREATE TABLE provenance (input_fingerprint TEXT, corpus_sha256 TEXT)')
                db.execute('INSERT INTO provenance VALUES (?,?)',(fingerprint,corpus_hash));db.commit();db.close()
                if index.exists() and index.read_bytes()==path.read_bytes():pass
                else:path.replace(index)
        counts={'searchable_metadata_records':len({d['episode_id'] for d in documents if d['source_type'] not in ('transcript','show_notes')}),
                'searchable_transcript_passages':sum(d['source_type']=='transcript' for d in passages),
                'searchable_transcript_episodes':len({d['episode_id'] for d in passages if d['source_type']=='transcript'}),
                'searchable_show_note_documents':len({d['episode_id'] for d in passages if d['source_type']=='show_notes'}),
                'searchable_show_note_passages':sum(d['source_type']=='show_notes' for d in passages)}
        report={'schema_version':1,'method':VERSION,'input_fingerprint':fingerprint,'corpus_sha256':corpus_hash,
                'index_sha256':a.digest(index.read_bytes()),'index_bytes':index.stat().st_size,
                'documents':len(documents),**counts}
        a.write(root/'reports/search-index.json',a.encoded(report))
    return {**report,'build_seconds':round(time.perf_counter()-started,3),'index_reused':unchanged}


def connect(root):
    path=(root/'search/archive.sqlite3').resolve()
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    fingerprint=db.execute('SELECT input_fingerprint FROM provenance').fetchone()[0]
    if fingerprint!=source_fingerprint(root):db.close();raise ValueError('Search index is stale; rebuild from current archive')
    return db


def query(root,text,source='all',episode=None,limit=5,phrase=False):
    root=Path(root).resolve();tokens=re.findall(r'[^\W_]+',text,flags=re.UNICODE)
    if not tokens:return []
    expression='"'+' '.join(tokens)+'"' if phrase else ' AND '.join('"'+x+'"' for x in tokens)
    db=connect(root)
    try:
        sql='SELECT d.payload,bm25(lexicon) FROM lexicon JOIN documents d ON d.id=lexicon.rowid WHERE lexicon MATCH ?'
        args=[expression]
        if source=='metadata':
            sql+=" AND d.source_type NOT IN ('transcript','show_notes')"
        elif source!='all':sql+=' AND d.source_type=?';args.append(source)
        if episode is not None:sql+=' AND d.episode_number=?';args.append(episode)
        rows=db.execute(sql,args).fetchall();results=[]
        for payload,bm in rows:
            doc=json.loads(payload)
            exact=' '.join(tokens).casefold() in doc['text'].casefold()
            score=BOOST[doc['source_type']] + (8 if exact else 0) - bm
            doc['ranking']={'field_boost':BOOST[doc['source_type']],'exact_phrase_bonus':8 if exact else 0,
                            'bm25_relevance':-bm,'score':score,'match_rule':'phrase' if phrase else 'all_tokens_in_same_passage'}
            results.append(doc)
        results.sort(key=lambda d:(-d['ranking']['score'],d['episode_number'] if d['episode_number'] is not None else -1,d['passage_id']))
        return [with_context(root,d) for d in results[:limit]]
    finally:db.close()


def with_context(root,doc):
    verify_document(root,doc)
    loc=doc['locator']
    if 'text_path' in loc:
        text=(root/loc['text_path']).read_bytes().decode('utf-8');left=max(0,loc['start']-300);right=min(len(text),loc['end']+300)
        doc['context']={'text':text[left:right],'start':left,'end':right,'match_start':loc['start'],'match_end':loc['end']}
    return doc


def context(root,pid):
    root=Path(root).resolve();db=connect(root)
    try:
        row=db.execute('SELECT payload FROM documents WHERE passage_id=?',(pid,)).fetchone()
        if not row:raise ValueError('Unknown passage ID')
        return with_context(root,json.loads(row[0]))
    finally:db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('rebuild','search','context'));p.add_argument('text',nargs='?')
    p.add_argument('--output',type=Path,default=a.ROOT/'archive');p.add_argument('--source',default='all',choices=('all','metadata',*BOOST))
    p.add_argument('--episode',type=int);p.add_argument('--limit',type=int,default=5);p.add_argument('--phrase',action='store_true');p.add_argument('--json',action='store_true')
    args=p.parse_args()
    if args.limit<1:p.error('--limit must be positive')
    if args.command=='rebuild':print(json.dumps(rebuild(args.output),indent=2));return
    if not args.text:p.error('Supply query text or passage ID')
    results=[context(args.output,args.text)] if args.command=='context' else query(args.output,args.text,args.source,args.episode,args.limit,args.phrase)
    if args.json:print(json.dumps(results,ensure_ascii=False,indent=2));return
    for d in results:
        print(f'Episode {d["episode_number"]}: {d["title"]}\nMatched source: {d["source_type"]}')
        if d['source_type']=='transcript':
            print(f'Timestamp: {d.get("timestamp") or "unavailable"}; speaker label: {d.get("speaker_label") or "unresolved"} (audio-unverified)')
        if 'context' in d:
            print('Source context (exact text; matched span is identified by the locator):')
            print(d['context']['text'])
        else:
            print(d['text'])
        print('Locator:',json.dumps(d['locator'],ensure_ascii=False));print('Passage ID:',d['passage_id'])
        if 'ranking' in d:print('Ranking:',json.dumps(d['ranking']))
        print()
    if not results:print('No lexical matches.')


if __name__=='__main__':main()
