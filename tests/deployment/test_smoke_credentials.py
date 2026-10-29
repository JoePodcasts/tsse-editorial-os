"""Exercise credential selection with synthetic values and a fake smoke process."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

WRAPPER = Path(__file__).with_name('smoke-with-project-env.mjs').resolve()


@unittest.skipUnless(shutil.which('node'), 'Node is required by the deployment workflow')
class SmokeCredentialTests(unittest.TestCase):
    def run_wrapper(self, project, fallback, expected, exit_code=0):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.vercel').mkdir()
            (root / '.vercel/.env.production.local').write_text(
                f'VERCEL_AUTOMATION_BYPASS_SECRET="{project}"\n')
            fake = root / 'python3'
            fake.write_text('#!/bin/sh\n[ "$VERCEL_AUTOMATION_BYPASS_SECRET" = "$EXPECTED" ] || exit 99\nexit "$CHILD_EXIT"\n')
            fake.chmod(0o700)
            result = subprocess.run(['node', str(WRAPPER), 'https://example.vercel.app'],
                cwd=root, capture_output=True, text=True, env={**os.environ,
                    'PATH': str(root) + os.pathsep + os.environ['PATH'],
                    'VERCEL_AUTOMATION_BYPASS_SECRET': fallback,
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
