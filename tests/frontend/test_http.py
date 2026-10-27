"""Actual HTTP integration, separate because local socket binding is required."""
import http.client
import io
import json
import threading
import unittest
import zipfile
from pathlib import Path
from urllib.parse import urlencode

import archive_web as web

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless((ROOT / 'archive/search/archive.sqlite3').exists(), 'Materialize the local archive first')
class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = web.ArchiveApp(ROOT/'archive').snapshot()[0]
        cls.count = len(cls.records)
        cls.server = web.make_server(ROOT / 'archive', port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, method='GET', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        self.addCleanup(connection.close)
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        body = response.read()
        return response, body

    def test_home_and_static_assets(self):
        response, body = self.request('/')
        self.assertEqual(response.status, 200)
        self.assertIn(b'<title>Content Archive', body)
        self.assertIn("script-src 'self'", response.getheader('Content-Security-Policy'))
        self.assertEqual(response.getheader('X-Content-Type-Options'), 'nosniff')
        self.assertIsNone(response.getheader('Access-Control-Allow-Origin'))
        for path in web.ASSETS:
            with self.subTest(path=path):
                response, body = self.request(path)
                self.assertEqual(response.status, 200)
                self.assertGreater(len(body), 100)

    def test_counts_and_browse_pages(self):
        response, body = self.request('/api/archive')
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(body)['episodes'], self.count)
        _, body = self.request(f'/api/episodes?offset={self.count-3}&limit=24&sort=newest')
        self.assertEqual([r['episode_number'] for r in json.loads(body)['episodes']], [r['episode_number'] for r in sorted(self.records,key=lambda r:r['published_at'],reverse=True)[-3:]])

    def test_form_query_to_exact_readable_source(self):
        response, body = self.request('/api/search?' + urlencode({'q': 'choosing a partner in life', 'source': 'transcript'}))
        self.assertEqual(response.status, 200)
        doc = next(d for d in json.loads(body)['results'] if d['episode_number'] == 191)
        route, params = doc['url'].split('?')
        response, _ = self.request(doc['url'])
        self.assertEqual(response.status, 200)  # direct browser reload returns the app
        response, content = self.request('/api' + route.removesuffix('/transcript') + '/content?source=transcript&' + params)
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(content)['selected_passage']['passage_id'], doc['passage_id'])

    def test_numeric_route_redirect_preserves_source_and_passage(self):
        response, _ = self.request('/episodes/195/transcript?passage=example')
        self.assertEqual(response.status, 308)
        self.assertRegex(response.getheader('Location'), r'^/episodes/[a-f0-9-]{36}/transcript\?passage=example$')

    def test_private_archive_and_unknown_paths_not_served(self):
        for path in ['/archive/catalogue.jsonl', '/archive/search/archive.sqlite3', '/assets/../archive/manifest.json', '/api/no-such-endpoint', '/episodes/999999']:
            with self.subTest(path=path):
                response, body = self.request(path)
                self.assertEqual(response.status, 404)
                self.assertIn('error', json.loads(body))

    def test_unrecognized_host_and_write_methods_blocked(self):
        response, _ = self.request('/api/archive', headers={'Host': 'untrusted.example'})
        self.assertEqual(response.status, 403)
        response, _ = self.request('/api/episodes', method='POST')
        self.assertEqual(response.status, 501)

    def test_input_validation_and_json_content_type(self):
        for path in ['/api/search?limit=999', '/api/episodes?sort=no', '/api/search?episode=abc']:
            response, body = self.request(path)
            self.assertEqual(response.status, 400)
            self.assertEqual(response.getheader('Content-Type'), 'application/json; charset=utf-8')
            self.assertIn('error', json.loads(body))

    def test_sync_status_is_persisted_state(self):
        from archive_operations import freshness
        response, body = self.request('/api/sync-status')
        self.assertEqual(response.status,200)
        self.assertEqual(json.loads(body)['sync'],freshness(ROOT/'archive'))

    def test_head_has_no_body(self):
        response, body = self.request('/', method='HEAD')
        self.assertEqual(response.status, 200)
        self.assertGreater(int(response.getheader('Content-Length')), 100)
        self.assertEqual(body, b'')

    def test_csv_download_is_actual_utf8_export(self):
        response, raw = self.request('/downloads/catalogue.csv')
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader('Content-Type'), 'text/csv; charset=utf-8')
        self.assertIn('attachment;', response.getheader('Content-Disposition'))
        self.assertEqual(raw, (ROOT / 'archive/exports/catalogue.csv').read_bytes())
        raw.decode('utf-8')

    def test_markdown_view_and_download_match_the_same_artifact(self):
        _, body = self.request('/api/episodes/195/file')
        file = json.loads(body)
        response, raw = self.request(file['download_url'])
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader('Content-Type'), 'text/markdown; charset=utf-8')
        self.assertIn(file['filename'], response.getheader('Content-Disposition'))
        self.assertEqual(raw, file['text'].encode('utf-8'))
        self.assertEqual(raw, (ROOT / 'archive/exports/episodes' / file['filename']).read_bytes())
        response, _ = self.request('/episodes/195/file')
        self.assertEqual(response.status, 308)
        response, _ = self.request('/episodes/' + file['remote_id'] + '/file')
        self.assertEqual(response.status, 200)

    def test_archive_files_route_and_real_inventory(self):
        for path in ['/archive-files', '/archive-files/episodes']:
            response, raw = self.request(path)
            self.assertEqual(response.status, 200)
            self.assertIn(b'<html', raw)
        _, raw = self.request('/api/files')
        report = json.loads(raw)
        self.assertEqual(report['csv_rows'], self.count)
        self.assertEqual(report['markdown_files'], self.count)
        self.assertEqual(report['transcript_wording_changes'], [])

    def test_zip_download_contains_only_exact_generated_documents(self):
        response, raw = self.request('/downloads/markdown-library.zip')
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader('Content-Type'), 'application/zip')
        with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
            self.assertEqual(len(bundle.namelist()), self.count)
            for name in bundle.namelist():
                self.assertEqual(bundle.read(name), (ROOT / 'archive/exports' / name).read_bytes())
        _, again = self.request('/downloads/markdown-library.zip')
        self.assertEqual(raw, again)

    def test_export_download_paths_are_allowlisted(self):
        for path in ['/downloads/../manifest.json', '/downloads/episodes/../../manifest.json', '/downloads/episodes/not-an-id.md', '/downloads/episodes/' + '0' * 36 + '.md']:
            response, _ = self.request(path)
            self.assertEqual(response.status, 404)


if __name__ == '__main__':
    unittest.main()
