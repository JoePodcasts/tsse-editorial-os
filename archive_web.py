#!/usr/bin/env python3
"""Read-only local web view of the canonical TSSE archive. No third-party deps."""
import argparse
import json
import mimetypes
import re
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import archive_search as search
import archive_sync as archive
from archive_files import ExportLibrary

REPO = Path(__file__).resolve().parent
SOURCES = ('all', 'metadata', 'transcript', 'show_notes')
SOURCE_LABELS = {
    'episode_title': 'Episode title', 'episode_number': 'Episode number',
    'published_at': 'Publication date', 'short_description': 'Short description',
    'speaker_labels': 'Source speaker labels', 'transcript': 'Transcript',
    'show_notes': 'Published show notes',
}
ASSETS = {
    '/assets/app.js': REPO / 'web/app.js',
    '/assets/style.css': REPO / 'web/style.css',
    '/assets/tsse-logo.png': REPO / 'publishing/templates/quote-card/v1/assets/tsse-logo.png',
    '/assets/source-sans.otf': REPO / 'publishing/templates/quote-card/v1/fonts/SourceSansPro-Regular.otf',
    '/assets/source-sans-semibold.otf': REPO / 'publishing/templates/quote-card/v1/fonts/SourceSansPro-Semibold.otf',
}


class APIError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def integer(value, default, minimum, maximum):
    try:
        result = int(value) if value is not None else default
    except (ValueError, TypeError):
        raise APIError('Expected a whole number.')
    if result is None or not minimum <= result <= maximum:
        raise APIError('Number is outside the allowed range.')
    return result


