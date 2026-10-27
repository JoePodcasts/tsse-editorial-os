"""Prepare local review examples. Never approves assets; originals remain untouched.

Run from repository root. Input paths are explicit CLI parameters, not machine defaults.
Pavel transcript extraction uses a supplied DOCX until its website passage is available.
"""
import argparse
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from publishing.quote_card import ROOT, digest

LOCAL=ROOT/'data/publishing/local'
PAVEL_GRAY_MASK=[(0,400),(7,383),(27,373),(29,342),(34,312),(54,290),(83,275),(115,263),(139,253),(140,237),(132,215),(128,188),(128,161),(130,131),(137,107),(153,86),(176,72),(200,62),(223,64),(244,75),(258,93),(268,116),(273,142),(273,170),(279,184),(277,208),(268,225),(265,246),(270,261),(305,275),(334,289),(357,309),(369,338),(377,371),(380,400)]
PATRICK_MASK=[(62,1064),(48,985),(50,886),(47,804),(57,699),(58,636),(71,590),(108,557),(177,520),(252,491),(309,469),(288,456),(274,438),(279,415),(269,389),(273,352),(274,317),(281,281),(284,248),(300,218),(312,184),(329,157),(354,125),(385,100),(414,75),(444,58),(479,47),(518,48),(553,53),(584,70),(600,94),(617,114),(631,144),(641,171),(646,207),(657,239),(661,276),(670,307),(668,343),(675,374),(660,408),(651,437),(675,453),(643,473),(603,485),(578,487),(582,508),(644,541),(703,573),(749,602),(777,659),(796,711),(811,810),(821,902),(843,1006),(843,1064)]
PATRICK_URL='https://www.counterpart.vc/our-team/patrick-eggen'
PATRICK_IMAGE='https://cdn.prod.website-files.com/67bf5e069915beed9f1078a5/67c0c8522c27e60a2082cd68_092324ComePlumCounterpartVC-9664%20copy%20(1).png'


def rel(p):
    return str(p.relative_to(ROOT))


def asset(p, source):
    return {'path':rel(p),'sha256':digest(p),'source':source,'status':'candidate'}


def cutout(name, points, expected):
    im=Image.open(LOCAL/(f'{name}-original.jpeg' if name=='pavel' else f'{name}-original.png')).convert('RGBA')
    if im.size!=expected:
        raise ValueError(f'{name}: mask is specific to {expected}; supplied image is {im.size}. Prepare a new reviewed mask.')
    mask=Image.new('L',im.size);ImageDraw.Draw(mask).polygon(points,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(1.1));im.putalpha(mask);bounds=mask.getbbox()
    im.crop(bounds).save(LOCAL/f'{name}-cutout.png')
    return json.dumps({'method':'manual_polygon_alpha','points':points,'feather_px':1.1,'crop':bounds,'status':'provisional_edge_review_required'},separators=(',',':'))


