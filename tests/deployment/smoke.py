"""Read-only deployment smoke checks, exact download integrity and HTTP timings."""
import argparse
import hashlib
import io
import json
import os
import statistics
import time
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirects(HTTPRedirectHandler):
    """Never forward deployment credentials or accept a login page as the app."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

QUERIES = ('customer discovery', 'proof of value', 'Gokul Rajaram', 'Commerce Ventures',
           'relentlessly resourceful', 'choosing a partner in life')


def verify(base, expected):
    origin = urlsplit(base)
    if origin.scheme not in ('http', 'https') or origin.path not in ('', '/') or origin.username:
        raise ValueError('Use an HTTP(S) deployment origin')
    base = base.rstrip('/')
    checks, timings = [], {}

    def check(name, passed):
        if not passed:
            raise AssertionError(name)
        checks.append(name)

    def request(path, status=200):
        headers = {}
        if os.environ.get('VERCEL_AUTOMATION_BYPASS_SECRET'):
            if origin.scheme != 'https' or not origin.hostname.endswith('.vercel.app'):
                raise ValueError('Protection bypass is restricted to HTTPS Vercel deployments')
            headers['x-vercel-protection-bypass'] = os.environ['VERCEL_AUTOMATION_BYPASS_SECRET']
        started = time.perf_counter()
        try:
            response = build_opener(NoRedirects).open(Request(base + path, headers=headers), timeout=30)
        except HTTPError as exc:
            response = exc
        with response:
            raw = response.read()
            check(f'HTTP {status}: {path} (received {response.status}; redirects are not followed)', response.status == status)
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            timings.setdefault(path, []).append(elapsed)
            return response.headers, raw

    def api(path, status=200):
        headers, raw = request(path, status)
        content_type = headers.get('Content-Type', '')
        cache_control = headers.get('Cache-Control', '')
        check(f'API type and no-store: {path} (Content-Type={content_type!r}, Cache-Control={cache_control!r})',
              'application/json' in content_type and 'no-store' in cache_control)
        check('No server paths in API: ' + path, b'/Users/' not in raw and b'Traceback' not in raw and b'origin_path' not in raw)
        return json.loads(raw)

    count = expected['published_episodes']
    request('/')
    archive = api('/api/archive')
    check('Coverage matches accepted build', archive['episodes'] == count and archive['markdown_files'] == count)
    sync = api('/api/sync-status')['sync']
    check('Matching real sync evidence', sync['status'] == 'success' and sync['archive_fingerprint'] == expected['archive_fingerprint'] and sync['published_episodes'] == count)
    from datetime import datetime
    check('Success timestamp not older than build baseline', datetime.fromisoformat(sync['last_successful_sync_at']) >= datetime.fromisoformat(expected['last_successful_sync_at']))
    passage = None
    for query in QUERIES:
        result = api('/api/search?' + urlencode({'q': query}))
        check('Nonempty lexical results: ' + query, bool(result['results']))
        passage = passage or next((r for r in result['results'] if r['source_type'] == 'transcript'), None)
    for _ in range(3):
        api('/api/search?' + urlencode({'q': QUERIES[0]}))
    check('Transcript result exists', passage is not None)
    request(passage['url'])
    parsed = urlsplit(passage['url'])
    episode_path = parsed.path.removesuffix('/transcript')
    content = api('/api' + episode_path + '/content?source=transcript&' + parsed.query)
    check('Exact passage selection', content['selected_passage']['passage_id'] == passage['passage_id'])
    for suffix in ('', '/transcript', '/show-notes', '/file'):
        request(episode_path + suffix)
    for route in ('/archive-files', '/archive-files/episodes'):
        request(route)
    api('/api' + episode_path + '/content?source=show_notes')
    files = api('/api/files')
    check('File counts match', files['published_episodes'] == count and files['markdown_files'] == count)
    md = api('/api' + episode_path + '/file')
    check('Public file API references static bytes', 'text' not in md)
    headers, raw = request(md['download_url'])
    check('Markdown integrity', hashlib.sha256(raw).hexdigest() == md['sha256'])
    check('Markdown headers', 'text/markdown' in headers.get('Content-Type', '') and md['filename'] in headers.get('Content-Disposition', ''))
    for path, mime, filename in (('/downloads/catalogue.csv', 'text/csv', 'catalogue.csv'),
                                  ('/downloads/markdown-library.zip', 'application/zip', 'tsse-markdown-library.zip')):
        headers, raw = request(path)
        reference = expected['static_files'][path.lstrip('/')]
        check('Exact static bytes: ' + path, len(raw) == reference['bytes'] and hashlib.sha256(raw).hexdigest() == reference['sha256'])
        check('Download headers: ' + path, mime in headers.get('Content-Type', '') and filename in headers.get('Content-Disposition', ''))
        if path.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
                check('ZIP complete and readable', len(zipped.namelist()) == count and zipped.testzip() is None)
    for route, code in (('/api/episodes/999999', 404), ('/api/search?limit=99999', 400),
                        ('/api' + episode_path + '/content?source=transcript&passage=' + '0' * 64, 404),
                        ('/archive/manifest.json', 404), ('/data/episodes/active/episode_196.json', 404),
                        ('/downloads/episodes/missing.md', 404)):
        request(route, code)
    return {'base': base, 'checks_passed': len(checks), 'checks': checks,
            'timings_ms': {key: {'first': values[0], 'median': statistics.median(values), 'samples': len(values)} for key, values in timings.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base')
    parser.add_argument('--expected-report', type=Path, default=Path('.vercel/archive-build-report.json'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = verify(args.base, json.loads(args.expected_report.read_text()))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
