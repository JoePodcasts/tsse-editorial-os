"""Local packaging harness, not an emulator or substitute for Vercel validation."""
import argparse
import json
import mimetypes
import re
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'vercel_runtime'))
from archive_public import PublicHandler


class Handler(PublicHandler):
    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path.startswith('/api/'):
            return super().do_GET()
        if path in ('/', '/archive-files', '/archive-files/episodes') or re.fullmatch(r'/episodes/[A-Za-z0-9:-]+(?:/transcript|/show-notes|/file)?', path):
            path = '/index.html'
        target = (ROOT / 'public' / path.lstrip('/')).resolve()
        if not target.is_relative_to(ROOT / 'public') or not target.is_file():
            return self.respond(404, {'error': 'Page not found.'})
        content_type = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        content_type = {'.md': 'text/markdown; charset=utf-8', '.csv': 'text/csv; charset=utf-8'}.get(target.suffix, content_type)
        raw = target.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        config = json.loads((ROOT / 'vercel.json').read_text())
        for header in config['headers'][0]['headers']:
            self.send_header(header['key'], header['value'])
        if path.startswith('/downloads/'):
            filename = 'tsse-markdown-library.zip' if target.suffix == '.zip' else target.name
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Built public archive: http://127.0.0.1:{args.port}', flush=True)
    server.serve_forever()
