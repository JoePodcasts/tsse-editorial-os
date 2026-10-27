#!/usr/bin/env python3
"""Transactional production orchestration of the existing archive pipeline."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import archive_sync as a
import archive_library as library
import archive_search as search
from archive_files import ExportLibrary

STATUS = 'sync-status.json'
RUN = 'reports/sync-run.json'
# Per-run operational state is persisted separately from content commits.
OPERATIONAL = (STATUS, 'ingestion_state.json', RUN)
CONTENT_PATHS = ('catalogue.jsonl', 'manifest.json', 'links.json', 'sources',
                 'derived/text', 'derived/segments', 'exports/catalogue.csv',
                 'exports/episodes', 'reports/latest.json', 'reports/latest.md')


def state_fingerprint(root):
    return a.digest(a.encoded([a.digest((root / name).read_bytes())
                              for name in ('catalogue.jsonl', 'manifest.json')]))


def freshness(root):
    """Expose only a successful record tied to the currently served archive."""
    root = Path(root)
    try:
        value = a.read_json(root / STATUS, {})
        stamp = datetime.fromisoformat(value['last_successful_sync_at'])
        if (value.get('status') != 'success' or stamp.tzinfo is None
                or stamp > datetime.now(timezone.utc)
                or value.get('archive_fingerprint') != state_fingerprint(root)):
            return None
        return {key: value[key] for key in ('status', 'last_successful_sync_at',
                'published_episodes', 'changes_detected', 'changes')}
    except (KeyError, TypeError, ValueError, OSError):
        return None


def validate_complete(root):
    """Same fidelity validators as manual operation, plus index and ZIP parity."""
    root = Path(root)
    core = a.validate(root)
    files = ExportLibrary(root)
    exports = files.inventory()
    index_path = root / 'search/archive.sqlite3'
    index_report = a.read_json(root / 'reports/search-index.json', {})
    if (index_report.get('input_fingerprint') != search.source_fingerprint(root)
            or not index_path.exists()
            or a.digest(index_path.read_bytes()) != index_report.get('index_sha256')):
        index_report = search.rebuild(root)
    with search.connect(root) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('Search index integrity check failed')
        indexed = {row[0] for row in db.execute('SELECT DISTINCT episode_id FROM documents')}
    records = a.load_catalogue(root / 'catalogue.jsonl')
    ids = {r['episode_id'] for r in records if r['public_presence'] == 'present'}
    if indexed != ids:
        raise ValueError('Search index does not cover the published catalogue')
    zip_path = root / 'exports/markdown-library.zip'
    zip_info_path = root / 'reports/library-zip.json'
    input_hash = a.digest(a.encoded(exports['files']))
    zip_info = a.read_json(zip_info_path, {})
    if (zip_info.get('input_hash') != input_hash or not zip_path.exists()
            or a.digest(zip_path.read_bytes()) != zip_info.get('sha256')):
        payload = files.zip_bytes()
        a.write(zip_path, payload)
        zip_info = {'input_hash': input_hash, 'sha256': a.digest(payload), 'bytes': len(payload),
                    'entries': exports['markdown_files']}
        a.write(zip_info_path, a.encoded(zip_info))
    with zipfile.ZipFile(zip_path) as bundle:
        expected = ['episodes/' + f['filename'] for f in exports['files']]
        if bundle.namelist() != expected:
            raise ValueError('ZIP membership differs from portable library')
        for info in exports['files']:
            if a.digest(bundle.read('episodes/' + info['filename'])) != info['sha256']:
                raise ValueError('ZIP member differs from original Markdown')
    # Exercise the actual frontend adapter against the candidate generation.
    from archive_web import ArchiveApp
    app = ArchiveApp(root)
    coverage = app.coverage()
    if coverage['episodes'] != exports['csv_rows'] or coverage['markdown_files'] != len(ids):
        raise ValueError('Frontend/export coverage mismatch')
    manifest = a.read_json(root/'manifest.json')
    for record in records:
        if record['episode_id'] in ids:
            if not app.episode(record, manifest[record['episode_id']]).get('file'):
                raise ValueError('Episode file not readable by frontend')
    return {'archive': core, 'portable_exports': 'PASS', 'search_index': 'PASS',
            'frontend': 'PASS', 'published_episodes': len(ids), 'coverage': coverage,
            'zip': zip_info, 'index_reused': index_report.get('index_reused', True)}


def change_counts(before_records, before_manifest, root):
    old = {r['episode_id']: r for r in before_records}
    records = a.load_catalogue(root/'catalogue.jsonl')
    manifest = a.read_json(root/'manifest.json')
    counts = dict(new=0, changed=0, unchanged=0, not_seen=0)
    for record in records:
        eid = record['episode_id']
        if record['public_presence'] != 'present': counts['not_seen'] += 1
        elif eid not in old: counts['new'] += 1
        elif record != old[eid] or manifest[eid] != before_manifest.get(eid): counts['changed'] += 1
        else: counts['unchanged'] += 1
    return counts


def sync(output, repository=a.ROOT, fetch=None, refresh_limit=20, min_age_days=7, delay=0.5):
    """Publish only after *all* remote work and local validation succeed."""
    output, repository = Path(output).resolve(), Path(repository).resolve()
    if (output == repository or output in repository.parents
            or any(output == repository/p or (repository/p) in output.parents
                   for p in ('data','docs','publishing','tests','.git','outputs','web','.github'))):
        raise ValueError('Output must be a dedicated archive directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not (output/'manifest.json').exists():
        raise ValueError('Refusing to replace non-archive output directory')
    transport = fetch if fetch is not None else library.PoliteAPI(delay)
    with a.lock(output):
        started = a.now()
        try:
            before = a.load_catalogue(output/'catalogue.jsonl')
            before_manifest = a.read_json(output/'manifest.json', {})
            with tempfile.TemporaryDirectory(prefix='.archive-production-', dir=output.parent) as tmp:
                stage = Path(tmp)/'candidate'
                if output.exists(): shutil.copytree(output, stage)
                # Existing commands operate only inside the disposable candidate.
                discovered = a.sync(stage, repository=repository, fetch=transport)
                ingested = library.ingest(stage, fetch=transport, delay=delay,
                    refresh_limit=refresh_limit, min_age_days=min_age_days, retry_missing=True)
                if discovered.get('failures') or ingested['failures'] or ingested['interrupted']:
                    raise ValueError('Source ingestion failed or was interrupted: ' + json.dumps(ingested['failures']))
                records = a.load_catalogue(stage/'catalogue.jsonl')
                manifest = a.read_json(stage/'manifest.json')
                if any(manifest[r['episode_id']][kind]['availability'] not in ('available','unavailable_at_source')
                       for r in records if r['public_presence']=='present' for kind in ('transcript','show_notes')):
                    raise ValueError('Unresolved source retrieval; retry the complete synchronization')
                changes = change_counts(before, before_manifest, stage)
                validation = validate_complete(stage)
                content_changed = any(changes[k] for k in ('new','changed','not_seen'))
                if content_changed:
                    report = a.read_json(stage/'reports/latest.json')
                    report['changes'] = changes
                    a.write(stage/'reports/latest.json', a.encoded(report))
                    library.write_report(stage, records, manifest, ingested)
                else:
                    # Keep accepted content coverage stable; this run belongs in RUN.
                    for name in ('reports/latest.json','reports/latest.md','reports/ingestion-latest.json'):
                        if (output/name).exists(): shutil.copy2(output/name, stage/name)
                pending = [{'episode_number': r['episode_number'], 'episode_id': r['episode_id'],
                            'missing': [kind for kind in ('show_notes','transcript')
                                        if not a.available(manifest[r['episode_id']][kind])]}
                           for r in records if r['public_presence']=='present'
                           and any(not a.available(manifest[r['episode_id']][kind]) for kind in ('show_notes','transcript'))]
                # Timestamp is created only after the full chain has validated.
                status = {'schema_version': 1, 'status': 'success', 'last_successful_sync_at': a.now(),
                          'published_episodes': validation['published_episodes'], 'changes': changes,
                          'changes_detected': content_changed, 'archive_fingerprint': state_fingerprint(stage)}
                run = {'started_at': started, **status, 'http_requests': getattr(transport,'requests',None),
                       'detail_requests': ingested['queued']-ingested['checkpoint_reused'],
                       'pending_sources': pending, 'validation': validation, 'content_changed': content_changed}
                a.write(stage/STATUS, a.encoded(status))
                a.write(stage/RUN, a.encoded(run))
                backup = Path(tmp)/'previous'
                if output.exists(): library.publish(stage, output, backup)
                else: stage.rename(output)
                return run
        except BaseException as exc:
            library.atomic_json(output.parent/('.'+output.name+'-production-failure.json'), {
                'attempted_at': started, 'status':'failed', 'error_type':type(exc).__name__,
                'message':str(exc), 'accepted_archive_unchanged':True})
            raise


def run_git(repository, *args):
    return subprocess.run(['git', '-C', str(repository), *args], check=True,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


def persist(repository, push=False, branch='main'):
    """Stage only approved archive content; no commit for operational-only changes."""
    repository = Path(repository).resolve()
    if not freshness(repository/'archive'):
        raise ValueError('Persistence requires a successful sync for the current archive state')
    validate_complete(repository/'archive')
    if run_git(repository, 'diff', '--cached', '--name-only'):
        raise ValueError('Refusing persistence with pre-existing staged changes')
    if run_git(repository, 'branch', '--show-current') != branch:
        raise ValueError('Persistence requires the configured default branch')
    paths = ['archive/'+p for p in CONTENT_PATHS if (repository/'archive'/p).exists()]
    run_git(repository, 'add', '--', *paths)
    changed = run_git(repository, 'diff', '--cached', '--name-only')
    if not changed: return {'persisted':True, 'commit_created':False}
    run_git(repository, '-c', 'user.name=github-actions[bot]', '-c',
            'user.email=41898282+github-actions[bot]@users.noreply.github.com',
            'commit', '-m', 'archive: sync published TSSE episodes')
    if push:
        # Fast-forward only. No force push, automatic rebase, or conflict masking.
        run_git(repository, 'push', 'origin', 'HEAD:refs/heads/'+branch)
    return {'persisted':True, 'commit_created':True, 'commit':run_git(repository,'rev-parse','HEAD')}


def restore_status(root, repository_slug, branch='main'):
    """Restore only successful, fingerprint-matching Actions operational state."""
    import re
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository_slug):
        raise ValueError('Invalid GitHub repository')
    root = Path(root).resolve()
    def gh(*args):
        return subprocess.run(['gh',*args],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
    runs = json.loads(gh('run','list','--repo',repository_slug,'--workflow','archive-sync.yml',
                        '--branch',branch,'--status','success','--limit','30','--json','databaseId'))
    for run in runs:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                gh('run','download',str(run['databaseId']),'--repo',repository_slug,
                   '--name','archive-sync-state','--dir',tmp)
            except subprocess.CalledProcessError:
                continue  # expired/missing artifacts; preserve the last local success
            status = a.read_json(Path(tmp)/STATUS, {})
            if status.get('status') != 'success' or status.get('archive_fingerprint') != state_fingerprint(root):
                continue
            stamp = datetime.fromisoformat(status['last_successful_sync_at'])
            if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
                raise ValueError('Invalid successful sync timestamp')
            previous = a.read_json(root/STATUS, {})
            if previous.get('archive_fingerprint') == status['archive_fingerprint'] and previous.get('last_successful_sync_at'):
                if datetime.fromisoformat(previous['last_successful_sync_at']) >= stamp:
                    return {'restored':False, 'reason':'Local success is newer or equal'}
            with a.lock(root):
                if status['archive_fingerprint'] != state_fingerprint(root):
                    raise ValueError('Archive changed while restoring synchronization status; retry')
                for name in OPERATIONAL:
                    source = Path(tmp)/name
                    if source.exists(): library.atomic_json(root/name, a.read_json(source))
            return {'restored':True,'run_id':run['databaseId']}
    return {'restored':False,'reason':'No successful matching artifact; existing status retained'}


def summary(root, persisted=None):
    run = a.read_json(Path(root)/RUN, {})
    if not run: return '## TSSE Archive Sync\n\nSync did not complete. See the failed step logs; previous successful state remains authoritative.\n'
    changes = run['changes']; counts = run['validation']['coverage']
    lines = ['## TSSE Archive Sync','', 'Last successful source check: '+run['last_successful_sync_at'], '',
             f"Published episodes: {counts['episodes']}",f"New: {changes['new']} · Changed: {changes['changed']} · Unchanged: {changes['unchanged']}",
             f"Transcripts: {counts['transcript']} · Published show notes: {counts['show_notes']} · Markdown files: {counts['markdown_files']}",
             '', 'Search index: PASS · Portable exports: PASS · Archive validation: PASS',
             'Persistence: '+('YES' if persisted else 'NOT CONFIRMED'), '']
    for pending in run['pending_sources']:
        lines.append(f"Episode {pending['episode_number']}: {', '.join(pending['missing'])} pending at source; retry next sync/manual run.")
    return '\n'.join(lines)+'\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('sync','validate','restore-status','persist','summary'))
    p.add_argument('--output', type=Path, default=a.ROOT/'archive')
    p.add_argument('--repository', type=Path, default=a.ROOT)
    p.add_argument('--refresh-limit', type=int, default=20)
    p.add_argument('--min-age-days', type=int, default=7)
    p.add_argument('--github-repository', default='JoePodcasts/tsse-editorial-os')
    p.add_argument('--branch', default='main')
    p.add_argument('--push', action='store_true')
    p.add_argument('--persisted', action='store_true')
    args = p.parse_args()
    if args.refresh_limit<0 or args.min_age_days<0: p.error('Refresh bounds must be nonnegative')
    if args.command=='sync': result=sync(args.output,args.repository,refresh_limit=args.refresh_limit,min_age_days=args.min_age_days)
    elif args.command=='validate': result=validate_complete(args.output)
    elif args.command=='restore-status': result=restore_status(args.output,args.github_repository,args.branch)
    elif args.command=='persist': result=persist(args.repository,args.push,args.branch)
    else: print(summary(args.output,args.persisted)); return
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        # Git/gh capture stderr so normal commands stay quiet. Preserve their
        # diagnostics on failure for Actions operators (never the public UI).
        print((exc.stderr or str(exc)).strip(), file=sys.stderr)
        sys.exit(exc.returncode or 1)
