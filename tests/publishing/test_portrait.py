"""Structural/matting regressions, not a claim of aesthetic approval."""
import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from publishing import portrait as p


class PortraitTests(unittest.TestCase):
    def setUp(self):
        self.c=p.read(p.CONFIG)
        y,x=np.mgrid[:64,:64]
        self.alpha=np.clip((20-np.sqrt((x-32)**2+(y-30)**2))/4,0,1)
        self.fg=np.zeros((64,64,3))+[.12,.22,.32]
        self.rgb=self.fg*self.alpha[:,:,None]+1-self.alpha[:,:,None]

    def test_trimap_expands_unknown_without_destroying_foreground(self):
        tri,r=p.trimap_from_probability(self.alpha,self.c)
        self.assertEqual(tri[30,32],1)
        self.assertEqual(tri[0,0],0)
        self.assertGreater((tri==.5).sum(),((self.alpha>0)&(self.alpha<1)).sum())
        self.assertEqual(r,2)

    def test_invalid_seeds_fail_instead_of_silent_rectangle(self):
        for value in [0,1]:
            with self.assertRaisesRegex(ValueError,'portrait_requires_review'):
                p.trimap_from_probability(np.full((64,64),value),self.c)

    def test_foreground_recovery_reduces_known_white_fringe(self):
        recovered=p.recover_foreground(self.rgb,self.alpha,self.c)
        edge=(self.alpha>.1)&(self.alpha<.9)
        before=np.mean(abs(self.rgb[edge]-self.fg[edge]))
        after=np.mean(abs(recovered[edge]-self.fg[edge]))
        self.assertLess(after,before*.5)
        np.testing.assert_array_equal(recovered[self.alpha==1],self.rgb[self.alpha==1])

    def test_native_dimensions_soft_alpha_and_no_rectangle(self):
        master=p.rgba_image(self.fg,self.alpha)
        report=p.inspect_master(master,(64,64),self.c)
        self.assertEqual(report['state'],'portrait_requires_review')
        self.assertGreater(report['checks']['partial_alpha_pixels'],0)
        self.assertEqual(report['checks']['corners']['top_left'],0)
        self.assertIn('low_resolution_source',report['warnings'])
        self.assertNotIn('implausible_subject_area',report['warnings'])
        with self.assertRaisesRegex(ValueError,'original dimensions'):
            p.inspect_master(master,(128,128),self.c)

    def test_corner_occupied_is_flagged_not_erased(self):
        alpha=self.alpha.copy();alpha[-1,-1]=1
        master=p.rgba_image(self.fg,alpha)
        report=p.inspect_master(master,(64,64),self.c)
        self.assertEqual(master.getpixel((63,63))[3],255)
        self.assertIn('subject_or_background_at_image_corner_review_source',report['warnings'])

    def test_opaque_rectangle_is_flagged(self):
        master=Image.new('RGBA',(64,64),'white')
        report=p.inspect_master(master,(64,64),self.c)
        self.assertIn('implausible_subject_area',report['warnings'])
        self.assertIn('no_partial_alpha_boundary',report['warnings'])

    def test_alpha_matting_repeatability(self):
        a,f,_,_=p.matte(self.rgb,self.alpha,self.c)
        b,g,_,_=p.matte(self.rgb,self.alpha,self.c)
        np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(f,g)
        self.assertLess(np.mean(abs(a-self.alpha)),.04)

    def test_input_cutout_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cutout.png';p.rgba_image(self.fg,self.alpha).save(path)
            with self.assertRaisesRegex(ValueError,'authentic opaque original'):p.original(path)

    def test_export_border_alpha_is_accepted_without_rgb_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'original.png'
            im=Image.new('RGBA',(16,16),(37,49,61,255))
            for y in range(16):im.putpixel((15,y),(37,49,61,128))
            im.save(path)
            loaded=p.original(path)
            self.assertEqual(loaded.size,(16,16))
            self.assertEqual(loaded.getpixel((15,3)),(37,49,61))

    def test_artifact_tampering_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);asset=path/'master.png';p.rgba_image(self.fg,self.alpha).save(asset)
            p.write(path/'manifest.json',{'dependencies':{},'artifacts':{'master.png':p.digest(asset)},'runtime':p.runtime()})
            p.verify(path)
            asset.write_bytes(asset.read_bytes()+b'changed')
            with self.assertRaisesRegex(ValueError,'artifact changed'):p.verify(path)

if __name__=='__main__':unittest.main()
