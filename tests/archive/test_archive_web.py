"""Read-only adapter contracts, using the actual preserved archive and index.

These checks are additional to the portable Phase 1/2 fixture tests. They skip
explicitly when a checkout has not yet materialized the full local archive.
"""
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import archive_sync as archive
import archive_search as search
import archive_web as web

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless((ROOT / 'archive/search/archive.sqlite3').exists(), 'Full archive index is not materialized')
class ArchiveWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = web.ArchiveApp(ROOT / 'archive')
        cls.records, cls.manifest = cls.app.snapshot()
        cls.by_number = {r['episode_number']: r for r in cls.records}

    def get(self, path, **params):
        return self.app.api(path, params)

    def test_live_coverage(self):
        counts=self.get('/api/archive')
        self.assertEqual(counts['episodes'],len(self.records))
        self.assertEqual(counts['markdown_files'],len(self.records))
        for kind in ('transcript','show_notes'):
            self.assertEqual(counts[kind],sum(archive.available(self.manifest[r['episode_id']][kind]) for r in self.records))
        self.assertEqual(counts['timestamped_transcripts'],sum(archive.available(self.manifest[r['episode_id']]['transcript']) and self.manifest[r['episode_id']]['transcript'].get('timestamps',{}).get('state')=='present' for r in self.records))

    def test_browse_all_published_once_and_sort(self):
        all_rows = []
        for offset in range(0, len(self.records), 24):
            data = self.get('/api/episodes', offset=str(offset))
            all_rows.extend(data['episodes'])
            self.assertEqual(data['total'], len(self.records))
        self.assertEqual(len({r['episode_id'] for r in all_rows}), len(self.records))
        self.assertEqual([r['episode_number'] for r in all_rows], [r['episode_number'] for r in sorted(self.records,key=lambda r:r['published_at'],reverse=True)])
        for sort in ('oldest', 'number'):
            self.assertEqual(self.get('/api/episodes', sort=sort)['episodes'][0]['episode_number'], 1)

    def test_every_catalogue_episode_has_detail(self):
        for record in self.records:
            detail = self.get('/api/episodes/' + record['remote_id'])
            self.assertEqual(detail['official_title'], record['official_title'])
            self.assertEqual(detail['duration_seconds'], record['duration_seconds'])
            self.assertEqual(detail['url'], '/episodes/' + record['remote_id'])

    def test_five_required_queries_use_existing_search(self):
        cases = [('proof of value', 'metadata', 195, 'episode_title'),
                 ('Gokul Rajaram', 'metadata', 2, 'speaker_labels'),
                 ('Commerce Ventures', 'show_notes', 75, 'show_notes'),
                 ('relentlessly resourceful', 'transcript', 2, 'transcript'),
                 ('choosing a partner in life', 'transcript', 191, 'transcript')]
        for q, source, episode, kind in cases:
            with self.subTest(query=q):
                data = self.get('/api/search', q=q, source=source, limit='100')
                doc = next(d for d in data['results'] if d['episode_number'] == episode and d['source_type'] == kind)
                original = search.context(self.app.root, doc['passage_id'])
                self.assertEqual(doc['text'], original['text'])
                self.assertEqual(doc['locator'], original['locator'])
                self.assertIn('passage=' + doc['passage_id'], doc['url'])
                self.assertEqual(doc['source_label'], web.SOURCE_LABELS[kind])

    def test_source_filter_and_episode_scope(self):
        data = self.get('/api/search', q='relentlessly resourceful', source='transcript', episode='2')
        self.assertTrue(data['results'])
        self.assertTrue(all(d['episode_number'] == 2 and d['source_type'] == 'transcript' for d in data['results']))

    def test_timestamp_and_source_speaker(self):
        data = self.get('/api/search', q='choosing a partner in life', source='transcript', episode='191')
        doc = data['results'][0]
        self.assertEqual(doc['timestamp'], '[00:23:15]')
        self.assertEqual(doc['speaker_label'], 'Justin Smith-Lorenzetti')
        self.assertEqual(doc['speaker_accuracy'], 'unverified')

    def test_missing_timestamp_not_fabricated_and_short_labels_preserved(self):
        record = self.by_number[74]
        data = self.get('/api/episodes/' + record['remote_id'] + '/content', source='transcript')
        self.assertTrue(data['passages'])
        self.assertTrue(all(p['timestamp'] is None for p in data['passages']))
        record = self.by_number[106]
        data = self.get('/api/episodes/' + record['remote_id'] + '/content', source='transcript')
        self.assertIn('Gopi', {p['speaker_label'] for p in data['passages']})

    def test_deep_link_exact_offsets_and_identity(self):
        doc = self.get('/api/search', q='relentlessly resourceful', source='transcript', episode='2')['results'][0]
        record = self.by_number[2]
        content = self.get('/api/episodes/' + record['remote_id'] + '/content', source='transcript', passage=doc['passage_id'])
        selected = content['selected_passage']
        self.assertEqual(selected['passage_id'], doc['passage_id'])
        self.assertEqual(content['text'][selected['locator']['start']:selected['locator']['end']], doc['text'])
        self.assertIn(doc['passage_id'], {p['passage_id'] for p in content['passages']})

    def test_notes_are_the_safe_text_projection(self):
        record = self.by_number[75]
        data = self.get('/api/episodes/' + record['remote_id'] + '/content', source='show_notes')
        source = self.manifest[record['episode_id']]['show_notes']
        self.assertEqual(data['text'], (self.app.root / source['derived_text']['path']).read_text())
        self.assertNotIn('<p>', data['text'])
        self.assertEqual(data['provenance']['original']['sha256'], source['current_version']['sha256'])

    def test_wrong_episode_source_unknown_passage_rejected(self):
        doc = self.get('/api/search', q='relentlessly resourceful', episode='2', source='transcript')['results'][0]
        for number, kind, pid in [(191, 'transcript', doc['passage_id']), (2, 'show_notes', doc['passage_id']),
                                  (2, 'transcript', '0' * 64), (2, 'transcript', '<script>')]:
            with self.subTest(number=number, source=kind), self.assertRaises(web.APIError) as caught:
                self.get('/api/episodes/' + self.by_number[number]['remote_id'] + '/content', source=kind, passage=pid)
            self.assertEqual(caught.exception.status, 404)

    def test_source_integrity_failure_is_explicit(self):
        record = self.by_number[2]
        with patch.object(web.archive, 'digest', return_value='mismatch'), self.assertRaises(web.APIError) as caught:
            self.app.content(record, self.manifest[record['episode_id']], 'transcript')
        self.assertEqual(caught.exception.status, 503)

    def test_unavailable_sources_have_no_invented_content(self):
        record = self.by_number[2]
        entries = {'transcript': {'availability': 'unavailable_at_source'}, 'show_notes': {'availability': 'pending'}}
        detail = self.app.episode(record, entries)
        self.assertFalse(detail['sources']['transcript']['available'])
        self.assertEqual(detail['sources']['show_notes']['availability'], 'pending')
        with self.assertRaises(web.APIError) as caught:
            self.app.content(record, entries, 'transcript')
        self.assertEqual(caught.exception.status, 404)

    def test_metadata_match_provenance(self):
        doc = self.get('/api/search', q='Gokul Rajaram', source='metadata')['results'][0]
        detail = self.get('/api/episodes/' + self.by_number[2]['remote_id'], passage=doc['passage_id'])
        self.assertEqual(detail['selected_match']['source_type'], 'speaker_labels')
        self.assertEqual(detail['selected_match']['speaker_accuracy'], 'unverified')

    def test_unknown_metadata_passage_is_not_reported_as_service_failure(self):
        for pid in ('invalid', '0' * 64):
            with self.subTest(passage=pid), self.assertRaises(web.APIError) as caught:
                self.get('/api/episodes/' + self.by_number[195]['remote_id'], passage=pid)
            self.assertEqual(caught.exception.status, 404)

    def test_no_results_and_empty_search(self):
        for q in ('NoSuchArchiveToken9ZZZZ', '', '!!!', '" OR NoSuchArchiveToken9ZZZZ *'):
            self.assertEqual(self.get('/api/search', q=q)['results'], [])

    def test_invalid_input_bounds(self):
        for path, params in [('/api/search', {'q': 'x' * 301}), ('/api/search', {'source': 'vector'}),
                             ('/api/search', {'limit': '-1'}), ('/api/search', {'limit': '10000'}),
                             ('/api/episodes', {'sort': 'bogus'}), ('/api/episodes', {'offset': '-1'}),
                             ('/api/episodes', {'limit': 'abc'})]:
            with self.subTest(path=path, params=params), self.assertRaises(web.APIError):
                self.get(path, **params)

    def test_numeric_alias_and_unknown_episode(self):
        self.assertEqual(self.get('/api/episodes/195')['remote_id'], self.by_number[195]['remote_id'])
        with self.assertRaises(web.APIError): self.get('/api/episodes/999999')

    def test_adapter_does_not_change_retrieval_ranking(self):
        args = dict(q='founder', source='transcript', limit='10')
        adapted = self.get('/api/search', **args)
        original = search.query(self.app.root, 'founder', 'transcript', limit=10)
        self.assertEqual([d['passage_id'] for d in adapted['results']], [d['passage_id'] for d in original])
        self.assertTrue(adapted['has_more'])

    def test_static_routes_are_an_explicit_allowlist(self):
        self.assertNotIn('/archive/catalogue.jsonl', web.ASSETS)
        self.assertNotIn('/archive/search/archive.sqlite3', web.ASSETS)
        for path in web.ASSETS.values(): self.assertTrue(path.is_file())
        source = (ROOT / 'web/app.js').read_text()
        self.assertNotRegex(source, r'\.innerHTML\s*=|insertAdjacentHTML|document\.write\(')


if __name__ == '__main__':
    unittest.main()
