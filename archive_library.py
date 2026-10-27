#!/usr/bin/env python3
"""Resumable official detail ingestion and offline archive materialization."""
import argparse
import copy
import json
import shutil
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

import archive_sync as a


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_bytes(a.encoded(value))
    tmp.replace(path)


class PoliteAPI:
    def __init__(self, delay=0.5):
        self.delay = delay
        self.requests = 0
        self.last = 0

    def request(self, url, **kwargs):
        remaining = self.delay - (time.monotonic() - self.last)
        if remaining > 0:
            time.sleep(remaining)
        self.requests += 1
        try:
            return a.request_json(url, **kwargs)
        finally:
            self.last = time.monotonic()

    def __call__(self, url, **kwargs):
        return a.api(url, request=self.request, **kwargs)


def accepted_detail_matches(root, record, entries):
    entry = entries.get('detail', {})
    if not a.available(entry):
        return False
    path = root / entry['current_version']['path']
    try:
        data = a.read_json(path)
        return (a.digest(path.read_bytes()) == entry['current_version']['sha256']
                and a.digest(a.encoded(a.metadata(data))) == entries['metadata']['current_version']['sha256'])
    except (ValueError, KeyError, OSError, TypeError):
        return False


def safe_detail(data, record):
    if not isinstance(data, dict) or not {'long_description', 'transcription'}.issubset(data):
        raise ValueError('Malformed detail: explicit source fields are required (null is allowed)')
    if data.get('id') != record['remote_id'] or (data.get('podcast') or {}).get('id') != record['podcast_id']:
        raise ValueError('Remote detail identity/podcast mismatch')
    # Preserve approved strings, not operational fields or action URLs.
    return {**a.metadata(data), 'podcast': {'id': record['podcast_id']},
            'audio_content_type': data.get('audio_content_type'),
            'long_description': data.get('long_description'), 'transcription': data.get('transcription')}


def materialize(root, records, manifest):
    for record in records:
        eid = record['episode_id']
        entries = manifest[eid]
        entries['markdown_path'] = f'exports/episodes/{record["remote_id"]}.md'
        record.pop('record_revision', None)
        record['record_revision'] = a.digest(a.encoded(record))
        a.write(root / entries['markdown_path'], a.markdown(record, entries, root))
    records.sort(key=lambda r: r['episode_id'])
    a.write(root / 'catalogue.jsonl', ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in records))
    a.write(root / 'manifest.json', a.encoded(manifest))
    a.write(root / 'exports/catalogue.csv', a.csv_export(records, manifest))
    return a.validate(root)


def structural_report(root, records, manifest):
    # Import lazily to keep ingestion independent of index construction.
    from archive_search import structure
    results = []
    for r in records:
        if r['public_presence'] != 'present':
            continue
        entries = manifest[r['episode_id']]
        if a.available(entries['transcript']):
            entry = entries['transcript']
            html = (root / entry['current_version']['path']).read_bytes().decode('utf-8')
            text = (root / entry['derived_text']['path']).read_bytes().decode('utf-8')
            result = structure(html, text)
            from newsletter_production_pipeline_v1 import validate_transcript as legacy_validator
            result['legacy_strict_validator_accepts'] = legacy_validator(text)['valid']
            results.append({'episode_id': r['episode_id'], 'episode_number': r['episode_number'], **result})
    return results


def write_report(root, records, manifest, run=None):
    previous = a.read_json(root/'reports/latest.json', {})
    run = run or previous.get('ingestion', {})
    report = a.coverage(records, manifest, previous.get('changes', {}), run.get('failures', []), a.now())
    counts = report['coverage']
    counts['markdown_documents'] = counts.pop('pilot_exported')
    stats = structural_report(root, records, manifest)
    def total(key):
        return sum(bool(s[key]) for s in stats)
    counts.update(official_timestamped_transcripts=total('has_timestamps'),
                  official_speaker_labelled_transcripts=total('has_labels'),
                  parseable_speaker_labelled_transcripts=total('labels_parseable'),
                  unusual_transcript_formats=total('unusual'),
                  multiple_turns_single_html_paragraph=total('multiple_turns_single_paragraph'),
                  legacy_strict_validator_rejected=sum(not s['legacy_strict_validator_accepts'] for s in stats),
                  ambiguous_colon_prefix_transcripts=sum(bool(s['unparsed_label_candidates']) for s in stats))
    statuses = {}
    for kind in ('show_notes', 'transcript'):
        statuses[kind] = {}
        for r in records:
            if r['public_presence']=='present':
                state=manifest[r['episode_id']][kind]['availability']
                statuses[kind][state]=statuses[kind].get(state,0)+1
    index_report = a.read_json(root/'reports/search-index.json', {})
    if index_report:
        from archive_search import source_fingerprint
        index_report = {**index_report, 'status': 'current' if index_report.get('input_fingerprint') == source_fingerprint(root) else 'stale_rebuild_required'}
    report.update(ingestion=run, official_source_states=statuses, transcript_structure=stats,
                  search=index_report, validation=a.validate(root))
    a.write(root/'reports/latest.json', a.encoded(report))
    lines = ['# TSSE archive coverage', '', f'Published episodes: **{report["published_episodes"]}**. Catalogue records: **{report["catalogue_records"]}**.', '',
             '| Coverage | Episodes | Percent of published |', '|---|---:|---:|']
    for k,v in counts.items():
        lines.append(f'| {k.replace("_"," ")} | {v} | {100*v/report["published_episodes"]:.1f}% |')
    lines.extend(['', 'Official source availability:', '', a.fence(json.dumps(statuses,indent=2)),
                  'Speaker labels describe source text only. No speaker identity is audio-verified. Legacy and official source coverage overlap.', '',
                  '## Search coverage', '', a.fence(json.dumps(index_report,indent=2)),
                  '## Ingestion run', '', a.fence(json.dumps(run,indent=2)),
                  'Per-episode format diagnostics and actual retrieval/validation failures are in `latest.json`.'])
    a.write(root/'reports/latest.md', '\n'.join(lines)+'\n')
    return report


