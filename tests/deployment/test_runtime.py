"""Tests for the built public adapter; run after archive_deploy.py build."""
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import archive_deploy as deploy
import archive_public as public

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless((ROOT / 'vercel_runtime/archive/search/archive.sqlite3').exists(), 'Build the deployment package first')
class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = public.PublicArchiveApp(ROOT / 'vercel_runtime/archive', fetch_status=lambda _: json.loads((ROOT / 'archive/sync-status.json').read_text()) if (ROOT / 'archive/sync-status.json').exists() else {})
        cls.application_patch = patch.object(public, 'application', return_value=cls.app)
        cls.application_patch.start()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), public.PublicHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
        cls.application_patch.stop()

    def request(self, path, method='GET'):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        self.addCleanup(conn.close)
        conn.request(method, path)
        response = conn.getresponse()
        return response.status, response.read()

    def test_rewrite_query_and_readonly_methods(self):
        code, raw = self.request('/api/archive-function?route=search&path=search&q=customer+discovery')
        self.assertEqual(code, 200)
        self.assertTrue(json.loads(raw)['results'])
        for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            self.assertEqual(self.request('/api/archive', method)[0], 405)

    def test_backend_failure_is_generic_and_does_not_leak_paths(self):
        with patch.object(self.app, 'api', side_effect=OSError('/private/database unavailable')), self.assertLogs(level='ERROR'):
            code, raw = self.request('/api/search?q=test')
        self.assertEqual(code, 503)
        self.assertNotIn(b'/private', raw)
        self.assertNotIn(b'Traceback', raw)

    def test_requests_never_mutate_deployment_data(self):
        before = deploy.snapshot(self.app.root)
        for route in ('/api/search?q=customer+discovery', '/api/episodes/195/content?source=transcript', '/api/files', '/api/sync-status'):
            self.assertEqual(self.request(route)[0], 200)
        self.assertEqual(deploy.snapshot(self.app.root), before)
