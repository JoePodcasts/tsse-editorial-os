#!/usr/bin/env python3
"""Build an allowlisted, validated read-only Vercel deployment from accepted data."""
import argparse
import copy
import json
import re
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

import archive_operations as ops
import archive_search as search
import archive_status as status
import archive_sync as a
from archive_files import ExportLibrary
from archive_public import PublicArchiveApp
from archive_web import ASSETS

RUNTIME_CODE = ('archive_public.py', 'archive_status.py', 'archive_web.py',
                'archive_search.py', 'archive_sync.py', 'archive_files.py', 'episode_discovery.py')
SOURCE_KINDS = ('metadata', 'summary', 'show_notes', 'transcript')
QUERIES = ('customer discovery', 'proof of value', 'Gokul Rajaram', 'Commerce Ventures',
           'relentlessly resourceful', 'choosing a partner in life')
SECRET_PATTERN = re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bAKIA[A-Z0-9]{16}\b|\bghp_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{30,}\b|\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b')


def copy_checked(source, destination, info):
    candidate = source / info['path']
    path = candidate.resolve()
    if not path.is_relative_to(source.resolve()) or any(p.is_symlink() for p in (candidate, *candidate.parents)):
        raise ValueError('Invalid source path in deployment inputs')
    raw = path.read_bytes()
    if a.digest(raw) != info['sha256']:
        raise ValueError('Deployment source hash mismatch')
    a.write(destination / info['path'], raw)


def snapshot(root):
    return {str(p.relative_to(root)): {'bytes': p.stat().st_size, 'sha256': a.digest(p.read_bytes())}
            for p in sorted(root.rglob('*')) if p.is_file()}


def inspect_public(root):
    """Fail closed on credential-shaped data and local development paths."""
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        if p.is_symlink() or p.name.startswith('.env') or p.suffix in ('.sqlite3', '.py', '.pyc'):
            raise ValueError('Unexpected public deployment file: ' + str(p.relative_to(root)))
        raw = p.read_bytes()
        if SECRET_PATTERN.search(raw):
            raise ValueError('Credential-shaped value requires review in ' + str(p.relative_to(root)))
        if p.suffix in ('.html', '.js', '.css', '.csv', '.md', '.json'):
            # A website URL can legitimately contain /home/ (e.g. leap.cl/en/home/).
            if re.search(rb'file:///(?:Users|home)/|(?<![A-Za-z0-9./])(?:/Users/|/home/[^ /]+/)|https?://(?:localhost|127\.0\.0\.1)(?::|/)', raw):
                raise ValueError('Local development reference in public file: ' + str(p.relative_to(root)))


