"""Build a clearly labelled side-by-side review sheet from two verified runs."""
import argparse
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from publishing.quote_card import verify_run,read,resolve


def review_pair(left,right,out):
    runs=[Path(left),Path(right)];sheet=Image.new('RGB',(1880,930),'#ecf0f3');draw=ImageDraw.Draw(sheet)
    job=read(runs[0]/'input.json');font=ImageFont.truetype(str(resolve(job['fonts']['bold']['path'])),24)
    small=ImageFont.truetype(str(resolve(job['fonts']['regular']['path'])),19)
    for i,run in enumerate(runs):
        m=verify_run(run);j=read(run/'input.json')
        draw.text((i*940+24,15),j['episode']['guest']+' — UNAPPROVED REVIEW',font=font,fill='#002436')
        draw.text((i*940+24,49),'Quote classification: '+j['quote']['classification'],font=small,fill='#503300')
        with Image.open(run/m['output']) as im:sheet.paste(im.resize((940,788),Image.Resampling.LANCZOS),(i*940,82))
        draw.text((i*940+24,886),'Portrait master approved / complete card awaits visual approval' if 'approval_candidate' in j['portrait'] else 'Source Sans Pro calibration / masks / decoration await approval',font=small,fill='#503300')
    Path(out).parent.mkdir(parents=True,exist_ok=True);sheet.save(out)
    return Path(out)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('left');p.add_argument('right');p.add_argument('--out',required=True);a=p.parse_args();print(review_pair(a.left,a.right,a.out))
