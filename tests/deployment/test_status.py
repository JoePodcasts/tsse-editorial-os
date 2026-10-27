import copy
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import archive_deploy as deploy
import archive_status as status

BASE = dict(schema_version=1, status='success', last_successful_sync_at='2026-01-06T14:30:00+00:00',
            published_episodes=195, changes_detected=False, changes={'new': 0, 'changed': 0}, archive_fingerprint='a' * 64)


class FreshnessTests(unittest.TestCase):
    def test_no_change_advances_without_changing_baseline(self):
        newer = {**BASE, 'last_successful_sync_at': '2026-01-13T14:30:00+00:00'}
        baseline = copy.deepcopy(BASE)
        current = status.PublicStatus(baseline, fetch=lambda _: newer, ttl=0)
        self.assertEqual(current.get(), newer)
        self.assertEqual(baseline, BASE)

    def test_failed_old_wrong_generation_and_wrong_count_do_not_replace_success(self):
        for update in ({**BASE, 'status': 'failed'}, {**BASE, 'archive_fingerprint': 'b' * 64},
                       {**BASE, 'published_episodes': 196}, {**BASE, 'last_successful_sync_at': '2026-01-01T00:00:00Z'},
                       {**BASE, 'last_successful_sync_at': '2099-01-01T00:00:00Z'}, {}):
            with self.subTest(update=update):
                self.assertEqual(status.PublicStatus(BASE, fetch=lambda _: update, ttl=0).get(), BASE)

    def test_network_failure_keeps_last_fetched_success(self):
        newer = {**BASE, 'last_successful_sync_at': '2026-01-13T14:30:00+00:00'}
        current = status.PublicStatus(BASE, fetch=lambda _: newer, ttl=0)
        current.get()
        def unavailable(_):
            raise OSError('Offline')
        current.fetch = unavailable
        self.assertEqual(current.get(), newer)

    def test_ttl_limits_network_calls(self):
        calls = []
        current = status.PublicStatus(BASE, fetch=lambda fp: calls.append(fp) or BASE)
        current.get(); current.get()
        self.assertEqual(calls, ['a' * 64])

    def test_record_has_no_private_extra_fields(self):
        self.assertEqual(status.checked({**BASE, 'operational_log': '/private/path'}, 'a' * 64, 195), BASE)

    def test_scanner_rejects_secrets_and_local_paths_but_preserves_public_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / 'episode.md'
            file.write_text('<a href="https://leap.cl/en/home/?utm_source=podcast">LEAP</a>')
            deploy.inspect_public(root)
            for text in ('/Users/someone/private.txt', 'file:///home/user/private.txt', 'http://localhost:8765', 'ghp_' + 'x' * 40):
                file.write_text(text)
                with self.assertRaises(ValueError):
                    deploy.inspect_public(root)

    def test_new_generation_has_new_artifact_identity(self):
        self.assertNotEqual(status.artifact_name('a' * 64), status.artifact_name('b' * 64))

    def test_missing_token_preserves_baseline(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(status.PublicStatus(BASE).get(), BASE)

    def test_signed_artifact_redirect_never_forwards_github_token(self):
        from urllib.request import Request
        request = Request('https://api.github.com/repos/example/archive', headers={'Authorization': 'Bearer secret'})
        redirected = status.SafeRedirect().redirect_request(request, None, 302, 'Found', {}, 'https://storage.example/signed')
        self.assertIsNone(redirected.get_header('Authorization'))
        with self.assertRaises(ValueError):
            status.SafeRedirect().redirect_request(request, None, 302, 'Found', {}, 'http://storage.example/signed')

    def test_artifact_retrieval_selects_latest_matching_main_record(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w') as bundle:
            bundle.writestr('sync-status.json', json.dumps(BASE))
        name = status.artifact_name('a' * 64)
        listing = {'artifacts': [dict(id=i, name=name, expired=False, workflow_run={'head_branch': branch})
                                 for i, branch in [(1, 'main'), (2, 'main'), (3, 'untrusted')]]}
        requests = []
        class Opener:
            def open(self, request, **kwargs):
                requests.append(request)
                return io.BytesIO(payload.getvalue() if request.full_url.endswith('/2/zip') else json.dumps(listing).encode())
        with patch.dict('os.environ', {'ARCHIVE_STATUS_TOKEN': 'example-token'}), patch.object(status, 'build_opener', return_value=Opener()):
            self.assertEqual(status.retrieve('a' * 64), BASE)
        self.assertTrue(requests[-1].full_url.endswith('/2/zip'))
        self.assertEqual(requests[0].get_header('Authorization'), 'Bearer example-token')

    def test_artifact_with_extra_operational_files_is_rejected(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w') as bundle:
            bundle.writestr('sync-status.json', json.dumps(BASE))
            bundle.writestr('private.log', 'not for frontend')
        class Opener:
            def open(self, request, **kwargs):
                if request.full_url.endswith('/zip'):
                    return io.BytesIO(payload.getvalue())
                return io.BytesIO(json.dumps({'artifacts': [dict(id=1, name=status.artifact_name('a' * 64), expired=False, workflow_run={'head_branch': 'main'})]}).encode())
        with patch.dict('os.environ', {'ARCHIVE_STATUS_TOKEN': 'example-token'}), patch.object(status, 'build_opener', return_value=Opener()):
            self.assertEqual(status.PublicStatus(BASE).get(), BASE)

    def test_failed_build_preserves_prior_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'public').mkdir()
            (root / 'public/index.html').write_text('previous deployment')
            with patch.object(deploy.a, 'validate', side_effect=ValueError('Rejected archive')):
                with self.assertRaises(ValueError):
                    deploy.build(root)
            self.assertEqual((root / 'public/index.html').read_text(), 'previous deployment')


if __name__ == '__main__':
    unittest.main()
