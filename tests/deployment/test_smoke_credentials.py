"""Exercise credential selection with synthetic values and a fake smoke process."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

WRAPPER = Path(__file__).with_name('smoke-with-project-env.mjs').resolve()


@unittest.skipUnless(shutil.which('node'), 'Node is required by the deployment workflow')
class SmokeCredentialTests(unittest.TestCase):
    def run_wrapper(self, project, fallback, expected, exit_code=0, lookup=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.vercel').mkdir()
            (root / '.vercel/.env.production.local').write_text(
                f'VERCEL_AUTOMATION_BYPASS_SECRET="{project}"\n')
            fake = root / 'python3'
            fake.write_text('#!/bin/sh\n[ "$VERCEL_AUTOMATION_BYPASS_SECRET" = "$EXPECTED" ] || exit 99\nexit "$CHILD_EXIT"\n')
            fake.chmod(0o700)
            args = ['node']
            if lookup is not None:
                mock = root / 'fetch.mjs'
                mock.write_text('globalThis.fetch = async (url, options) => {\n'
                    'if (url !== "https://api.vercel.com/v9/projects/prj_test?teamId=team_test" || '
                    '(options.method && options.method !== "GET") || options.redirect !== "error") '
                    'throw new Error("Unexpected request");\n'
                    'return {ok: true, json: async () => (' + json.dumps(lookup) + ')};\n};\n')
                args += ['--import', str(mock)]
            result = subprocess.run(args + [str(WRAPPER), 'https://example.vercel.app'],
                cwd=root, capture_output=True, text=True, env={**os.environ,
                    'PATH': str(root) + os.pathsep + os.environ['PATH'],
                    'VERCEL_AUTOMATION_BYPASS_SECRET': fallback,
                    'VERCEL_TOKEN': 'synthetic-api-token' if lookup is not None else '',
                    'VERCEL_PROJECT_ID': 'prj_test', 'VERCEL_ORG_ID': 'team_test',
                    'EXPECTED': expected, 'CHILD_EXIT': str(exit_code)})
            for value in (project, fallback):
                if value:
                    self.assertNotIn(value, result.stdout + result.stderr)
            return result

    def test_pulled_project_value_takes_precedence(self):
        self.assertEqual(self.run_wrapper('synthetic-project', 'synthetic-stale', 'synthetic-project').returncode, 0)

    def test_existing_github_value_is_fallback(self):
        self.assertEqual(self.run_wrapper('', 'synthetic-github', 'synthetic-github').returncode, 0)

    def test_missing_credential_fails_closed(self):
        self.assertNotEqual(self.run_wrapper('', '', '').returncode, 0)

    def test_smoke_failure_propagates(self):
        self.assertEqual(self.run_wrapper('synthetic-project', '', 'synthetic-project', 7).returncode, 7)

    def test_reads_existing_automation_credential_only(self):
        project = {'id': 'prj_test', 'accountId': 'team_test', 'protectionBypass': {
            'synthetic-share': {'scope': 'shareable-link'},
            'synthetic-existing': {'scope': 'automation-bypass'}}}
        self.assertEqual(self.run_wrapper('', 'synthetic-stale', 'synthetic-existing', lookup=project).returncode, 0)

    def test_missing_existing_credential_does_not_create_one_or_use_stale_fallback(self):
        self.assertNotEqual(self.run_wrapper('', 'synthetic-stale', '', lookup={
            'id': 'prj_test', 'accountId': 'team_test'}).returncode, 0)

    def test_wrong_project_is_rejected(self):
        self.assertNotEqual(self.run_wrapper('', '', '', lookup={
            'id': 'prj_wrong', 'accountId': 'team_test'}).returncode, 0)
