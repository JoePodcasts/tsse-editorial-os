"""Portable deliverable contracts; actual archive data is never mutated."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import archive_files as files
import archive_sync as archive
import archive_web as web

ROOT = Path(__file__).resolve().parents[2] / 'archive'


@unittest.skipUnless((ROOT / 'exports/catalogue.csv').exists(), 'Materialize the archive exports first')
class PortableFilesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = files.ExportLibrary(ROOT)
        cls.report = cls.library.inventory()
        cls.records = [r for r in archive.load_catalogue(ROOT/'catalogue.jsonl') if r['public_presence']=='present']
        cls.manifest = archive.read_json(ROOT/'manifest.json')
        cls.count = len(cls.records)

    def test_counts_utf8_and_complete_sections(self):
        for key in ['published_episodes', 'csv_rows', 'markdown_files', 'metadata_documents']:
            self.assertEqual(self.report[key], self.count)
        self.assertTrue(self.report['utf8_valid'])
        for kind, key in [('show_notes','show_note_documents'),('transcript','transcript_documents')]:
            self.assertEqual(self.report[key],sum(archive.available(self.manifest[r['episode_id']][kind]) for r in self.records))
        self.assertEqual(self.report['timestamped_transcripts'],sum(archive.available(self.manifest[r['episode_id']]['transcript']) and self.manifest[r['episode_id']]['transcript'].get('timestamps',{}).get('state')=='present' for r in self.records))

    def test_textual_fidelity_no_changed_words_or_timestamps(self):
        self.assertEqual(self.report['transcript_wording_changes'], [])
        self.assertEqual(self.report['transcript_timestamp_changes'], [])
        self.assertTrue(self.report['source_html_preserved'])

    def test_all_csv_fields_are_existing_export_fields(self):
        self.assertEqual(self.report['csv_fields'], list(archive.CSV_FIELDS))
        self.assertEqual(self.library.csv_bytes(), (ROOT / 'exports/catalogue.csv').read_bytes())

    def test_all_files_have_unique_canonical_mapping_and_exact_download_bytes(self):
        self.assertEqual(len({f['remote_id'] for f in self.report['files']}), self.count)
        for info in self.report['files']:
            actual, raw = self.library.markdown(info['remote_id'])
            self.assertEqual(info['filename'], info['remote_id'] + '.md')
            self.assertEqual(raw, (ROOT / 'exports/episodes' / info['filename']).read_bytes())
            self.assertEqual(actual['sha256'], archive.digest(raw))

    def test_zip_reproducible_across_new_instances_and_only_existing_markdown(self):
        first = self.library.zip_bytes()
        second = files.ExportLibrary(ROOT).zip_bytes()
        self.assertEqual(first, second)
        with zipfile.ZipFile(io.BytesIO(first)) as bundle:
            names = bundle.namelist()
            self.assertEqual(len(names), self.count)
            self.assertEqual(names, sorted(names))
            for entry in bundle.infolist():
                self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertTrue(entry.filename.startswith('episodes/'))
                self.assertTrue(entry.filename.endswith('.md'))
                self.assertEqual(bundle.read(entry), (ROOT / 'exports' / entry.filename).read_bytes())

    def test_no_arbitrary_file_lookup(self):
        for identity in ['../manifest.json', '/etc/passwd', '0' * 36]:
            with self.assertRaises(ValueError): self.library.markdown(identity)

    def test_generated_file_view_is_actual_artifact(self):
        app = web.ArchiveApp(ROOT)
        record = app.resolve('195', app.snapshot()[0])
        info = app.api('/api/episodes/195/file', {})
        self.assertEqual(info['text'].encode('utf-8'), (ROOT / 'exports/episodes' / (record['remote_id'] + '.md')).read_bytes())
        self.assertEqual(app.api('/api/episodes/195', {})['file']['filename'], info['filename'])

    def test_noncanonical_manifest_path_is_rejected(self):
        record = {'remote_id': 'safe'}
        with self.assertRaises(ValueError): files.export_path(ROOT, record, {'markdown_path': '../source.md'})

    def test_export_symlink_cannot_leave_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'exports/episodes').mkdir(parents=True)
            (root / 'exports/episodes/x.md').symlink_to('/etc/hosts')
            with self.assertRaises(ValueError):
                files.export_path(root, {'remote_id': 'x'}, {'markdown_path': 'exports/episodes/x.md'})

    def test_changed_export_invalidates_verified_cache(self):
        # A controlled temp export validates cache invalidation without copying
        # the archive or editing one byte in its accepted deliverables.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'exports/episodes').mkdir(parents=True)
            for name in ['catalogue.jsonl', 'manifest.json', 'exports/catalogue.csv']:
                (root / name).write_text('before')
            library = files.ExportLibrary(root)
            with patch.object(files, 'validate_exports', return_value={'version': 1}) as validate:
                self.assertEqual(library.inventory()['version'], 1)
                library.inventory(); self.assertEqual(validate.call_count, 1)
                (root / 'exports/catalogue.csv').write_text('after-change')
                library.inventory(); self.assertEqual(validate.call_count, 2)

    def test_words_changed_in_actual_markdown_are_rejected(self):
        target = ROOT / 'exports/episodes' / self.report['files'][0]['filename']
        original = Path.read_bytes
        def changed(path):
            raw = original(path)
            return raw.replace(b'Canonical identity:', b'Altered identity:', 1) if path == target else raw
        with patch.object(Path, 'read_bytes', changed), self.assertRaisesRegex(ValueError, 'Markdown differs'):
            files.validate_exports(ROOT)

    def test_variable_fences_are_parsed_without_rendering_html(self):
        source = '<p>Literal ``` and <script>text only</script></p>'
        document = '## Example\n\n' + archive.fence(source, 'html')
        self.assertEqual(files.fenced_section(document, 'Example'), source + '\n')


if __name__ == '__main__':
    unittest.main()
