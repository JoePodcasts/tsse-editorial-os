import copy
import csv
import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from urllib.error import URLError

import archive_sync as a

PODCAST = '8a5f01b8-f271-4de0-b289-c224dc4fce0a'


def episode(number=1, **overrides):
    item = {'id': str(uuid.UUID(int=number)), 'number': number,
            'title': 'A "quoted", café title', 'published_at': '2026-01-01T04:00:00-08:00',
            'duration': 195, 'description': 'Official summary, with\na line break.',
            'slug': 'episode-' + str(number), 'enclosure_url': 'https://audio.example/one.mp3',
            'season': {'number': 1, 'href': a.SIMPLECAST_API + '/seasons/one', 'next_episode_number': 2},
            'type': 'full', 'status': 'published', 'is_hidden': False,
            'image_url': None, 'updated_at': '2026-01-02T04:00:00-08:00', 'guid': 'guid-' + str(number)}
    item.update(overrides)
    return item


def detail(item, **overrides):
    result = dict(item, podcast={'id': PODCAST}, audio_content_type='audio/mpeg',
                  long_description='<p>Exact <strong>notes</strong> &amp; links.</p>',
                  transcription='<p>[00:00:00] Gopi Rangan: café &amp; tea.<br />Keep  two spaces.</p>')
    result.update(overrides)
    return result


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.stage = self.root / 'stage'
        self.stage.mkdir()
        self.one = episode()

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, items=None, details=None, pilot=(1,), stamp='2026-01-03T00:00:00+00:00'):
        items = items if items is not None else [self.one]
        details = details if details is not None else {i['id']: detail(i) for i in items}
        def fetch(url):
            value = details[url.rsplit('/', 1)[-1]]
            if isinstance(value, Exception):
                raise value
            return value
        return a.build(self.stage, self.repo, items, PODCAST, fetch, set(pilot), stamp)

    def manifest(self):
        return a.read_json(self.stage / 'manifest.json')

    def record(self):
        return a.load_catalogue(self.stage / 'catalogue.jsonl')[0]

    def test_full_round_trip_and_exact_source(self):
        report = self.build()
        self.assertTrue(report['validation']['valid'])
        record = self.record()
        self.assertEqual(record['episode_id'], 'simplecast:' + self.one['id'])
        entries = self.manifest()[record['episode_id']]
        original = detail(self.one)
        for kind, field in [('show_notes','long_description'), ('transcript','transcription')]:
            raw = (self.stage / entries[kind]['current_version']['path']).read_bytes()
            self.assertEqual(raw, original[field].encode('utf-8'))
            self.assertEqual(a.digest(raw), entries[kind]['current_version']['sha256'])
        md = (self.stage / entries['markdown_path']).read_text()
        self.assertIn(original['transcription'], md)
        self.assertIn(original['long_description'], md)
        self.assertIn('Gopi Rangan: café & tea.', md)
        self.assertIn('Keep  two spaces.', md)
        self.assertIn('[00:00:00]', md)

    def test_csv_quotes_unicode_and_newlines(self):
        self.build()
        rows = list(csv.DictReader(io.StringIO((self.stage/'exports/catalogue.csv').read_text())))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['title'], self.one['title'])
        self.assertEqual(rows[0]['summary'], self.one['description'])
        self.assertEqual(rows[0]['duration_display'], '00:03:15')
        self.assertEqual(json.loads(rows[0]['speakers_json']), ['Gopi Rangan'])
        self.assertEqual(rows[0]['guest_names_json'],'[]')

    def test_idempotent_reconciliation_and_stable_acquisition_dates(self):
        self.build()
        before = {str(p.relative_to(self.stage)): p.read_bytes() for p in self.stage.rglob('*') if p.is_file() and 'reports' not in p.parts}
        result = self.build(stamp='2026-01-10T00:00:00+00:00')
        after = {str(p.relative_to(self.stage)): p.read_bytes() for p in self.stage.rglob('*') if p.is_file() and 'reports' not in p.parts}
        self.assertEqual(result['changes'], {'new':0,'changed':0,'unchanged':1,'not_seen':0})
        self.assertEqual(before, after)

    def test_source_change_retains_previous_version(self):
        self.build()
        old = self.manifest()[self.record()['episode_id']]['transcript']['current_version']
        self.build(details={self.one['id']:detail(self.one, transcription='<p>Gopi Rangan: Changed at source.</p>')})
        new = self.manifest()[self.record()['episode_id']]['transcript']['current_version']
        self.assertNotEqual(old['sha256'], new['sha256'])
        self.assertTrue((self.stage / old['path']).exists())
        self.assertEqual(self.manifest()[self.record()['episode_id']]['transcript']['previous_versions'],[old])

    def test_missing_optional_content_is_explicit(self):
        self.build(details={self.one['id']:detail(self.one,long_description=None, transcription='')})
        entries=self.manifest()[self.record()['episode_id']]
        self.assertEqual(entries['show_notes']['availability'],'unavailable_at_source')
        self.assertEqual(entries['transcript']['availability'],'unavailable_at_source')
        self.assertIn('unavailable_at_source',(self.stage/entries['markdown_path']).read_text())
        self.assertIsNone(self.record()['artwork_url'])

    def test_metadata_only_episode_without_number_is_member(self):
        item=episode();item.update(number=None, slug=None)
        self.build(items=[item],pilot=())
        self.assertEqual(len(a.load_catalogue(self.stage/'catalogue.jsonl')),1)
        self.assertEqual(self.manifest()[self.record()['episode_id']]['transcript']['availability'],'not_checked')
        self.assertIsNone(self.record()['episode_number'])
        self.assertIsNone(self.record()['episode_url'])

    def test_duplicate_remote_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate canonical'):
            self.build(items=[self.one,self.one])

    def test_conflicting_editorial_number_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate editorial'):
            self.build(items=[self.one,episode(1,id=str(uuid.UUID(int=9)))],pilot=())

    def test_detail_identity_mismatch_is_partial_failure(self):
        result=self.build(details={self.one['id']:detail(self.one,id=str(uuid.UUID(int=9)))})
        self.assertEqual(result['validation_failures'],1)
        self.assertEqual(result['published_episodes'],1)
        self.assertEqual(self.manifest()[self.record()['episode_id']]['transcript']['availability'],'failed')

    def test_detail_wrong_podcast_rejected(self):
        result=self.build(details={self.one['id']:detail(self.one,podcast={'id':str(uuid.UUID(int=9))})})
        self.assertEqual(result['validation_failures'],1)

    def test_retrieval_failure_preserves_accepted_source(self):
        self.build()
        old=self.manifest()
        report=self.build(details={self.one['id']:URLError('timeout')})
        self.assertEqual(report['retrieval_failures'],1)
        self.assertEqual(old,self.manifest())
        self.assertEqual(report['coverage']['official_transcripts'],1)

    def test_malformed_metadata_types_rejected(self):
        for key,value in [('duration',True),('number','1'),('title',{}),('season',[]),('published_at','2026-01-01'),('slug','../outside')]:
            with self.subTest(key=key),self.assertRaises((ValueError,TypeError)):
                a.normalize(episode(**{key:value}),PODCAST)

    def test_manifest_tampering_detected(self):
        self.build()
        e=self.manifest()[self.record()['episode_id']]
        (self.stage/e['transcript']['current_version']['path']).write_text('changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            a.validate(self.stage)

    def test_export_tampering_detected(self):
        self.build()
        e=self.manifest()[self.record()['episode_id']]
        (self.stage/e['markdown_path']).write_text('paraphrased')
        with self.assertRaisesRegex(ValueError,'Markdown round-trip'):
            a.validate(self.stage)

    def test_unicode_passage_offsets(self):
        text='[00:00:00] Gopi Rangan: 😀 café\n\nA second paragraph'
        spans,_=a.segments(text)
        self.assertEqual(len(spans),2)
        for s in spans:self.assertEqual(text[s['start']:s['end']],s['excerpt'])
        self.assertEqual(spans[0]['timestamps'][0]['seconds'],0)

    def test_short_single_speaker_untimed_source_accepted(self):
        self.build(details={self.one['id']:detail(self.one,transcription='<p>Gopi Rangan: Hello.</p>')})
        t=self.manifest()[self.record()['episode_id']]['transcript']
        self.assertTrue(a.available(t))
        self.assertEqual(t['timestamps']['state'],'absent')
        self.assertEqual(t['speaker_labels']['raw_labels'],['Gopi Rangan'])

    def test_shell_is_validation_failure(self):
        result=self.build(details={self.one['id']:detail(self.one,transcription='<!DOCTYPE html><div id="app"></div>')})
        self.assertEqual(result['validation_failures'],1)

    def test_markdown_fences_do_not_terminate_source(self):
        self.build(details={self.one['id']:detail(self.one,transcription='<p>Gopi Rangan: ``` exact.</p>')})
        e=self.manifest()[self.record()['episode_id']]
        self.assertIn('````html',(self.stage/e['markdown_path']).read_text())

    def test_removed_record_retained_and_reappearance_has_same_id(self):
        self.build(items=[self.one,episode(2)],pilot=())
        report=self.build(pilot=())
        self.assertEqual(report['published_episodes'],1)
        self.assertEqual(report['catalogue_records'],2)
        report=self.build(items=[self.one,episode(2)],pilot=())
        self.assertEqual(report['changes']['new'],0)
        self.assertEqual(len(self.manifest()),2)

    def test_legacy_and_intelligence_are_separate_layers(self):
        folder=self.repo/'data/transcripts';folder.mkdir(parents=True)
        (folder/'episode-1_transcript.txt').write_text('Gopi Rangan: Original legacy text.')
        folder=self.repo/'data/episodes/rank4';folder.mkdir(parents=True)
        path=folder/'episode_1.json'
        path.write_text(json.dumps({'episode_number':1,'episode_url':a.SITE_URL+'/episodes/episode-1','primary_theme':'Editorial'}))
        original=path.read_bytes()
        self.build()
        e=self.manifest()[self.record()['episode_id']]
        self.assertEqual(e['intelligence']['layer'],'editorial_intelligence')
        self.assertEqual(e['transcript_legacy']['layer'],'legacy_source')
        self.assertNotIn('Editorial',json.dumps(self.record()))
        self.assertEqual(path.read_bytes(),original)

    def test_br_separated_speaker_turns_are_detected_without_rewriting(self):
        html = '<p>[00:00:00] Guest Name: Hi.<br>[00:00:01] Gopi Rangan: Hello.</p>'
        self.build(details={self.one['id']:detail(self.one, transcription=html)})
        entry = self.manifest()[self.record()['episode_id']]['transcript']
        self.assertEqual(entry['speaker_labels']['raw_labels'], ['Guest Name','Gopi Rangan'])
        text = (self.stage / entry['derived_text']['path']).read_text()
        for span in a.segments(text)[0]:
            self.assertEqual(text[span['start']:span['end']], span['excerpt'])
        self.assertEqual(text, '[00:00:00] Guest Name: Hi.\n[00:00:01] Gopi Rangan: Hello.\n\n')

    def test_crosswalk_conflict_does_not_attach_intelligence(self):
        folder=self.repo/'data/episodes/rank4';folder.mkdir(parents=True)
        (folder/'episode_1.json').write_text(json.dumps({'episode_number':1,'episode_url':'https://wrong.example'}))
        self.build()
        entry=self.manifest()[self.record()['episode_id']]['intelligence']
        self.assertFalse(a.available(entry))
        self.assertEqual(len(entry['unresolved_references']),1)

    def test_sync_publishes_transaction_and_is_idempotent(self):
        def fetch(url, **kwargs):
            if url.endswith('/sites/search'):return {'podcast':{'id':PODCAST}}
            if '/podcasts/' in url:return {'collection':[self.one], 'pages':{'total':1,'current':1,'next':None}}
            return detail(self.one)
        output=self.root/'accepted'
        first=a.sync(output,self.repo,pilot=(1,),fetch=fetch)
        before={str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file() and 'reports' not in p.parts}
        second=a.sync(output,self.repo,pilot=(1,),fetch=fetch)
        after={str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file() and 'reports' not in p.parts}
        self.assertEqual(first['changes']['new'],1)
        self.assertEqual(second['changes']['new'],0)
        self.assertEqual(second['changes']['changed'],0)
        self.assertEqual(before,after)
        self.assertTrue(a.validate(output)['valid'])
        self.assertFalse((self.root/'.accepted.lock').exists())

    def test_invalid_catalogue_cannot_replace_accepted_archive(self):
        def fetch(url, **kwargs):
            if url.endswith('/sites/search'):return {'podcast':{'id':PODCAST}}
            return {'collection':[self.one], 'pages':{'total':1,'current':1,'next':None}}
        output=self.root/'accepted'
        a.sync(output,self.repo,fetch=fetch)
        before=(output/'catalogue.jsonl').read_bytes()
        invalid=episode(duration='broken')
        def bad(url, **kwargs):
            if url.endswith('/sites/search'):return {'podcast':{'id':PODCAST}}
            return {'collection':[invalid], 'pages':{'total':1,'current':1,'next':None}}
        with self.assertRaises(ValueError):a.sync(output,self.repo,fetch=bad)
        self.assertEqual((output/'catalogue.jsonl').read_bytes(),before)

    def test_untrusted_next_host_rejected(self):
        def fetch(url):return {'collection':[self.one], 'pages':{'total':2,'current':1,'next':{'href':'https://evil.example/episodes'}}}
        with self.assertRaisesRegex(ValueError,'host'):a.fetch_catalogue(PODCAST,fetch)

    def test_page_total_change_rejected(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            if len(calls)==1:return {'collection':[self.one], 'pages':{'total':2,'current':1,'next':{'href':f'/podcasts/{PODCAST}/episodes?offset=1'}}}
            return {'collection':[episode(2)], 'pages':{'total':3,'current':2,'next':None}}
        with self.assertRaisesRegex(ValueError,'changed'):a.fetch_catalogue(PODCAST,fetch)

    def test_crlf_source_and_projection_are_preserved(self):
        raw='<p>[00:00:00] Gopi Rangan: First.\r\nStill the same words.</p>'
        self.build(details={self.one['id']:detail(self.one,transcription=raw)})
        entry=self.manifest()[self.record()['episode_id']]['transcript']
        self.assertEqual((self.stage/entry['current_version']['path']).read_bytes(),raw.encode())
        self.assertIn(b'First.\r\nStill', (self.stage/entry['derived_text']['path']).read_bytes())
        self.assertTrue(a.validate(self.stage)['valid'])

    def test_empty_final_page_is_not_complete_catalogue(self):
        def fetch(url):
            if 'offset=1' in url:return {'collection':[], 'pages':{'total':2,'current':2,'next':None}}
            return {'collection':[self.one], 'pages':{'total':2,'current':1,'next':{'href':f'/podcasts/{PODCAST}/episodes?offset=1'}}}
        with self.assertRaisesRegex(ValueError,'Empty catalogue page'):a.fetch_catalogue(PODCAST,fetch)

    def test_pagination_two_pages(self):
        pages=[]
        def fetch(url):
            pages.append(url)
            if len(pages)==1:return {'collection':[self.one], 'pages':{'total':2,'current':1,'next':{'href':f'/podcasts/{PODCAST}/episodes?offset=1'}}}
            return {'collection':[episode(2)], 'pages':{'total':2,'current':2,'next':None}}
        items,result=a.fetch_catalogue(PODCAST,fetch)
        self.assertEqual(len(items),2)
        self.assertEqual(result['pages'],2)

    def test_bad_pagination_and_duplicates(self):
        variants=[
            {'collection':[self.one], 'pages':{'total':2,'current':1,'next':None}},
            {'collection':[self.one], 'pages':{'total':1,'current':1,'next':{'href':'https://evil.example'}}},
            {'collection':[self.one,self.one], 'pages':{'total':1,'current':1,'next':None}},
            {'collection':None, 'pages':{}},
        ]
        for page in variants:
            with self.subTest(page=page),self.assertRaises(ValueError):a.fetch_catalogue(PODCAST,lambda u:page)

    def test_fatal_remote_failure_preserves_previous_archive(self):
        self.build()
        before=(self.stage/'catalogue.jsonl').read_bytes()
        def fetch(url,**kwargs):raise URLError('offline')
        with self.assertRaises(URLError):a.sync(self.stage,self.repo,fetch=fetch)
        self.assertEqual((self.stage/'catalogue.jsonl').read_bytes(),before)
        self.assertTrue((self.root/'.stage-last-failure.json').exists())


if __name__=='__main__':
    unittest.main()
