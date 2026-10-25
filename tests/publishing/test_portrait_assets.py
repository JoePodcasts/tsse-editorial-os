import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from publishing import portrait_assets as a
from publishing import quote_card as q

class PortraitAssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.master=self.root/'supplied.png'
        im=Image.new('RGBA',(80,100));ImageDraw.Draw(im).ellipse((10,5,70,95),fill='gray');im.save(self.master)

    def register(self,name='candidate-01',parent=None):
        return a.register(self.root/'library',name,'Guest',self.master,self.master,'Official supplied transparent portrait',parent=parent)

    def test_supplied_master_requires_human_approval(self):
        candidate=self.register();record=a.verify_candidate(candidate)
        self.assertEqual(record['origin_kind'],'supplied_transparent')
        self.assertEqual(record['state'],'portrait_requires_review')
        self.assertIsNone(record['processing_run'])
        with self.assertRaises(OSError):a.approved(candidate)
        a.decide(candidate,'approve','Editor','Explicit test authorization')
        self.assertEqual(a.approved(candidate,'Guest')['candidate_id'],'candidate-01')
        with self.assertRaisesRegex(ValueError,'guest mismatch'):a.approved(candidate,'Different guest')

    def test_revision_and_rejection_preserve_candidates(self):
        first=self.register();a.decide(first,'try_another_approach','Editor','Test feedback')
        second=self.register('candidate-02',first);a.decide(second,'reject','Editor','Unsuitable test')
        self.assertEqual(a.read(second)['parent_candidate'],str(first))
        self.assertTrue((first.parent/'master.png').exists())
        with self.assertRaisesRegex(ValueError,'human approval'):a.approved(first)
        with self.assertRaises(FileExistsError):self.register()
        with self.assertRaises(FileExistsError):a.decide(first,'approve','Editor','New decision must use new candidate')

    def test_select_current_keeps_previous_approval(self):
        first=self.register();a.decide(first,'approve','Editor','First authorization');a.select_current(first)
        second=self.register('candidate-02',first);a.decide(second,'approve','Editor','Second authorization');a.select_current(second)
        self.assertEqual(a.read(second.parent.parent/'current.json')['Guest']['candidate'],str(second))
        a.approved(first)

    def test_master_and_decision_tampering_rejected(self):
        first=self.register();a.decide(first,'approve','Editor','Authorization')
        master=first.parent/'master.png';master.write_bytes(master.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'content changed'):a.approved(first)

    def test_plain_opaque_rectangle_cannot_register(self):
        Image.new('RGBA',(80,100),'white').save(self.master)
        with self.assertRaisesRegex(ValueError,'transparent background'):self.register()
