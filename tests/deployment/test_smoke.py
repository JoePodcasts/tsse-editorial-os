"""Ensure staged validation cannot mistake an authentication page for the app."""
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from smoke import verify


class SmokeTests(unittest.TestCase):
    def test_redirect_is_rejected_without_requesting_login_page(self):
        requests = []

        class LoginRedirect(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(302 if self.path == '/' else 200)
                self.send_header('Location', '/login?private=not-for-logs')
                self.end_headers()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), LoginRedirect)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.dict('os.environ', {'VERCEL_AUTOMATION_BYPASS_SECRET': ''}):
                with self.assertRaisesRegex(AssertionError, 'received 302') as error:
                    verify(f'http://127.0.0.1:{server.server_port}', {'published_episodes': 196})
            self.assertNotIn('private', str(error.exception))
            self.assertEqual(requests, ['/'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