def build(repository=a.ROOT, output=None, fetch_status=status.retrieve):
    repository = Path(repository).resolve()
    output = Path(output).resolve() if output else repository
    source = repository / 'archive'
    started = time.perf_counter()
    # Never regenerate or mutate accepted source/exports in a web build.
    a.validate(source)
    inventory = ExportLibrary(source).inventory()
    count = inventory['published_episodes']
    fingerprint = ops.state_fingerprint(source)
    baseline = a.read_json(source / ops.STATUS, {})
    if not baseline:
        baseline = fetch_status(fingerprint)
    baseline = status.checked(baseline, fingerprint, count)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.archive-deploy-', dir=output) as tmp:
        work = Path(tmp)
        full = work / 'input'
        full.mkdir()
        for name in ops.CONTENT_PATHS:
            src = source / name
            if src.is_dir():
                shutil.copytree(src, full / name)
            elif src.is_file():
                (full / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, full / name)
        index_report = search.rebuild(full)
        runtime = work / 'vercel_runtime'
        data = runtime / 'archive'
        public = work / 'public'
        data.mkdir(parents=True)
        public.mkdir()
        for name in RUNTIME_CODE:
            shutil.copyfile(repository / name, runtime / name)
        records = [r for r in a.load_catalogue(source / 'catalogue.jsonl') if r['public_presence'] == 'present']
        manifest = a.read_json(source / 'manifest.json')
        reduced = {}
        for record in records:
            entries = manifest[record['episode_id']]
            selected = {}
            for kind in SOURCE_KINDS:
                entry = copy.deepcopy(entries[kind])
                entry.pop('previous_versions', None)
                entry.pop('origin_path', None)
                selected[kind] = entry
                for key in ('current_version', 'derived_text'):
                    if entry.get(key):
                        copy_checked(source, data, entry[key])
            # Export-state flags are metadata, never editorial content/references.
            for kind in ('structured_transcript', 'intelligence', 'newsletter', 'social'):
                selected[kind] = {'kind': kind, 'availability': entries[kind]['availability']}
            selected['markdown_path'] = entries['markdown_path']
            reduced[record['episode_id']] = selected
        a.write(data / 'catalogue.jsonl', ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in records))
        a.write(data / 'manifest.json', a.encoded(reduced))
        (data / 'search').mkdir()
        shutil.copyfile(full / 'search/archive.sqlite3', data / 'search/archive.sqlite3')
        # Corpus and passage identities are unchanged. Bind provenance to the
        # reduced deployment manifest, not private/unused source references.
        with sqlite3.connect(data / 'search/archive.sqlite3') as db:
            db.execute('UPDATE provenance SET input_fingerprint=?', (search.source_fingerprint(data),))
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('Invalid deployment search index')
        a.write(data / ops.STATUS, a.encoded(baseline))
        bundle = ExportLibrary(source).zip_bytes()
        public_inventory = {**inventory, 'zip_bytes': len(bundle), 'zip_sha256': a.digest(bundle)}
        a.write(data / 'export-inventory.json', a.encoded(public_inventory))
        a.write(public / 'downloads/markdown-library.zip', bundle)
        a.write(public / 'downloads/catalogue.csv', (source / 'exports/catalogue.csv').read_bytes())
        for info in inventory['files']:
            raw = (source / 'exports/episodes' / info['filename']).read_bytes()
            if a.digest(raw) != info['sha256']:
                raise ValueError('Markdown changed during deployment build')
            a.write(public / 'downloads/episodes' / info['filename'], raw)
        a.write(public / 'index.html', (repository / 'web/index.html').read_bytes())
        for url, src in ASSETS.items():
            # Asset paths are an explicit existing product allowlist.
            a.write(public / url.lstrip('/'), (repository / src.relative_to(a.ROOT)).read_bytes())
        inspect_public(public)
        app = PublicArchiveApp(data, fetch_status=lambda _: baseline)
        if app.coverage()['episodes'] != count or app.coverage()['markdown_files'] != count:
            raise ValueError('Deployment coverage differs from validated archive')
        comparisons = []
        for query in QUERIES:
            expected = search.query(full, query, limit=30)
            actual = app.api('/api/search', {'q': query})['results']
            if [(d['passage_id'], d['text'], d['ranking']) for d in actual] != [(d['passage_id'], d['text'], d['ranking']) for d in expected]:
                raise ValueError('Deployment search differs from canonical retrieval')
            comparisons.append({'query': query, 'results': len(actual), 'identical': True})
        for record in records:
            app.api('/api/episodes/' + record['remote_id'] + '/file', {})
            for kind in ('transcript', 'show_notes'):
                if a.available(reduced[record['episode_id']][kind]):
                    app.content(record, reduced[record['episode_id']], kind)
        runtime_files, static_files = snapshot(runtime), snapshot(public)
        runtime_bytes = sum(f['bytes'] for f in runtime_files.values())
        if runtime_bytes >= 250_000_000:
            raise ValueError('Deployment exceeds the conservative 250 MB function budget')
        report = {'archive_fingerprint': fingerprint, 'published_episodes': count,
                  'last_successful_sync_at': baseline['last_successful_sync_at'],
                  'runtime_bytes': runtime_bytes, 'static_bytes': sum(f['bytes'] for f in static_files.values()),
                  'archive_data_bytes': sum(f['bytes'] for path, f in runtime_files.items() if path.startswith('archive/')),
                  'search_index_bytes': (data / 'search/archive.sqlite3').stat().st_size,
                  'index_build_seconds': index_report['build_seconds'],
                  'build_seconds': round(time.perf_counter() - started, 3),
                  'queries': comparisons, 'runtime_files': runtime_files, 'static_files': static_files}
        # Only replace build-owned outputs after complete validation.
        for name in ('public', 'vercel_runtime'):
            destination = output / name
            if destination.exists():
                shutil.rmtree(destination)
            (work / name).rename(destination)
        a.write(output / '.vercel/archive-build-report.json', a.encoded(report))
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build',))
    parser.add_argument('--repository', type=Path, default=a.ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = build(args.repository, args.output)
    print(json.dumps({k: v for k, v in report.items() if k not in ('runtime_files', 'static_files')}, indent=2))


if __name__ == '__main__':
    main()
