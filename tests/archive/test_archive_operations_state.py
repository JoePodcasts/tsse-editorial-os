"""Successful-state artifact restoration and timezone-aware scheduling."""
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

import archive_operations as ops
import archive_sync as a


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'archive';self.root.mkdir()
        (self.root/'catalogue.jsonl').write_text('{}\n');(self.root/'manifest.json').write_text('{}')
        self.status={'status':'success','last_successful_sync_at':'2026-01-06T14:30:00+00:00',
                     'archive_fingerprint':ops.state_fingerprint(self.root),'published_episodes':1,
                     'changes_detected':False,'changes':dict(new=0,changed=0,unchanged=1,not_seen=0)}
    def gh(self,args,**kwargs):
        if 'list' in args:
            self.assertIn('--status',args);self.assertEqual(args[args.index('--status')+1],'success')
            self.assertIn('--branch',args)
            return SimpleNamespace(stdout=json.dumps([{'databaseId':42}]))
        target=Path(args[args.index('--dir')+1]);(target/ops.STATUS).write_bytes(a.encoded(self.status))
        (target/'ingestion_state.json').write_text('{}')
        return SimpleNamespace(stdout='')
    def test_successful_artifact_restored_for_same_archive(self):
        with patch.object(subprocess,'run',side_effect=self.gh):result=ops.restore_status(self.root,'owner/repo')
        self.assertTrue(result['restored']);self.assertEqual(a.read_json(self.root/ops.STATUS),self.status)
    def test_failed_artifact_not_accepted(self):
        self.status['status']='failed'
        with patch.object(subprocess,'run',side_effect=self.gh):result=ops.restore_status(self.root,'owner/repo')
        self.assertFalse(result['restored']);self.assertFalse((self.root/ops.STATUS).exists())
    def test_other_archive_artifact_not_accepted(self):
        self.status['archive_fingerprint']='different'
        with patch.object(subprocess,'run',side_effect=self.gh):result=ops.restore_status(self.root,'owner/repo')
        self.assertFalse(result['restored'])
    def test_older_artifact_cannot_replace_newer_local_success(self):
        newer=dict(self.status,last_successful_sync_at='2026-02-03T14:30:00+00:00')
        (self.root/ops.STATUS).write_bytes(a.encoded(newer))
        with patch.object(subprocess,'run',side_effect=self.gh):result=ops.restore_status(self.root,'owner/repo')
        self.assertFalse(result['restored']);self.assertEqual(a.read_json(self.root/ops.STATUS),newer)
    def test_expired_artifact_preserves_last_success(self):
        (self.root/ops.STATUS).write_bytes(a.encoded(self.status));before=(self.root/ops.STATUS).read_bytes()
        def gh(args,**kwargs):
            if 'list' in args:return SimpleNamespace(stdout='[{"databaseId":42}]')
            raise subprocess.CalledProcessError(1,args)
        with patch.object(subprocess,'run',side_effect=gh):result=ops.restore_status(self.root,'owner/repo')
        self.assertFalse(result['restored']);self.assertEqual((self.root/ops.STATUS).read_bytes(),before)
    def test_timezone_schedule_including_dst_transitions(self):
        workflow=(Path(__file__).resolve().parents[2]/'.github/workflows/archive-sync.yml').read_text()
        self.assertIn("cron: '30 6 * * 2'",workflow);self.assertIn('timezone: America/Los_Angeles',workflow)
        self.assertIn('workflow_dispatch:',workflow)
        for date,hour in [('2026-01-06',14),('2026-03-03',14),('2026-03-10',13),('2026-10-27',13),('2026-11-03',14)]:
            local=datetime.fromisoformat(date+'T06:30:00').replace(tzinfo=ZoneInfo('America/Los_Angeles'))
            self.assertEqual(local.weekday(),1);self.assertEqual(local.astimezone(timezone.utc).hour,hour)
    def test_workflow_persistence_follows_validation_and_artifact_follows_push(self):
        workflow=(Path(__file__).resolve().parents[2]/'.github/workflows/archive-sync.yml').read_text()
        self.assertLess(workflow.index('archive_operations.py sync'),workflow.index('Regression tests'))
        self.assertLess(workflow.index('Regression tests'),workflow.index('archive_operations.py persist'))
        self.assertLess(workflow.index('archive_operations.py persist'),workflow.index('uses: actions/upload-artifact'))
        self.assertNotIn('pull_request:',workflow)
        self.assertNotIn('git add .',workflow)

if __name__=='__main__':unittest.main()