def publish(stage, output, backup):
    try:
        output.rename(backup)
        stage.rename(output)
    except BaseException:
        if backup.exists() and not output.exists():
            backup.rename(output)
        raise


def ingest(output, limit=None, refresh_limit=0, min_age_days=7, delay=0.5, fetch=None, progress=None, retry_missing=False):
    output=Path(output).resolve()
    if not (output/'manifest.json').exists():
        raise ValueError('Synchronize an official catalogue before detail ingestion')
    started=time.monotonic()
    transport = PoliteAPI(delay) if fetch is None else fetch
    journal=output.parent/('.'+output.name+'-ingest-checkpoints')
    journal.mkdir(exist_ok=True)
    with a.lock(output), tempfile.TemporaryDirectory(prefix='.archive-ingest-',dir=output.parent) as tmp:
        stage=Path(tmp)/'archive'
        shutil.copytree(output,stage)
        records=a.load_catalogue(stage/'catalogue.jsonl')
        manifest=a.read_json(stage/'manifest.json')
        state=a.read_json(stage/'ingestion_state.json', {})
        stamp=a.now()
        dt=datetime.fromisoformat(stamp)
        current=[r for r in records if r['public_presence']=='present']
        current.sort(key=lambda r:(r['episode_number'] is None,r['episode_number'] or 0,r['episode_id']))
        queue=[]
        for r in current:
            eid=r['episode_id'];s=state.get(eid,{})
            if (not accepted_detail_matches(stage,r,manifest[eid]) or s.get('status')=='failed'
                    or (retry_missing and any(manifest[eid][kind]['availability']=='unavailable_at_source'
                                              for kind in ('transcript','show_notes')))):
                if s.get('retry_after') and datetime.fromisoformat(s['retry_after'])>dt:
                    continue
                queue.append(r)
        refresh=[]
        if refresh_limit:
            queued={r['episode_id'] for r in queue}
            for r in current:
                if r['episode_id'] in queued:continue
                s=state.get(r['episode_id'],{})
                checked=s.get('checked_at') or manifest[r['episode_id']]['detail']['current_version']['retrieved_at']
                if datetime.fromisoformat(checked)<=dt-timedelta(days=min_age_days):refresh.append((checked,r))
            queue.extend(r for _,r in sorted(refresh,key=lambda x:x[0])[:refresh_limit])
        if limit is not None:queue=queue[:limit]
        successes=0;reused=0;failures=[];interrupted=False;successful_ids=set()
        for index,r in enumerate(queue):
            eid=r['episode_id'];entries=manifest[eid]
            metadata_hash=entries['metadata']['current_version']['sha256']
            checkpoint=journal/(r['remote_id']+'.json')
            try:
                cached=a.read_json(checkpoint,{})
                if (cached.get('metadata_sha256')==metadata_hash
                        and cached.get('payload_sha256')==a.digest(a.encoded(cached.get('payload')))):
                    detail=cached['payload'];acquired=cached['retrieved_at'];reused+=1
                else:
                    data=transport(a.SIMPLECAST_API+'/episodes/'+r['remote_id'])
                    detail=safe_detail(data,r);acquired=a.now()
                    atomic_json(checkpoint,{'metadata_sha256':metadata_hash,'retrieved_at':acquired,
                                            'payload':detail,'payload_sha256':a.digest(a.encoded(detail))})
                candidate=copy.deepcopy(entries);candidate_record=copy.deepcopy(r)
                a.detail_sources(stage,candidate_record,detail,acquired,candidate)
                manifest[eid]=candidate;r.update(candidate_record)
                state[eid]={'status':'accepted','metadata_sha256':metadata_hash,'checked_at':stamp}
                successes+=1
                successful_ids.add(eid)
            except KeyboardInterrupt:
                interrupted=True
                break
            except (HTTPError,URLError,TimeoutError,OSError,ValueError,KeyError,TypeError) as exc:
                kind='retrieval' if isinstance(exc,(HTTPError,URLError,TimeoutError,OSError)) else 'validation'
                if kind == 'validation' and checkpoint.exists():
                    # Preserve evidence while ensuring the next eligible retry can
                    # fetch a corrected remote source, not replay a bad response forever.
                    checkpoint.replace(journal/(r['remote_id']+'.failed.json'))
                failures.append({'episode_id':eid,'episode_number':r['episode_number'],'type':kind,
                                 'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__})
                state[eid]={'status':'failed','metadata_sha256':metadata_hash,'checked_at':stamp,
                            'retry_after':(dt+timedelta(minutes=5)).isoformat()}
                for source_kind in ('show_notes','transcript'):
                    if not a.available(entries[source_kind]):
                        entries[source_kind]={'kind':source_kind,'availability':'failed'}
            if progress and ((index+1)%10==0 or index+1==len(queue)):
                progress({'processed':index+1,'queued':len(queue),'accepted':successes,'failures':len(failures)})
        validation=materialize(stage,records,manifest)
        a.write(stage/'ingestion_state.json',a.encoded(state))
        run={'started_at':stamp,'duration_seconds':round(time.monotonic()-started,3),
             'queued':len(queue),'accepted':successes,'checkpoint_reused':reused,
             'skipped_accepted':len(current)-len(queue),'http_requests':getattr(transport,'requests',None),
             'interrupted':interrupted,'failures':failures,'validation':validation}
        a.write(stage/'reports/ingestion-latest.json',a.encoded(run))
        write_report(stage,records,manifest,run)
        publish(stage,output,Path(tmp)/'previous')
        # Only remove durable checkpoints after successful publication. An abrupt
        # process death before this point resumes without re-requesting accepted data.
        for r in queue:
            if r['episode_id'] in successful_ids:
                (journal/(r['remote_id']+'.json')).unlink(missing_ok=True)
        return run


def reparse(output):
    """Upgrade derived parsing from preserved detail fields, with no HTTP calls."""
    output=Path(output).resolve()
    with a.lock(output), tempfile.TemporaryDirectory(prefix='.archive-reparse-',dir=output.parent) as tmp:
        stage=Path(tmp)/'archive';shutil.copytree(output,stage)
        records=a.load_catalogue(stage/'catalogue.jsonl');manifest=a.read_json(stage/'manifest.json')
        for record in records:
            entries=manifest[record['episode_id']]
            if not a.available(entries.get('detail',{})):continue
            detail=a.read_json(stage/entries['detail']['current_version']['path'])
            detail['podcast']={'id':record['podcast_id']}
            acquired=entries['detail']['current_version']['retrieved_at']
            a.detail_sources(stage,record,detail,acquired,entries)
        materialize(stage,records,manifest)
        report=write_report(stage,records,manifest)
        publish(stage,output,Path(tmp)/'previous')
        return {'validation':report['validation'],'http_requests':0,'parser':a.SEGMENT_VERSION}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('ingest','export','report','reparse'))
    p.add_argument('--output',type=Path,default=a.ROOT/'archive')
    p.add_argument('--limit',type=int)
    p.add_argument('--refresh-limit',type=int,default=0)
    p.add_argument('--min-age-days',type=int,default=7)
    p.add_argument('--delay',type=float,default=0.5)
    args=p.parse_args()
    if any(v<0 for v in (args.refresh_limit,args.min_age_days,args.delay)) or (args.limit is not None and args.limit<0):p.error('Budgets and delays must be nonnegative')
    if args.command=='ingest':
        result=ingest(args.output,args.limit,args.refresh_limit,args.min_age_days,args.delay,
                      progress=lambda x:print(json.dumps(x),flush=True))
    elif args.command=='reparse':
        result=reparse(args.output)
    else:
        with a.lock(args.output.resolve()):
            records=a.load_catalogue(args.output/'catalogue.jsonl');manifest=a.read_json(args.output/'manifest.json')
            if args.command=='export':materialize(args.output,records,manifest)
            result=write_report(args.output,records,manifest)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 2 if result.get('failures') or result.get('interrupted') else 0


if __name__=='__main__':
    raise SystemExit(main())
