import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.error import URLError

import archive_library as lib
import archive_search as search
import archive_sync as a

FIXTURE=Path(__file__).parent/'fixtures/real_episodes.json'


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.root=self.base/'archive';self.root.mkdir();self.repo=self.base/'repo';self.repo.mkdir()
        self.details=a.read_json(FIXTURE)['episodes']
        self.podcast=self.details[0]['podcast']['id']
        self.lookup={d['id']:d for d in self.details}
        a.build(self.root,self.repo,self.details,self.podcast,lambda u:self.lookup[u.rsplit('/',1)[-1]],set(),a.now())

    def fetch(self,url):
        return self.lookup[url.rsplit('/',1)[-1]]

    def ingest(self,**kwargs):
        return lib.ingest(self.root,fetch=self.fetch,delay=0,**kwargs)

    def test_archive_wide_real_sources_and_full_markdown(self):
        run=self.ingest()
        self.assertEqual(run['accepted'],5);self.assertEqual(run['failures'],[])
        m=a.read_json(self.root/'manifest.json')
        for d in self.details:
            e=m['simplecast:'+d['id']]
            self.assertEqual((self.root/e['transcript']['current_version']['path']).read_text(),d['transcription'])
            self.assertTrue((self.root/e['markdown_path']).exists())
        self.assertTrue(a.validate(self.root)['valid'])

    def test_unchanged_ingestion_does_no_network_work(self):
        self.ingest()
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file() and 'reports' not in p.parts}
        def unexpected(url):raise AssertionError('Unexpected request')
        run=lib.ingest(self.root,fetch=unexpected,delay=0)
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file() and 'reports' not in p.parts}
        self.assertEqual(run['queued'],0);self.assertEqual(before,after)

    def test_limit_and_resume(self):
        first=self.ingest(limit=2);second=self.ingest()
        self.assertEqual(first['accepted'],2);self.assertEqual(second['accepted'],3)
        self.assertEqual(len(list((self.root/'exports/episodes').glob('*.md'))),5)

    def test_missing_sources_remain_in_catalogue_and_metadata_search(self):
        missing=dict(self.details[0],long_description=None,transcription=None)
        self.lookup[missing['id']]=missing
        self.ingest();search.rebuild(self.root)
        r=next(r for r in a.load_catalogue(self.root/'catalogue.jsonl') if r['remote_id']==missing['id'])
        hits=search.query(self.root,str(r['episode_number']),source='metadata')
        self.assertTrue(any(h['episode_id']==r['episode_id'] for h in hits))
        m=a.read_json(self.root/'manifest.json')[r['episode_id']]
        self.assertEqual(m['transcript']['availability'],'unavailable_at_source')
        self.assertTrue((self.root/m['markdown_path']).exists())

    def test_failed_detail_does_not_remove_episode(self):
        def fail(url):raise URLError('offline')
        run=lib.ingest(self.root,fetch=fail,delay=0,limit=1)
        self.assertEqual(run['failures'][0]['type'],'retrieval')
        self.assertEqual(len(a.load_catalogue(self.root/'catalogue.jsonl')),5)
        self.assertEqual(len(list((self.root/'exports/episodes').glob('*.md'))),5)

    def test_changed_source_metadata_refreshes_only_changed_episode(self):
        self.ingest()
        # Fixtures change metadata coherently, as a subsequent catalogue sync would.
        d=self.details[0];eid='simplecast:'+d['id'];m=a.read_json(self.root/'manifest.json');r=a.load_catalogue(self.root/'catalogue.jsonl')
        old=m[eid]['transcript']['current_version']
        changed=dict(d,updated_at='2026-10-26T08:00:00+00:00',transcription=d['transcription']+'<p>Controlled fixture source edit.</p>')
        self.lookup[d['id']]=changed
        for record in r:
            if record['episode_id']==eid:
                record['source_updated_at']=changed['updated_at']
                m[eid]['metadata']=a.source(self.root,d['id'],'metadata',a.encoded(a.metadata(changed)),'application/json',a.SIMPLECAST_API,a.now(),m[eid]['metadata'])
        lib.materialize(self.root,r,m)
        run=self.ingest();self.assertEqual(run['accepted'],1)
        e=a.read_json(self.root/'manifest.json')[eid]['transcript']
        self.assertIn(old,e['previous_versions'])

    def test_checkpoint_resumes_after_process_interruption(self):
        calls=[]
        def interrupted(url):
            calls.append(url)
            if len(calls)==3:raise KeyboardInterrupt()
            return self.fetch(url)
        run=lib.ingest(self.root,fetch=interrupted,delay=0)
        self.assertTrue(run['interrupted']);self.assertEqual(run['accepted'],2)
        self.assertEqual(self.ingest()['accepted'],3)

    def test_durable_checkpoint_replays_without_remote_request(self):
        with patch.object(lib,'publish',side_effect=OSError('simulated process failure before publication')):
            with self.assertRaises(OSError):self.ingest()
        journal=self.base/'.archive-ingest-checkpoints'
        self.assertEqual(len(list(journal.glob('*.json'))),5)
        def unexpected(url):raise AssertionError('Should replay durable checkpoint')
        run=lib.ingest(self.root,fetch=unexpected,delay=0)
        self.assertEqual(run['checkpoint_reused'],5)
        self.assertEqual(run['accepted'],5)

    def test_discovered_short_labels_are_not_replaced_with_full_names(self):
        cases=a.read_json(Path(__file__).parent/'fixtures/real_format_cases.json')['episodes']
        a.build(self.root,self.repo,cases,self.podcast,lambda u:next(d for d in cases if d['id']==u.rsplit('/',1)[-1]),{106,113},a.now())
        m=a.read_json(self.root/'manifest.json')
        for d in cases:
            if d['number'] not in (106,113):continue
            labels=m['simplecast:'+d['id']]['transcript']['speaker_labels']['raw_labels']
            self.assertIn('Gopi',labels)
            self.assertNotIn('Gopi Rangan',labels)
            stats=search.structure(d['transcription'],a.project(d['transcription']))
            self.assertTrue(stats['unusual']);self.assertIn('Gopi',stats['short_source_labels'])

    def test_discovered_single_paragraph_151_has_sourceable_turns(self):
        d=next(d for d in a.read_json(Path(__file__).parent/'fixtures/real_format_cases.json')['episodes'] if d['number']==151)
        a.build(self.root,self.repo,[d],self.podcast,lambda u:d,{151},a.now())
        r=next(r for r in a.load_catalogue(self.root/'catalogue.jsonl') if r['episode_number']==151)
        entry=a.read_json(self.root/'manifest.json')[r['episode_id']]['transcript']
        docs=list(search.source_documents(self.root,r,entry,'transcript'))
        self.assertTrue(any(x['speaker_label']=='Gopi Rangan' for x in docs))
        for doc in docs:search.verify_document(self.root,doc)
        self.assertTrue(search.structure(d['transcription'],a.project(d['transcription']))['multiple_turns_single_paragraph'])

    def test_passage_ids_and_source_spans_are_stable(self):
        self.ingest();search.rebuild(self.root)
        original=(self.root/'derived/passages.jsonl').read_bytes()
        first=json.loads(original.splitlines()[0])
        text=(self.root/first['locator']['text_path']).read_text()
        self.assertEqual(text[first['locator']['start']:first['locator']['end']],first['text'])
        search.rebuild(self.root)
        self.assertEqual(original,(self.root/'derived/passages.jsonl').read_bytes())

    def test_interrupted_refresh_retains_unprocessed_checkpoint(self):
        self.ingest()
        d=next(d for d in self.details if d['number']==195)
        eid='simplecast:'+d['id'];m=a.read_json(self.root/'manifest.json')
        journal=self.base/'.archive-ingest-checkpoints';checkpoint=journal/(d['id']+'.json')
        payload=lib.safe_detail(d,{'remote_id':d['id'],'podcast_id':self.podcast})
        lib.atomic_json(checkpoint,{'metadata_sha256':m[eid]['metadata']['current_version']['sha256'],
                                   'retrieved_at':a.now(),'payload':payload,'payload_sha256':a.digest(a.encoded(payload))})
        def stop(url):raise KeyboardInterrupt()
        run=lib.ingest(self.root,fetch=stop,delay=0,refresh_limit=5,min_age_days=0)
        self.assertTrue(run['interrupted'])
        self.assertTrue(checkpoint.exists())
        resumed=lib.ingest(self.root,fetch=self.fetch,delay=0,refresh_limit=5,min_age_days=0)
        self.assertEqual(resumed['checkpoint_reused'],1)

    def test_local_provisional_episode_is_not_official_membership(self):
        folder=self.repo/'data/episodes/active';folder.mkdir(parents=True)
        (folder/'episode_196.json').write_text(json.dumps({'episode_number':196,'title':'UNPUBLISHEDONLYLOCAL196'}))
        self.ingest();built=search.rebuild(self.root)
        self.assertEqual(built['searchable_metadata_records'],5)
        self.assertEqual(search.query(self.root,'UNPUBLISHEDONLYLOCAL196'),[])

    def test_real_pilot_formats_and_passage_locations(self):
        self.ingest();search.rebuild(self.root)
        docs=[json.loads(x) for x in (self.root/'derived/passages.jsonl').read_text().splitlines()]
        for doc in docs:search.verify_document(self.root,doc)
        by_number={d['number']:d for d in self.details}
        untimed=search.structure(by_number[75]['transcription'],a.project(by_number[75]['transcription']))
        self.assertFalse(untimed['has_timestamps']);self.assertTrue(untimed['has_labels'])
        recent=search.structure(by_number[195]['transcription'],a.project(by_number[195]['transcription']))
        self.assertTrue(recent['multiple_turns_single_paragraph'])
        self.assertTrue(any(d['speaker_label']=='Gopi Rangan' and d['episode_number']==195 for d in docs))

    def test_lexical_queries_source_types_and_provenance(self):
        self.ingest();search.rebuild(self.root)
        for query,source,number in [('Gokul Rajaram','transcript',2),('proof of value','episode_title',195),('Commerce Ventures','show_notes',75)]:
            with self.subTest(query=query):
                hits=search.query(self.root,query,source=source,episode=number,limit=3)
                self.assertTrue(hits)
                self.assertTrue(all(h['source_type']==source for h in hits))
                for h in hits:
                    search.verify_document(self.root,h)
                    self.assertEqual(search.context(self.root,h['passage_id'])['text'],h['text'])

    def test_offline_index_rebuild_and_deterministic_ranking(self):
        self.ingest();first=search.rebuild(self.root)
        before=(self.root/'search/archive.sqlite3').read_bytes()
        results=search.query(self.root,'founders',limit=10)
        second=search.rebuild(self.root)
        self.assertTrue(second['index_reused']);self.assertEqual(before,(self.root/'search/archive.sqlite3').read_bytes())
        self.assertEqual(results,search.query(self.root,'founders',limit=10))
        (self.root/'search/archive.sqlite3').unlink();search.rebuild(self.root)
        self.assertEqual(before,(self.root/'search/archive.sqlite3').read_bytes())

    def test_actual_search_quality_fixtures(self):
        self.ingest();search.rebuild(self.root)
        cases=a.read_json(Path(__file__).parent/'fixtures/search_queries.json')['queries']
        for case in cases:
            with self.subTest(query=case['query']):
                hits=search.query(self.root,case['query'],source=case['source'],limit=50)
                self.assertTrue(any(h['episode_number']==case['expected_episode'] for h in hits))
                self.assertTrue(all(h['source_type'] not in ('transcript','show_notes') if case['source']=='metadata' else h['source_type']==case['source'] for h in hits))

    def test_prose_colon_prefix_is_not_a_speaker_name(self):
        text='The more important question for me is: why now?\nGopi Rangan: A source label.'
        spans,flags=a.segments(text)
        self.assertIsNone(spans[0]['speaker_label'])
        self.assertEqual(flags['speaker_labels']['raw_labels'],['Gopi Rangan'])
        self.assertEqual([m.group(1) or m.group(2) for m in search.turns(text)],['Gopi Rangan'])

    def test_real_short_label_case_excludes_prose_colon_candidates(self):
        d=next(d for d in a.read_json(Path(__file__).parent/'fixtures/real_format_cases.json')['episodes'] if d['number']==113)
        text=a.project(d['transcription'])
        self.assertEqual(search.structure(d['transcription'],text)['raw_labels'],['Alex','Gopi'])

    def test_show_note_headings_are_never_speaker_attributions(self):
        self.ingest();search.rebuild(self.root)
        docs=[json.loads(line) for line in (self.root/'derived/passages.jsonl').read_text().splitlines()]
        notes=[d for d in docs if d['source_type']=='show_notes']
        self.assertTrue(notes)
        self.assertTrue(all(d['speaker_label'] is None for d in notes))
        self.assertTrue(all(d['speaker_accuracy']=='not_applicable' for d in notes))

    def test_stale_index_is_rejected(self):
        self.ingest();search.rebuild(self.root)
        path=self.root/'manifest.json';path.write_text(path.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'stale'):search.query(self.root,'founders')

    def test_query_syntax_is_literal_and_safe(self):
        self.ingest();search.rebuild(self.root)
        self.assertEqual(search.query(self.root,'" OR * NOT ) ---'),search.query(self.root,'OR NOT'))
        self.assertEqual(search.query(self.root,'" * ) ---'),[])


if __name__=='__main__':unittest.main()