class ArchiveApp:
    """Adapter, not another corpus: source truth remains in the Phase 1/2 files."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.files = ExportLibrary(self.root)

    def snapshot(self):
        # These small files are read together per request. No stale in-memory
        # episode database, and ingestion changes appear on the next request.
        records = [r for r in archive.load_catalogue(self.root / 'catalogue.jsonl')
                   if r['public_presence'] == 'present']
        return records, archive.read_json(self.root / 'manifest.json')

    @staticmethod
    def episode_url(record):
        return '/episodes/' + record['remote_id']

    def resolve(self, identity, records):
        matches = [r for r in records if identity in (r['remote_id'], r['episode_id'])
                   or (identity.isdigit() and r['episode_number'] == int(identity))]
        if len(matches) != 1:
            raise APIError('Episode not found or episode number is ambiguous.', 404)
        return matches[0]

    def episode(self, record, entries):
        result = {k: record.get(k) for k in (
            'episode_id', 'remote_id', 'episode_number', 'official_title',
            'published_at', 'duration_seconds', 'episode_type', 'episode_url', 'summary')}
        result['url'] = self.episode_url(record)
        path = self.root / 'exports/episodes' / (record['remote_id'] + '.md')
        if (entries.get('markdown_path') == 'exports/episodes/' + path.name
                and path.resolve().is_relative_to(self.root) and path.is_file()):
            result['file'] = {'filename': path.name, 'bytes': path.stat().st_size,
                              'url': result['url'] + '/file',
                              'download_url': '/downloads/episodes/' + path.name}
        result['sources'] = {kind: {
            'availability': entries.get(kind, {}).get('availability', 'missing'),
            'available': archive.available(entries.get(kind, {})),
            **({'timestamps': entries[kind].get('timestamps', {}),
                'speaker_labels': entries[kind].get('speaker_labels', {})} if kind == 'transcript' and kind in entries else {}),
        } for kind in ('transcript', 'show_notes')}
        return result

    def coverage(self):
        records, manifest = self.snapshot()
        coverage = {'episodes': len(records)}
        for kind in ('transcript', 'show_notes'):
            coverage[kind] = sum(archive.available(manifest[r['episode_id']].get(kind, {})) for r in records)
        coverage['timestamped_transcripts'] = sum(
            archive.available(manifest[r['episode_id']].get('transcript', {})) and
            manifest[r['episode_id']]['transcript'].get('timestamps', {}).get('state') == 'present'
            for r in records)
        coverage['markdown_files'] = sum('file' in self.episode(r, manifest[r['episode_id']]) for r in records)
        return coverage

    def browse(self, params):
        records, manifest = self.snapshot()
        sort = params.get('sort', 'newest')
        if sort not in ('newest', 'oldest', 'number'):
            raise APIError('Unknown catalogue sort.')
        key = (lambda r: (r['episode_number'] is None, r['episode_number'] or 0, r['remote_id'])) if sort == 'number' else (
            lambda r: (r.get('published_at') or '', r['remote_id']))
        records.sort(key=key, reverse=sort == 'newest')
        offset = integer(params.get('offset'), 0, 0, 1000000)
        limit = integer(params.get('limit'), 24, 1, 100)
        return {'total': len(records), 'offset': offset, 'limit': limit,
                'episodes': [self.episode(r, manifest[r['episode_id']]) for r in records[offset:offset + limit]]}

    def query(self, params):
        text = params.get('q', '').strip()
        if len(text) > 300:
            raise APIError('Search queries can contain up to 300 characters.')
        source = params.get('source', 'all')
        if source not in SOURCES:
            raise APIError('Unknown search source.')
        limit = integer(params.get('limit'), 30, 1, 100)
        episode = None
        if params.get('episode'):
            episode = integer(params['episode'], None, 0, 1000000)
        records, _ = self.snapshot()
        by_id = {r['episode_id']: r for r in records}
        # Ask for one extra result to truthfully indicate truncation without
        # replacing the existing search or ranking implementation.
        matches = search.query(self.root, text, source, episode, limit + 1)
        results = []
        for doc in matches[:limit]:
            record = by_id.get(doc['episode_id'])
            if not record:
                raise APIError('Search index is out of date. Rebuild it before searching.', 503)
            base = self.episode_url(record)
            tab = {'transcript': '/transcript', 'show_notes': '/show-notes'}.get(doc['source_type'], '')
            results.append({**doc, 'published_at': record.get('published_at'),
                            'source_label': SOURCE_LABELS[doc['source_type']],
                            'url': base + tab + '?' + urlencode({'passage': doc['passage_id']})})
        return {'query': text, 'results': results, 'has_more': len(matches) > limit,
                'limit': limit, 'method': search.VERSION}

    def passage(self, pid):
        if not re.fullmatch(r'[0-9a-f]{64}', pid):
            raise APIError('Invalid passage ID.', 404)
        try:
            return search.context(self.root, pid)
        except ValueError as exc:
            if str(exc) == 'Unknown passage ID':
                raise APIError('This passage is no longer in the current index. Search again to find its current source.', 404)
            raise

    def content(self, record, entries, source, pid=None):
        if source not in ('transcript', 'show_notes'):
            raise APIError('Unknown reading source.')
        entry = entries.get(source, {})
        if not archive.available(entry):
            raise APIError('This source is not available in the local archive.', 404)
        text_info, original = entry['derived_text'], entry['current_version']
        for info in (text_info, original):
            path = (self.root / info['path']).resolve()
            if not path.is_relative_to(self.root) or archive.digest(path.read_bytes()) != info['sha256']:
                raise APIError('Source integrity check failed. Revalidate the archive.', 503)
        text = (self.root / text_info['path']).read_bytes().decode('utf-8')
        selected = None
        if pid:
            selected = self.passage(pid)
            if selected['episode_id'] != record['episode_id'] or selected['source_type'] != source:
                raise APIError('This passage does not belong to this episode and source.', 404)
        db = search.connect(self.root)
        try:
            docs = [json.loads(row[0]) for row in db.execute(
                'SELECT payload FROM documents WHERE episode_id=? AND source_type=?',
                (record['episode_id'], source))]
        finally:
            db.close()
        docs.sort(key=lambda d: d['locator']['start'])
        spans = []
        previous = 0
        for doc in docs:
            loc = doc['locator']
            if (loc['source_sha256'] != original['sha256'] or loc['text_sha256'] != text_info['sha256']
                    or loc['start'] < previous or text[loc['start']:loc['end']] != doc['text']):
                raise APIError('Passage offsets do not match this source. Rebuild the search index.', 503)
            previous = loc['end']
            spans.append({k: doc.get(k) for k in ('passage_id', 'timestamp', 'speaker_label', 'locator')})
        return {'source': source, 'text': text, 'passages': spans, 'selected_passage': selected,
                'provenance': {'source_id': entry['source_id'], 'source_url': entry['source_url'],
                               'source_field': entry['source_field'], 'original': original,
                               'derived_text': text_info}}

    def api(self, path, params):
        if path == '/api/sync-status':
            from archive_operations import freshness
            return {'sync': freshness(self.root)}
        if path == '/api/archive':
            return self.coverage()
        if path == '/api/episodes':
            return self.browse(params)
        if path == '/api/search':
            return self.query(params)
        if path == '/api/files':
            report = self.files.inventory()
            bundle = self.files.zip_bytes()
            from archive_operations import freshness
            return {**{k: v for k, v in report.items() if k != 'files'}, 'sync': freshness(self.root),
                    'zip_bytes': len(bundle), 'zip_sha256': archive.digest(bundle),
                    'csv_download_url': '/downloads/catalogue.csv',
                    'zip_download_url': '/downloads/markdown-library.zip'}
        match = re.fullmatch(r'/api/episodes/([A-Za-z0-9:-]+)(/content|/file)?', path)
        if match:
            records, manifest = self.snapshot()
            record = self.resolve(match[1], records)
            entries = manifest[record['episode_id']]
            if match[2] == '/file':
                info, raw = self.files.markdown(record['remote_id'])
                return {**info, 'text': raw.decode('utf-8'),
                        'download_url': '/downloads/episodes/' + info['filename']}
            if match[2] == '/content':
                return self.content(record, entries, params.get('source', 'transcript'), params.get('passage'))
            result = self.episode(record, entries)
            if params.get('passage'):
                # Metadata deep links also retain and verify their exact field.
                doc = self.passage(params['passage'])
                if doc['episode_id'] != record['episode_id'] or doc['source_type'] in ('transcript', 'show_notes'):
                    raise APIError('The selected metadata match belongs to another source.', 404)
                result['selected_match'] = doc
            return result
        raise APIError('Page not found.', 404)


class Handler(BaseHTTPRequestHandler):
    server_version = 'TSSEArchive/1'

    def respond(self, status, body, content_type='application/json; charset=utf-8', filename=None):
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        if filename:
            self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        try:
            if len(self.path) > 4096:
                raise APIError('URL is too long.', 414)
            # A local read-only library should not be reachable through a
            # hostile DNS rebinding host name. No CORS headers are emitted.
            host = self.headers.get('Host', '').split(':')[0]
            if host not in ('127.0.0.1', 'localhost', self.server.server_address[0]):
                raise APIError('Unrecognized host.', 403)
            parsed = urlsplit(self.path)
            params = {k: values[-1] for k, values in parse_qs(parsed.query).items()}
            if parsed.path.startswith('/api/'):
                self.respond(200, self.server.app.api(parsed.path, params))
            elif parsed.path == '/downloads/catalogue.csv':
                self.respond(200, self.server.app.files.csv_bytes(), 'text/csv; charset=utf-8', 'catalogue.csv')
            elif parsed.path == '/downloads/markdown-library.zip':
                self.respond(200, self.server.app.files.zip_bytes(), 'application/zip', 'tsse-markdown-library.zip')
            elif re.fullmatch(r'/downloads/episodes/[a-f0-9-]{36}\.md', parsed.path):
                identity = parsed.path.rsplit('/', 1)[1][:-3]
                records, _ = self.server.app.snapshot()
                record = self.server.app.resolve(identity, records)
                info, raw = self.server.app.files.markdown(record['remote_id'])
                self.respond(200, raw, 'text/markdown; charset=utf-8', info['filename'])
            elif parsed.path in ASSETS:
                path = ASSETS[parsed.path]
                self.respond(200, path.read_bytes(), mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
            elif parsed.path in ('/', '/archive-files', '/archive-files/episodes') or re.fullmatch(r'/episodes/[A-Za-z0-9:-]+(?:/transcript|/show-notes|/file)?', parsed.path):
                if parsed.path.startswith('/episodes/'):
                    parts = parsed.path.split('/')
                    records, _ = self.server.app.snapshot()
                    record = self.server.app.resolve(parts[2], records)
                    if parts[2] != record['remote_id']:
                        self.send_response(HTTPStatus.PERMANENT_REDIRECT)
                        suffix = '/' + parts[3] if len(parts) > 3 else ''
                        self.send_header('Location', self.server.app.episode_url(record) + suffix + ('?' + parsed.query if parsed.query else ''))
                        self.end_headers()
                        return
                self.respond(200, (REPO / 'web/index.html').read_bytes(), 'text/html; charset=utf-8')
            else:
                raise APIError('Page not found.', 404)
        except APIError as exc:
            self.respond(exc.status, {'error': str(exc)})
        except (sqlite3.Error, OSError, ValueError, KeyError) as exc:
            self.log_error('Archive unavailable: %s', exc)
            self.respond(503, {'error': 'The local archive or search index is unavailable or out of date. Run archive_search.py rebuild; check the server log for details.'})


def make_server(root, host='127.0.0.1', port=8765):
    server = ThreadingHTTPServer((host, port), Handler)
    server.app = ArchiveApp(root)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=REPO / 'archive')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--github-status', metavar='OWNER/REPO',
                        help='Restore successful Actions status and prepare derived files for this checkout (requires gh authentication)')
    args = parser.parse_args()
    if args.github_status:
        from archive_operations import restore_status, validate_complete
        validate_complete(args.archive)
        print(restore_status(args.archive, args.github_status), flush=True)
    app = ArchiveApp(args.archive)
    coverage = app.coverage()
    db = search.connect(app.root)
    db.close()
    server = make_server(args.archive, port=args.port)
    print(f"TSSE Content Archive · {coverage['episodes']} episodes\nhttp://127.0.0.1:{server.server_port}\nCtrl+C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
