"""Read-only Vercel adapter; the canonical archive/search implementations are reused."""
import json
import logging
import re
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import archive_sync as archive
from archive_status import PublicStatus
from archive_web import APIError, ArchiveApp


def public_value(value):
    """Keep hashes, source URLs and offsets, not server/repository file locators."""
    hidden = {'path', 'source_path', 'text_path', 'origin_path', 'previous_versions'}
    if isinstance(value, dict):
        return {k: public_value(v) for k, v in value.items() if k not in hidden}
    if isinstance(value, list):
        return [public_value(v) for v in value]
    return value


class PublicArchiveApp(ArchiveApp):
    def __init__(self, root, fetch_status=None):
        self.root = Path(root).resolve()
        self.records = archive.load_catalogue(self.root / 'catalogue.jsonl')
        self.manifest = archive.read_json(self.root / 'manifest.json')
        self.inventory = archive.read_json(self.root / 'export-inventory.json')
        self.file_info = {f['remote_id']: f for f in self.inventory['files']}
        status = archive.read_json(self.root / 'sync-status.json')
        self.status = PublicStatus(status, **({'fetch': fetch_status} if fetch_status else {}))

    def snapshot(self):
        return list(self.records), self.manifest

    def episode(self, record, entries):
        value = super().episode(record, entries)
        info = self.file_info[record['remote_id']]
        value['file'] = {**info, 'url': value['url'] + '/file',
                         'download_url': '/downloads/episodes/' + info['filename']}
        return value

    def api(self, path, params):
        if path == '/api/sync-status':
            result = {'sync': self.status.get()}
        elif path == '/api/files':
            result = {k: v for k, v in self.inventory.items() if k != 'files'}
            result.update(sync=self.status.get(), csv_download_url='/downloads/catalogue.csv',
                          zip_download_url='/downloads/markdown-library.zip')
        elif (match := re.fullmatch(r'/api/episodes/([A-Za-z0-9:-]+)/file', path)):
            record = self.resolve(match[1], self.records)
            info = self.file_info[record['remote_id']]
            result = {**info, 'download_url': '/downloads/episodes/' + info['filename']}
        else:
            result = super().api(path, params)
        return public_value(result)


_app = None


def application():
    global _app
    if _app is None:
        _app = PublicArchiveApp(Path(__file__).resolve().parent / 'archive')
    return _app


class PublicHandler(BaseHTTPRequestHandler):
    server_version = 'TSSEArchive'
    sys_version = ''

    def respond(self, status, value):
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(raw)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        try:
            if len(self.path) > 4096:
                raise APIError('URL is too long.', 414)
            parsed = urlsplit(self.path)
            params = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
            route = params.pop('route', '')
            path = '/api/' + route if parsed.path == '/api/archive_function' else parsed.path
            self.respond(200, application().api(path, params))
        except APIError as exc:
            message = str(exc).replace('local archive', 'archive') if exc.status < 500 else 'The archive is temporarily unavailable. Please try again.'
            self.respond(exc.status, {'error': message})
        except Exception:
            logging.exception('Archive request failed')
            self.respond(503, {'error': 'The archive is temporarily unavailable. Please try again.'})

    def do_POST(self):
        self.respond(405, {'error': 'This archive is read-only.'})

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST
