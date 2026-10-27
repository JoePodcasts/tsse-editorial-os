"""Production lifecycle simulations; synthetic episodes never enter real archive/."""
import copy
import csv
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import archive_sync as a
import archive_library as lib
import archive_operations as ops
import archive_search as search
from archive_files import ExportLibrary
from archive_web import ArchiveApp
from test_archive_sync import episode, detail, PODCAST


class Remote:
    def __init__(self, count=195):
        self.items=[episode(n,title=f'Fixture episode {n}') for n in range(1,count+1)]
        self.details={i['id']:detail(i,transcription=f'<p>[00:01:23] Fixture Speaker: Synthetic archive fixture token{ i["number"] }.</p>') for i in self.items}
        self.requests=0; self.detail_requests=0
    def __call__(self,url,**kwargs):
        self.requests+=1
        if url.endswith('/sites/search'): return {'podcast':{'id':PODCAST}}
        if '/podcasts/' in url:
            offset=int(parse_qs(urlparse(url).query).get('offset',['0'])[0])
            more=offset+100<len(self.items)
            return {'collection':self.items[offset:offset+100], 'pages':{
                'total':(len(self.items)+99)//100, 'current':offset//100+1,
                'next':{'href':f'{a.SIMPLECAST_API}/podcasts/{PODCAST}/episodes?offset={offset+100}'} if more else None}}
        self.detail_requests+=1
        result=self.details[url.rsplit('/',1)[-1]]
        if isinstance(result,BaseException): raise result
        return result


class ProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_tmp=tempfile.TemporaryDirectory(); cls.base=Path(cls.base_tmp.name)
        cls.repo=cls.base/'repo';cls.repo.mkdir();cls.baseline=cls.base/'archive'
        cls.initial=ops.sync(cls.baseline,cls.repo,fetch=Remote(),delay=0)
    @classmethod
    def tearDownClass(cls): cls.base_tmp.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'archive';shutil.copytree(self.baseline,self.root)
        self.remote=Remote()
    def sync(self,**kwargs): return ops.sync(self.root,self.repo,fetch=self.remote,delay=0,**kwargs)
    def bytes(self): return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
    def new(self,pending=False):
        item=episode(196,title='Isolated next episode fixture');self.remote.items.append(item)
        self.remote.details[item['id']]=detail(item,transcription=None if pending else '<p>[00:02:03] Fixture Speaker: nextunique196 searchable fixture.</p>')
        return item
    def test_no_change_week_preserves_files_and_refreshes_success(self):
        before=self.bytes();stamp=ops.freshness(self.root)['last_successful_sync_at']
        mtimes={p.name:p.stat().st_mtime_ns for p in (self.root/'exports/episodes').glob('*.md')}
        report=self.sync();after=self.bytes()
        self.assertEqual(report['changes'],dict(new=0,changed=0,unchanged=195,not_seen=0))
        self.assertEqual(self.remote.detail_requests,0)
        self.assertEqual(report['http_requests'],3)
        self.assertTrue(report['validation']['index_reused'])
        self.assertNotEqual(stamp,ops.freshness(self.root)['last_successful_sync_at'])
        self.assertEqual({p.name:p.stat().st_mtime_ns for p in (self.root/'exports/episodes').glob('*.md')},mtimes)
        self.assertEqual({k:v for k,v in before.items() if k not in ops.OPERATIONAL},
                         {k:v for k,v in after.items() if k not in ops.OPERATIONAL})
    def test_episode196_full_frontend_exports_index_zip_and_status(self):
        item=self.new();stamp=ops.freshness(self.root)['last_successful_sync_at'];report=self.sync()
        self.assertEqual(report['changes'],dict(new=1,changed=0,unchanged=195,not_seen=0))
        app=ArchiveApp(self.root)
        self.assertEqual(app.api('/api/archive',{})['episodes'],196)
        self.assertEqual(app.api('/api/archive',{})['transcript'],196)
        self.assertEqual(app.api('/api/files',{})['markdown_files'],196)
        self.assertEqual(app.api('/api/files',{})['csv_rows'],196)
        self.assertEqual(app.api('/api/episodes',{})['total'],196)
        self.assertTrue(app.api('/api/episodes/196',{})['file'])
        self.assertIn('nextunique196',app.api('/api/episodes/196/file',{})['text'])
        self.assertTrue(search.query(self.root,'nextunique196',episode=196))
        self.assertEqual(ops.freshness(self.root)['published_episodes'],196)
        self.assertNotEqual(ops.freshness(self.root)['last_successful_sync_at'],stamp)
        with __import__('zipfile').ZipFile(self.root/'exports/markdown-library.zip') as z:
            self.assertEqual(len(z.namelist()),196);self.assertIn('episodes/'+item['id']+'.md',z.namelist())
    def test_episode196_pending_then_retries_and_becomes_searchable(self):
        item=self.new(pending=True);report=self.sync()
        self.assertEqual(report['validation']['coverage']['episodes'],196)
        self.assertEqual(report['validation']['coverage']['transcript'],195)
        self.assertEqual(report['pending_sources'][0]['missing'],['transcript'])
        self.assertIn('Availability: unavailable_at_source',ArchiveApp(self.root).api('/api/episodes/196/file',{})['text'])
        self.remote.details[item['id']]['transcription']='<p>[00:00:01] Fixture Speaker: readyunique196.</p>'
        self.remote.detail_requests=0
        report=self.sync()
        self.assertEqual(self.remote.detail_requests,1)
        self.assertEqual(report['changes']['changed'],1)
        self.assertEqual(report['validation']['coverage']['transcript'],196)
        self.assertTrue(search.query(self.root,'readyunique196'))
    def test_historical_correction_versions_and_unchanged_neighbors(self):
        before=(self.root/'exports/episodes'/f'{self.remote.items[1]["id"]}.md').read_bytes()
        item=self.remote.items[0];item['title']='Corrected title';item['updated_at']='2026-10-26T01:00:00+00:00'
        self.remote.details[item['id']]=detail(item,transcription='<p>[00:04:56] Fixture Speaker: correctedunique.</p>')
        report=self.sync()
        self.assertEqual(report['changes']['changed'],1)
        self.assertEqual(report['changes']['unchanged'],194)
        entry=a.read_json(self.root/'manifest.json')['simplecast:'+item['id']]['transcript']
        self.assertEqual(len(entry['previous_versions']),1)
        self.assertTrue(search.query(self.root,'correctedunique'))
        self.assertEqual(before,(self.root/'exports/episodes'/f'{self.remote.items[1]["id"]}.md').read_bytes())
    def test_source_only_correction_detected_by_bounded_refresh(self):
        item=self.remote.items[0]
        self.remote.details[item['id']]['transcription']='<p>Silentcorrection without catalogue revision.</p>'
        report=self.sync(refresh_limit=1,min_age_days=0)
        self.assertEqual(self.remote.detail_requests,1)
        self.assertEqual(report['changes']['changed'],1)
        self.assertTrue(search.query(self.root,'Silentcorrection'))
    def assert_failure_unchanged(self, callback):
        before=self.bytes()
        with self.assertRaises((ValueError,URLError,OSError,RuntimeError)): callback()
        self.assertEqual(before,self.bytes())
        self.assertTrue((self.root.parent/'.archive-production-failure.json').exists())
    def test_catalogue_unavailable_retains_last_good(self):
        self.assert_failure_unchanged(lambda:ops.sync(self.root,self.repo,fetch=lambda *a,**k: (_ for _ in ()).throw(URLError('offline'))))
    def test_malformed_catalogue_retains_last_good(self):
        original=self.remote
        def fetch(url,**kwargs):
            return {'collection':'bad'} if '/podcasts/' in url else original(url,**kwargs)
        self.assert_failure_unchanged(lambda:ops.sync(self.root,self.repo,fetch=fetch))
    def test_detail_transport_failure_aborts_new_episode(self):
        item=self.new();self.remote.details[item['id']]=URLError('source unavailable')
        self.assert_failure_unchanged(self.sync)
    def test_missing_transcript_field_is_malformed_not_pending(self):
        item=self.new();del self.remote.details[item['id']]['transcription']
        self.assert_failure_unchanged(self.sync)
    def test_malformed_transcript_type_aborts(self):
        item=self.new();self.remote.details[item['id']]['transcription']={'bad':'payload'}
        self.assert_failure_unchanged(self.sync)
    def test_export_failure_rolls_back(self):
        self.new()
        with patch.object(a,'markdown',side_effect=OSError('export failure')):self.assert_failure_unchanged(self.sync)
    def test_validation_failure_rolls_back(self):
        self.new()
        with patch.object(ops,'validate_complete',side_effect=ValueError('failed validation')):self.assert_failure_unchanged(self.sync)
    def test_index_failure_rolls_back(self):
        self.new()
        with patch.object(search,'rebuild',side_effect=ValueError('index failure')):self.assert_failure_unchanged(self.sync)
    def test_zip_failure_rolls_back(self):
        self.new()
        with patch.object(ExportLibrary,'zip_bytes',side_effect=ValueError('zip failure')):self.assert_failure_unchanged(self.sync)
    def test_promotion_failure_rolls_back(self):
        self.new();original=Path.rename
        def rename(path,target):
            if path.name=='candidate' and Path(target).resolve()==self.root.resolve():raise OSError('promotion failure')
            return original(path,target)
        with patch.object(Path,'rename',rename):self.assert_failure_unchanged(self.sync)
    def test_status_only_accepts_matching_success(self):
        self.assertIsNotNone(ops.freshness(self.root))
        status=a.read_json(self.root/ops.STATUS);status['status']='failed';lib.atomic_json(self.root/ops.STATUS,status)
        self.assertIsNone(ops.freshness(self.root))
        status['status']='success';status['archive_fingerprint']='bad';lib.atomic_json(self.root/ops.STATUS,status)
        self.assertIsNone(ops.freshness(self.root))
    def test_fresh_checkout_rebuilds_ignored_search_and_zip(self):
        before=(self.root/ops.STATUS).read_bytes()
        for name in ('search/archive.sqlite3', 'derived/passages.jsonl',
                     'derived/search-documents.jsonl', 'exports/markdown-library.zip',
                     'reports/search-index.json', 'reports/library-zip.json'):
            (self.root/name).unlink()
        result=ops.validate_complete(self.root)
        self.assertEqual(result['published_episodes'],195)
        self.assertEqual(result['zip']['entries'],195)
        self.assertTrue(search.query(self.root,'token195'))
        self.assertTrue((self.root/'derived/passages.jsonl').is_file())
        self.assertTrue((self.root/'derived/search-documents.jsonl').is_file())
        self.assertEqual((self.root/ops.STATUS).read_bytes(),before)
    def test_non_archive_target_rejected(self):
        with self.assertRaises(ValueError):ops.sync(self.repo,self.repo,fetch=self.remote)
    def test_git_no_change_week_has_no_commit(self):
        repository=self.root.parent
        subprocess.run(['git','init','-b','main',str(repository)],check=True,capture_output=True)
        (self.root/'.gitignore').write_text('\n'.join('/'+x for x in ops.OPERATIONAL)+'\n')
        subprocess.run(['git','-C',str(repository),'add','archive'],check=True,capture_output=True)
        ops.run_git(repository,'-c','user.name=Fixture','-c','user.email=fixture@example.test','commit','-m','initial')
        before=ops.run_git(repository,'rev-parse','HEAD');self.sync()
        result=ops.persist(repository)
        self.assertFalse(result['commit_created']);self.assertEqual(before,ops.run_git(repository,'rev-parse','HEAD'))
    def test_git_push_failure_is_not_reported_success(self):
        with patch.object(ops,'freshness',return_value={'status':'success'}),patch.object(ops,'validate_complete'):
            with patch.object(ops,'run_git',side_effect=['','main','', 'archive/catalogue.jsonl','', subprocess.CalledProcessError(1,['git','push'])]):
                with self.assertRaises(subprocess.CalledProcessError):ops.persist(self.root.parent,push=True)
    def test_new_episode_commits_only_allowed_content_and_pushes(self):
        repository=self.root.parent
        remote=repository/'remote.git'
        subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
        subprocess.run(['git','init','-b','main',str(repository)],check=True,capture_output=True)
        shutil.copyfile(a.ROOT/'archive/.gitignore',self.root/'.gitignore')
        ops.run_git(repository,'add','archive')
        ops.run_git(repository,'-c','user.name=Fixture','-c','user.email=fixture@example.test','commit','-m','initial')
        ops.run_git(repository,'remote','add','origin',str(remote))
        (repository/'unrelated.txt').write_text('Must not be committed')
        self.new();self.sync()
        result=ops.persist(repository,push=True)
        self.assertTrue(result['commit_created'])
        self.assertEqual(result['commit'],ops.run_git(remote,'rev-parse','refs/heads/main'))
        paths=ops.run_git(repository,'diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines()
        self.assertIn('archive/catalogue.jsonl',paths)
        self.assertTrue(all(any(path=='archive/'+allowed or path.startswith('archive/'+allowed+'/')
                               for allowed in ops.CONTENT_PATHS) for path in paths))
        self.assertNotIn('archive/'+ops.STATUS,paths)
        self.assertTrue((repository/'unrelated.txt').is_file())
    def test_git_commit_failure_is_not_reported_success(self):
        with patch.object(ops,'freshness',return_value={'status':'success'}),patch.object(ops,'validate_complete'):
            with patch.object(ops,'run_git',side_effect=['','main','', 'archive/catalogue.jsonl', subprocess.CalledProcessError(1,['git','commit'])]):
                with self.assertRaises(subprocess.CalledProcessError):ops.persist(self.root.parent,push=True)


if __name__=='__main__':unittest.main()