def prepare(pavel_photo, pavel_docx, patrick_photo, bold, regular):
    LOCAL.mkdir(parents=True,exist_ok=True)
    for src,name in [(pavel_photo,'pavel-original.jpeg'),(patrick_photo,'patrick-original.png'),(pavel_docx,'pavel-transcript.docx')]:
        target=LOCAL/name
        if Path(src).resolve()!=target.resolve(): shutil.copyfile(src,target)
    with zipfile.ZipFile(pavel_docx) as z:
        root=ET.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text='\n\n'.join(''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in root.findall('.//w:p',ns))
    (LOCAL/'pavel-transcript.txt').write_text(text)
    (LOCAL/'pavel-episode.json').write_text(json.dumps({'episode_number':196,'guest_name':'Pavel Prata','episode_url':'','status':'provisional_from_supplied_reference_filename'},indent=2))
    fonts={role:{'path':str(Path(path).resolve()),'sha256':digest(path),'family':ImageFont.truetype(str(path),24).getname()[0],'status':'confirmed'} for role,path in [('bold',bold),('regular',regular)]}
    for name,guest,number,record,transcript,quote,classification,source_start,source_end,lines,position in [
        ('pavel','Pavel Prata',196,LOCAL/'pavel-episode.json',LOCAL/'pavel-transcript.txt',
         'A polished pitch by a VC can tell you how an investor describes their value. Only founders can tell you whether the VC actually delivered it.',
         'editorial_paraphrase','And in many cases,','[00:19:55]',
         ['A polished pitch by','a VC can tell you','how an investor','describes their value.','Only founders can','tell you whether the','VC actually delivered it.'],[405,117,700]),
        ('patrick','Patrick Eggen',70,ROOT/'data/episodes/rank4/episode_70.json',ROOT/'data/transcripts/tsse70-cvcs-not-devil-patrick-counterpart_transcript.txt',
         'Capital is a commodity. So you need a real edge.', 'verbatim','Capital is a commodity.',' So you need a real edge.',[],[475,103,590])]:
        transcript_text=transcript.read_text();start=transcript_text.index(source_start)
        end=transcript_text.index(source_end,start)+(len(source_end) if name=='patrick' else 0)
        if name=='pavel':
            while transcript_text[end-1].isspace():end-=1
        phrase='Only founders can tell you' if name=='pavel' else 'a real edge'
        highlight=quote.index(phrase)
        recipe=cutout(name,PAVEL_GRAY_MASK if name=='pavel' else PATRICK_MASK,(400,400) if name=='pavel' else (843,1064))
        provenance=str(Path(pavel_photo).resolve()) if name=='pavel' else PATRICK_URL+' | image: '+PATRICK_IMAGE
        job={'schema_version':1,'episode':{'number':number,'guest':guest,'record_path':rel(record),'record_sha256':digest(record)},'quote_number':1,
             'quote':{'text':quote,'classification':classification,'source':{'path':rel(transcript),'sha256':digest(transcript),'url':'' if name=='pavel' else json.loads(record.read_text())['episode_url']+'/transcript','speaker':guest,'start':start,'end':end,'excerpt':transcript_text[start:end]},'editorial_note':'Reference wording is a paraphrase of the passage; cannot approve as a direct quote.' if name=='pavel' else '', 'emphasis':[{'start':highlight,'end':highlight+len(phrase)}],'lines':lines,'paragraph_starts':[quote.index('Only founders')] if name=='pavel' else [],'review_status':'candidate'},
             'attribution':{'role':'Founder' if name=='pavel' else 'Co-founder and Partner','company':'Murph Capital' if name=='pavel' else 'Counterpart Ventures'},
             'portrait':{'original':asset(LOCAL/(f'{name}-original.jpeg' if name=='pavel' else f'{name}-original.png'),provenance),'cutout':asset(LOCAL/f'{name}-cutout.png','Derived from hashed original; see recipe'),'recipe':recipe,'x':position[0],'y':position[1],'width':position[2]},'fonts':fonts,'profile':'long' if name=='pavel' else 'auto'}
        (LOCAL/f'{name}.json').write_text(json.dumps(job,indent=2,ensure_ascii=False)+'\n')
    (LOCAL/'source-receipt.json').write_text(json.dumps({'pavel_docx':{'source':str(Path(pavel_docx).resolve()),'sha256':digest(pavel_docx),'extraction':'word/document.xml paragraph text; website correspondence not verified'},'patrick_portrait':{'page':PATRICK_URL,'image_url':PATRICK_IMAGE,'sha256':digest(LOCAL/'patrick-original.png'),'status':'user_supplied_official_source; edge mask pending review'}},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['pavel-photo','pavel-docx','patrick-photo']:p.add_argument('--'+key,required=True)
    for role,weight in [('bold','Semibold'),('regular','Regular')]:p.add_argument('--'+role,default=str(ROOT/f'publishing/templates/quote-card/v1/fonts/SourceSansPro-{weight}.otf'))
    a=p.parse_args();prepare(a.pavel_photo,a.pavel_docx,a.patrick_photo,a.bold,a.regular)
