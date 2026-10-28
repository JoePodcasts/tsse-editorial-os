import json
import tempfile
import unittest
from pathlib import Path

from check_prebuilt import check


class PrebuiltTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / '.vercel/output'
        self.function = self.output / 'functions/api/archive_function.func'
        self.function.mkdir(parents=True)
        self.config = {'runtime': 'python3.12', 'handler': 'vc__handler__python.vc_handler'}
        for name in ('vc__handler__python.py', 'api/archive_function.py',
                     'vercel_runtime/archive_public.py',
                     'vercel_runtime/archive/search/archive.sqlite3',
                     'vercel_runtime/archive/catalogue.jsonl',
                     'vercel_runtime/archive/sync-status.json'):
            path = self.function / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture')
        (self.output / 'static').mkdir()
        (self.output / 'static/index.html').write_text('homepage')
        (self.output / 'config.json').write_text(json.dumps({'routes': [
            {'src': '^/api/(.*)$', 'dest': '/api/archive_function?route=$1'}]}))
        self.save()

    def save(self):
        (self.function / '.vc-config.json').write_text(json.dumps(self.config))

    def test_accepts_bundled_files(self):
        self.assertEqual(check(self.root)['runtime'], 'python3.12')

    def test_static_only_build_is_rejected(self):
        (self.function / '.vc-config.json').unlink()
        with self.assertRaisesRegex(ValueError, 'function is missing'):
            check(self.root)

    def test_cli_file_map_must_resolve_to_real_files(self):
        name = 'vercel_runtime/archive/search/archive.sqlite3'
        target = self.root / name
        target.parent.mkdir(parents=True)
        (self.function / name).rename(target)
        self.config['filePathMap'] = {name: name}
        self.save()
        check(self.root)
        target.unlink()
        with self.assertRaisesRegex(ValueError, 'required file'):
            check(self.root)

    def test_wrong_route_or_runtime_is_rejected(self):
        self.config['runtime'] = 'nodejs24.x'
        self.save()
        with self.assertRaisesRegex(ValueError, 'Python 3.12'):
            check(self.root)
        self.config['runtime'] = 'python3.12'
        self.save()
        (self.output / 'config.json').write_text('{"routes": []}')
        with self.assertRaisesRegex(ValueError, 'rewrite'):
            check(self.root)
