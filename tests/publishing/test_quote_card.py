"""Offline contract, provenance, geometry and approval regressions.

Synthetic alpha rectangle is a test fixture, never a purported guest portrait.
Vendored Source Sans Pro keeps these checks portable.
"""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw
from publishing import quote_card as q
from publishing import portrait_assets as assets


class QuoteCardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.spec=q.read(q.SPEC_PATH)
        bold=os.environ.get('TSSE_TEST_FONT_BOLD',str(q.ROOT/'publishing/templates/quote-card/v1/fonts/SourceSansPro-Bold.otf'))
        regular=os.environ.get('TSSE_TEST_FONT_REGULAR',str(q.ROOT/'publishing/templates/quote-card/v1/fonts/SourceSansPro-Regular.otf'))
        if not Path(bold).is_file() or not Path(regular).is_file():
            self.skipTest('Supply TSSE_TEST_FONT_BOLD and TSSE_TEST_FONT_REGULAR')
        portrait=self.root/'synthetic-alpha.png';im=Image.new('RGBA',(80,100));ImageDraw.Draw(im).rectangle((20,0,79,99),fill='gray');im.save(portrait)
        record=q.ROOT/'data/episodes/rank4/episode_70.json';transcript=q.ROOT/'data/transcripts/tsse70-cvcs-not-devil-patrick-counterpart_transcript.txt'
        text=transcript.read_text();quote='Capital is a commodity. So you need a real edge.';start=text.index(quote)
        asset={'path':str(portrait),'sha256':q.digest(portrait),'source':'Synthetic test fixture, not a guest photo','status':'approved'}
        self.job={'schema_version':1,'episode':{'number':70,'guest':'Patrick Eggen','record_path':str(record),'record_sha256':q.digest(record)},'quote_number':1,
                  'quote':{'text':quote,'classification':'verbatim','source':{'path':str(transcript),'sha256':q.digest(transcript),'url':q.read(record)['episode_url']+'/transcript','speaker':'Patrick Eggen','start':start,'end':start+len(quote),'excerpt':quote},'editorial_note':'','emphasis':[{'start':quote.index('a real'),'end':len(quote)-1}],'lines':[],'review_status':'approved'},
                  'attribution':{'role':'Co-founder and Partner','company':'Counterpart Ventures'},'portrait':{'original':asset.copy(),'cutout':asset.copy(),'recipe':'test fixture','x':545,'y':110,'width':540},
                  'fonts':{r:{'path':p,'sha256':q.digest(p),'family':'Source Sans Pro','status':'confirmed'} for r,p in [('bold',bold),('regular',regular)]},'profile':'auto'}

        candidate=assets.register(self.root/'portraits','test-01','Patrick Eggen',portrait,portrait,'Synthetic test fixture',kind='supplied_transparent')
        assets.decide(candidate,'approve','Test reviewer','Synthetic test approval')
        self.job['portrait']['approval_candidate']=str(candidate)

    def write_job(self):
        p=self.root/'job.json';p.write_text(json.dumps(self.job));return p

    def render(self,name='run'):
        out=self.root/name;q.render(self.write_job(),out);return out

    def test_verbatim_source_and_filename(self):
        q.validate_input(self.job,self.spec)
        self.assertEqual(q.filename(self.job),'TSSE70 Patrick Eggen quote 1.png')

    def test_schema_rejects_missing_and_unknown_fields(self):
        for mutate in [lambda j:j.pop('portrait'),lambda j:j.update(unknown=True),lambda j:j['episode'].update(number=True)]:
            job=copy.deepcopy(self.job);mutate(job)
            with self.assertRaises(q.ValidationError):q.validate_input(job,self.spec)

    def test_episode_guest_mismatch(self):
        self.job['episode']['guest']='Other Guest'
        with self.assertRaisesRegex(q.ValidationError,'Episode/guest'):q.validate_input(self.job,self.spec)

    def test_wrong_quote_and_wrong_speaker(self):
        self.job['quote']['text']='Invented words.'
        with self.assertRaisesRegex(q.ValidationError,'Verbatim wording'):q.validate_input(self.job,self.spec)
        self.job['quote']['text']=self.job['quote']['source']['excerpt'];self.job['quote']['source']['speaker']='Someone else'
        with self.assertRaisesRegex(q.ValidationError,'speaker'):q.validate_input(self.job,self.spec)

    def test_cannot_relabel_host_passage(self):
        source=self.job['quote']['source'];text=Path(source['path']).read_text();excerpt='You are listening to The Sure Shot Entrepreneur';i=text.index(excerpt)
        source.update(start=i,end=i+len(excerpt),excerpt=excerpt);self.job['quote']['text']=excerpt
        with self.assertRaisesRegex(q.ValidationError,'guest speaker'):q.validate_input(self.job,self.spec)

    def test_lightly_cleaned_requires_explanation(self):
        self.job['quote'].update(classification='lightly_cleaned',text='Capital is a commodity. You need a real edge.',emphasis=[])
        with self.assertRaisesRegex(q.ValidationError,'explanation'):q.validate_input(self.job,self.spec)
        self.job['quote']['editorial_note']='Removed So; source excerpt retained.'
        q.validate_input(self.job,self.spec)

    def test_paraphrase_cannot_be_approved(self):
        self.job['quote'].update(classification='editorial_paraphrase',editorial_note='Editorial summary')
        blockers=q.validate_input(self.job,self.spec)
        self.assertTrue(any('direct-quote design' in b for b in blockers))

    def test_asset_change_and_false_transparency(self):
        a=self.job['portrait']['cutout'];im=Image.new('RGBA',(80,100),'white');im.save(a['path']);a['sha256']=q.digest(a['path']);self.job['portrait']['original']['sha256']=a['sha256']
        with self.assertRaisesRegex(q.ValidationError,'real transparency'):q.validate_input(self.job,self.spec)
        a['sha256']='0'*64
        with self.assertRaisesRegex(q.ValidationError,'content changed'):q.validate_input(self.job,self.spec)

    def test_overflow_and_changed_linebreaks(self):
        self.job['quote']['text']='Oversized quote text. '*80
        with self.assertRaisesRegex(q.ValidationError,'overflows'):q.layout(self.job,self.spec)
        self.job['quote']['text']=self.job['quote']['source']['excerpt'];self.job['quote']['lines']=['Changed words']
        with self.assertRaisesRegex(q.ValidationError,'Line breaks'):q.validate_input(self.job,self.spec)

    def test_bad_emphasis_and_missing_template_layer(self):
        self.job['quote']['emphasis']=[{'start':0,'end':999}]
        with self.assertRaisesRegex(q.ValidationError,'Emphasis'):q.validate_input(self.job,self.spec)
        self.job['quote']['emphasis']=[];self.spec.pop('footer')
        with self.assertRaisesRegex(q.ValidationError,'required element'):q.validate_input(self.job,self.spec)

    def test_renderer_refuses_unapproved_portrait_even_with_approved_labels(self):
        candidate=Path(self.job['portrait']['approval_candidate'])
        review=candidate.parent/'review.json';record=q.read(review)
        record.update(decision='reject',state='rejected');review.write_text(json.dumps(record))
        with self.assertRaisesRegex(q.ValidationError,'human approval'):
            q.validate_input(self.job,self.spec)

    def test_renderer_refuses_different_master_than_approved(self):
        im=Image.new('RGBA',(80,100));ImageDraw.Draw(im).rectangle((22,0,79,99),fill='navy')
        path=self.root/'different.png';im.save(path)
        self.job['portrait']['cutout'].update(path=str(path),sha256=q.digest(path))
        with self.assertRaisesRegex(q.ValidationError,'approved portrait master'):
            q.validate_input(self.job,self.spec)

    def test_font_missing(self):
        self.job['fonts']['bold']['path']=str(self.root/'absent.ttf')
        with self.assertRaisesRegex(q.ValidationError,'missing file'):q.validate_input(self.job,self.spec)

    def test_repeat_render_pixel_and_byte_identity(self):
        a=self.render('a');b=self.render('b');name=q.filename(self.job)
        self.assertEqual(q.digest(a/name),q.digest(b/name));im=Image.open(a/name)
        self.assertEqual(im.size,(1880,1576));self.assertEqual(im.format,'PNG');im.close()
        q.verify_run(a)
        with self.assertRaisesRegex(q.ValidationError,'already exists'):q.render(self.write_job(),a)

    def test_png_tamper_invalidates_review(self):
        out=self.render();p=out/q.filename(self.job);p.write_bytes(p.read_bytes()+b'tampered')
        with self.assertRaisesRegex(q.ValidationError,'image changed'):q.verify_run(out)

    def test_input_tamper_invalidates_review(self):
        out=self.render();p=out/'input.json';j=q.read(p);j['quote_number']=2;p.write_text(json.dumps(j))
        with self.assertRaisesRegex(q.ValidationError,'input changed'):q.verify_run(out)

    def test_provisional_spec_refuses_approval(self):
        provisional=self.root/'provisional.json'
        self.spec.update(status='provisional_reconstruction',unresolved=['Human visual review required'])
        provisional.write_text(json.dumps(self.spec))
        with patch.object(q,'SPEC_PATH',provisional):
            out=self.render();decision=self.root/'decision.json';decision.write_text(json.dumps({'run_id':q.read(out/'manifest.json')['run_id'],'decision':'approved','reviewer':'Test'}))
            with self.assertRaisesRegex(q.ValidationError,'Unresolved'):q.approve(out,decision)

    def test_explicit_approval_after_resolved_spec(self):
        approved=self.root/'spec.json';self.spec.update(status='approved',unresolved=[]);approved.write_text(json.dumps(self.spec))
        with patch.object(q,'SPEC_PATH',approved):
            out=self.render();m=q.read(out/'manifest.json');decision=self.root/'decision.json'
            decision.write_text(json.dumps({'run_id':m['run_id'],'decision':'approved','reviewer':'Test reviewer'}))
            self.assertEqual(q.approve(out,decision)['state'],'approved');self.assertEqual(q.verify_run(out)['state'],'approved')
            with self.assertRaisesRegex(q.ValidationError,'already approved'):q.approve(out,decision)
            approved.write_text(approved.read_text()+' ')
            with self.assertRaisesRegex(q.ValidationError,'changed since rendering'):q.verify_run(out)

    def test_long_quote_uses_same_template(self):
        self.job['quote']['lines']=['A polished pitch by','a VC can tell you','how an investor','describes their value.','Only founders can','tell you whether the','VC actually delivered it.']
        self.job['quote']['text']=' '.join(self.job['quote']['lines'])
        plan=q.layout(self.job,self.spec)
        self.assertEqual(plan['profile'],'long')
        self.assertEqual(len(plan['quote_boxes']),7)
        self.assertLessEqual(max(b[3] for b in plan['quote_boxes']),502)

    def test_paragraph_spacing_preserves_shared_baselines(self):
        self.job['profile']='medium'
        self.job['quote']['lines']=['Capital is a','commodity. So','you need a real','edge.']
        plain=q.layout(self.job,self.spec)
        self.job['quote']['paragraph_starts']=[self.job['quote']['text'].index('you need')]
        plan=q.layout(self.job,self.spec)
        self.assertEqual(plan['baselines'][:2],plain['baselines'][:2])
        self.assertEqual(plan['baselines'][2]-plain['baselines'][2],15)
        self.assertEqual(plan['baselines'][3]-plan['baselines'][2],63)
        self.job['quote']['emphasis']=[]
        self.assertEqual(q.layout(self.job,self.spec),plan)

    def test_paragraph_cannot_split_explicit_line(self):
        self.job['quote']['lines']=['Capital is a','commodity. So','you need a real','edge.']
        self.job['quote']['paragraph_starts']=[self.job['quote']['text'].index('need')]
        with self.assertRaisesRegex(q.ValidationError,'paragraph'):
            q.layout(self.job,self.spec)

    def test_measured_modes_and_fixed_attribution(self):
        short=q.layout(self.job,self.spec)
        self.assertEqual(short['profile'],'short')
        self.assertEqual(short['divider_y'],499)
        self.assertAlmostEqual((short['quote_boxes'][0][1]+short['quote_boxes'][-1][3])/2,(165+470)/2)
        self.job['quote'].update(text="Don’t build what’s possible. Build what matters to the customer.",lines=[])
        medium=q.layout(self.job,self.spec)
        self.assertEqual(medium['profile'],'medium')
        self.assertEqual(medium['divider_y'],short['divider_y'])
        self.assertAlmostEqual(medium['quote_boxes'][0][1],165)
        self.job['quote']['text']='Build what matters.'
        self.job['profile']='long'
        override=q.layout(self.job,self.spec)
        self.assertEqual(override['profile'],'long')
        self.assertEqual(override['divider_y'],516)

    def test_localized_glow_and_footer_color_span(self):
        bg=q.decoration(self.spec)
        # The visible upper-right disc is bright; its left side stays dark.
        bright=bg.getpixel((900*q.SCALE,220*q.SCALE))
        dark=bg.getpixel((530*q.SCALE,400*q.SCALE))
        self.assertGreater(bright[2]-dark[2],70)
        self.assertEqual(self.spec['footer_gradient_region'],[664,788])

    def test_portrait_bottom_cannot_end_above_footer(self):
        p=Path(self.job['portrait']['cutout']['path']);im=Image.new('RGBA',(80,40));ImageDraw.Draw(im).rectangle((20,0,79,39),fill='gray');im.save(p)
        plan=q.layout(self.job,self.spec)
        with self.assertRaisesRegex(q.ValidationError,'bottom ends above'):
            q.draw_card(self.job,self.spec,plan)

    def test_logo_master_replacement_is_rejected(self):
        self.spec['logo']['sha256']='0'*64
        with self.assertRaisesRegex(q.ValidationError,'authentic source'):
            q.validate_input(self.job,self.spec)

    def test_geometry_against_reference_anchors(self):
        # Independent bounds from measured approved references, not a snapshot of code.
        self.assertAlmostEqual(self.spec['rule'][0]/940,278/1370,delta=.002)
        self.assertAlmostEqual(self.spec['rule'][2]/940,727/1370,delta=.002)
        self.assertAlmostEqual(self.spec['footer'][1][1]/788,975/1148,delta=.007)
        self.assertTrue(70<=self.spec['quote']['x']<=75)
        bg=q.decoration(self.spec)
        # Rule must actually be painted, not merely present in JSON.
        rgb=bg.getpixel((300*q.SCALE,95*q.SCALE));self.assertGreater(rgb[1],180);self.assertGreater(rgb[2],180)
        for name,size in [('kapil',(940,788)),('pavel',(1370,1148))]:
            with Image.open(q.ROOT/f'publishing/templates/quote-card/v1/assets/reference-{name}.png') as ref:
                self.assertEqual(ref.size,size)
                self.assertAlmostEqual(ref.width/ref.height,940/788,delta=.001)


if __name__=='__main__':unittest.main()
