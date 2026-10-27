"""Diagnostic sheets only; does not alter portrait masters or render quote cards."""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from publishing import portrait as p
from publishing import quote_card as q

FONT=q.ROOT/'publishing/templates/quote-card/v1/fonts/SourceSansPro-Regular.otf'


def checker(size):
    im=Image.new('RGBA',size,'#b0b0b0');d=ImageDraw.Draw(im)
    for y in range(0,size[1],16):
        for x in range(0,size[0],16):
            if (x//16+y//16)%2:d.rectangle((x,y,x+15,y+15),fill='#e8e8e8')
    return im


def composite(im,bg):
    bg=bg.convert('RGBA');bg.alpha_composite(im);return bg.convert('RGB')


def sheet(panels,out,cell=(430,560),enlarge=False):
    width,height=cell
    im=Image.new('RGB',(width*len(panels),height+70),'#edf1f4');d=ImageDraw.Draw(im)
    font=ImageFont.truetype(str(FONT),21)
    for i,(title,picture) in enumerate(panels):
        d.text((i*width+12,12),title,font=font,fill='#002436')
        picture=picture.copy()
        if enlarge:
            factor=min(2,(width-16)/picture.width,height/picture.height)
            picture=picture.resize((round(picture.width*factor),round(picture.height*factor)),Image.Resampling.NEAREST)
        else:picture.thumbnail((width-16,height),Image.Resampling.LANCZOS)
        im.paste(picture,(i*width+(width-picture.width)//2,62+(height-picture.height)//2))
    im.save(out)


def review(run,previous_job,out):
    run,out=Path(run),Path(out);m=p.verify(run);out.mkdir(parents=True,exist_ok=True)
    source=p.original(m['source']);master=Image.open(run/'master.png').convert('RGBA')
    # Restore the old cropped mask to source coordinates for fair edge comparison.
    job=q.read(previous_job);recipe=q.read(previous_job)['portrait']['recipe'];import json
    crop=json.loads(recipe)['crop']
    old=Image.new('RGBA',source.size);old.paste(Image.open(q.resolve(job['portrait']['cutout']['path'])),(crop[0],crop[1]))
    spec=q.read(q.SPEC_PATH);bg=q.decoration(spec).resize(tuple(spec['canvas']),Image.Resampling.LANCZOS)
    foreground=master.crop(master.getbbox());scale=min(690/foreground.height,520/foreground.width)
    foreground=foreground.resize((round(foreground.width*scale),round(foreground.height*scale)),Image.Resampling.LANCZOS)
    bg.alpha_composite(foreground,(940-foreground.width,788-foreground.height))
    bg.convert('RGB').save(out/'tsse-composite.png')
    sheet([('Original photograph',source),('Previous polygon cutout',composite(old,checker(source.size))),('New master — review required',composite(master,checker(source.size))),('On actual TSSE decoration',bg.convert('RGB'))],out/'comparison.png')
    colors=[('White','#ffffff'),('Black','#000000'),('Mid-gray','#808080'),('TSSE dark',spec['colors']['background_top']),('TSSE cyan',spec['colors']['disc_top'])]
    panels=[]
    for title,color in colors:
        comp=composite(master,Image.new('RGBA',source.size,color));comp.save(out/(title.lower().replace(' ','-')+'.png'));panels.append((title,comp))
    sheet(panels,out/'backgrounds.png',cell=(330,480))
    bbox=master.getbbox();x0,y0,x1,y1=bbox
    # Generic top 55% of subject bounds, same rule for every guest. No retouching.
    end=min(source.height,round(y0+.55*(y1-y0)))
    hair_box=master.getchannel('A').crop((0,y0,source.width,end)).getbbox()
    hx0,_,hx1,_=hair_box
    box=(max(0,hx0-8),max(0,y0-8),min(source.width,hx1+8),end)
    old_dark=composite(old,Image.new('RGBA',source.size,spec['colors']['background_top']))
    new_dark=composite(master,Image.new('RGBA',source.size,spec['colors']['background_top']))
    for title,im in [('before-edge',old_dark),('after-edge',new_dark),('source-edge',source)]:
        part=im.crop(box);part.resize((part.width*2,part.height*2),Image.Resampling.NEAREST).save(out/(title+'.png'))
    sheet([('Original — hair / ears',source.crop(box)),('Previous — on TSSE dark',old_dark.crop(box)),('New — on TSSE dark',new_dark.crop(box))],out/'edge-comparison.png',cell=(700,650),enlarge=True)
    shoulder=(max(0,x0-8),round(y0+.5*(y1-y0)),min(source.width,x1+8),y1)
    sheet([('Original — clothing edges',source.crop(shoulder)),('Previous — on TSSE dark',old_dark.crop(shoulder)),('New — on TSSE dark',new_dark.crop(shoulder))],out/'shoulder-comparison.png',cell=(650,650),enlarge=True)
    sheet([('Alpha matte',Image.open(run/'alpha-16bit.png').point(lambda x:x/257).convert('L').convert('RGB')),('Color recovery result',Image.open(run/'foreground.png').convert('RGB'))],out/'matte-and-foreground.png')
    p.write(out/'review.json',{'portrait_run':str(run.resolve()),'master_sha256':p.digest(run/'master.png'),'edge_box':list(box),'edge_enlargement':'2x nearest-neighbor in separate edge files; sheets fit panels','background_spec_sha256':p.digest(q.SPEC_PATH),'previous_input_sha256':p.digest(previous_job),'state':'portrait_requires_review','note':'Portrait-only diagnostic composite. No quote-card job changed.'})

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run');parser.add_argument('--previous-job',required=True);parser.add_argument('--out',required=True);a=parser.parse_args();review(a.run,a.previous_job,a.out)
