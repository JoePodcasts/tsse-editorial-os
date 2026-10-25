"""Deterministic, local TSSE quote cards. Never uploads or implicitly approves."""
import argparse
import difflib
import hashlib
import html
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, features, __version__ as PIL_VERSION

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'publishing/templates/quote-card/v1/spec.json'
SCHEMA_PATH = ROOT / 'schemas/publishing/quote-card.schema.json'
SCALE = 4  # All layout and rasterization at one fixed supersampling scale.


class ValidationError(ValueError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def value_hash(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def resolve(path):
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def normalized(text):
    # No punctuation edits or word changes are allowed in a verbatim comparison.
    return ' '.join(text.split())


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def check_schema(value, schema, label='input'):
    """Validate the exact JSON Schema subset used by our closed input contract.

    Unknown validation keywords fail, rather than silently ignoring a constraint.
    The checked-in schema is also consumable by standard JSON Schema validators.
    """
    known = {'$schema', 'title', 'type', 'properties', 'required', 'additionalProperties',
             'items', 'enum', 'const', 'minimum', 'minLength', 'pattern'}
    require(not set(schema) - known, f'{label}: unsupported schema constraint')
    typ = schema.get('type')
    tests = {'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list),
             'string': lambda v: isinstance(v, str), 'integer': lambda v: type(v) is int,
             'number': lambda v: type(v) in (int, float)}
    if typ:
        require(typ in tests and tests[typ](value), f'{label}: expected {typ}')
    if 'const' in schema:
        require(type(value) is type(schema['const']) and value == schema['const'], f'{label}: unsupported version')
    if 'enum' in schema:
        require(value in schema['enum'], f'{label}: must be one of {schema["enum"]}')
    if 'minimum' in schema:
        require(value >= schema['minimum'], f'{label}: below minimum')
    if 'minLength' in schema:
        require(len(value.strip()) >= schema['minLength'], f'{label}: cannot be blank')
    if 'pattern' in schema:
        require(re.fullmatch(schema['pattern'], value) is not None, f'{label}: invalid format')
    if typ == 'object':
        for key in schema.get('required', []):
            require(key in value, f'{label}.{key}: required')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False:
            require(not set(value) - set(props), f'{label}: unknown fields {set(value)-set(props)}')
        for key in value:
            if key in props:
                check_schema(value[key], props[key], label + '.' + key)
    if typ == 'array':
        for index, item in enumerate(value):
            check_schema(item, schema['items'], f'{label}[{index}]')


def checked_asset(asset, label):
    path = resolve(asset['path'])
    require(path.is_file(), f'{label}: missing file {asset["path"]}')
    require(digest(path) == asset['sha256'], f'{label}: content changed; update provenance and review')
    return path


def filename(job):
    guest = job['episode']['guest']
    require(guest == guest.strip() and not re.search(r'[/\\<>:"|?*\x00-\x1f]', guest), 'Guest name contains unsafe filename characters')
    return f'TSSE{job["episode"]["number"]} {guest} quote {job["quote_number"]}.png'


def validate_input(job, spec):
    check_schema(job, read(SCHEMA_PATH))
    filename(job)
    require(all(k in spec for k in ['canvas','export','colors','quote','profiles','portrait','rule','disc','dots','marks','attribution','logo','footer']), 'Template is missing a required element')
    blockers = list(spec['unresolved']) if spec['status'] != 'approved' else []
    ep = job['episode']
    record = read(checked_asset({'path': ep['record_path'], 'sha256': ep['record_sha256']}, 'Episode record'))
    require(record.get('episode_number') == ep['number'] and record.get('guest_name') == ep['guest'], 'Episode/guest do not match the referenced episode record')
    q = job['quote']; source = q['source']
    require(q['text'] == normalized(q['text']), 'Published quote must use single spaces; specify line breaks separately')
    text = checked_asset(source, 'Transcript').read_text(encoding='utf-8')
    require(0 <= source['start'] < source['end'] <= len(text), 'Transcript passage offsets are invalid')
    require(text[source['start']:source['end']] == source['excerpt'], 'Transcript passage does not match the stored source excerpt')
    require(source['speaker'] == ep['guest'], 'Quote source speaker does not match the guest')
    # Speaker must be established in the source, not merely asserted in metadata.
    preceding = text[:source['start']]
    turns = list(re.finditer(r'^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?([A-Z][A-Za-z .’\'-]{1,79}):', preceding, re.M))
    require(bool(turns) and turns[-1].group(1).strip() == ep['guest'], 'Cannot verify the guest speaker for this source passage')
    require(not re.search(r'^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?[A-Z][A-Za-z .’\'-]{1,79}:', source['excerpt'], re.M), 'Passage crosses a speaker boundary')
    if not source['url'].startswith('https://podcast.sure.ventures/'):
        blockers.append('Transcript website source unresolved; local transcript is a provisional input only')
    if record.get('episode_url') and source['url']:
        require(source['url'].rstrip('/').removesuffix('/transcript') == record['episode_url'].rstrip('/'), 'Quote source URL belongs to a different episode')
    if q['classification'] == 'verbatim':
        require(normalized(q['text']) == normalized(source['excerpt']), 'Verbatim wording differs from the transcript passage')
    else:
        require(bool(q['editorial_note'].strip()), 'Edited or paraphrased text requires an editorial explanation')
    if q['classification'] == 'editorial_paraphrase':
        blockers.append('Editorial paraphrase: this direct-quote design cannot be approved; use a verified quote or approve a distinct paraphrase template')
    if q['review_status'] != 'approved':
        blockers.append('Quote wording/context requires human review')
    last = 0
    for span in q['emphasis']:
        require(last <= span['start'] < span['end'] <= len(q['text']), 'Emphasis ranges overlap or exceed quote text')
        last = span['end']
    paragraphs=q.get('paragraph_starts',[])
    require(paragraphs==sorted(set(paragraphs)), 'Paragraph starts must be unique and sorted')
    require(all(0 < v < len(q['text']) and q['text'][v-1]==' ' and q['text'][v]!=' ' for v in paragraphs), 'Paragraph starts must point to word boundaries')
    if q['lines']:
        require(normalized(' '.join(q['lines'])) == normalized(q['text']), 'Line breaks change the published wording')
    for key in ['bold', 'regular']:
        f = job['fonts'][key]; checked_asset(f, f'{key} font')
        if f['status'] != 'confirmed':
            blockers.append(f'{key} font is provisional ({f["family"]})')
    portrait = job['portrait']; bounds = spec['portrait']
    for k in ['x', 'y', 'width']:
        require(bounds[k+'_min'] <= portrait[k] <= bounds[k+'_max'], f'Portrait {k} is outside the template region')
    for key in ['original', 'cutout']:
        checked_asset(portrait[key], 'Portrait '+key)
        if portrait[key]['status'] != 'approved':
            blockers.append('Portrait '+key+' awaits identity/edge/provenance approval')
    with Image.open(resolve(portrait['cutout']['path'])) as im:
        require(im.mode == 'RGBA' and im.getchannel('A').getextrema() == (0, 255), 'Portrait cutout must have real transparency and opaque subject pixels')
    from publishing import portrait_assets
    try:
        candidate=resolve(portrait['approval_candidate'])
        approved=portrait_assets.approved(candidate,job['episode']['guest'])
        require(portrait['cutout']['sha256']==approved['files']['master.png'], 'Cutout must match the approved portrait master')
        require(portrait['original']['sha256']==approved['files'][approved['source']['stored_file']], 'Original must match approved portrait provenance')
    except (ValueError, OSError, KeyError) as error:
        raise ValidationError('Portrait approval: '+str(error)) from error
    require(resolve(spec['logo']['path']).is_file(), 'TSSE logo master is missing')
    require(digest(resolve(spec['logo']['path'])) == spec['logo']['sha256'], 'TSSE logo master does not match the pinned authentic source')
    with Image.open(resolve(spec['logo']['path'])) as im:
        require(im.mode == 'RGBA' and im.getchannel('A').getextrema() == (0, 255), 'TSSE logo must have genuine transparency')
    return blockers


def font(job, role, size):
    return ImageFont.truetype(str(resolve(job['fonts'][role]['path'])), round(size*SCALE), layout_engine=ImageFont.Layout.BASIC)


def text_positions(text, f, tracking=0):
    # Preserve kerning across highlighted spans; spacing uses the same advances
    # for wrapping, bounds and paint. Units here are supersampled pixels.
    return [f.getlength(text[:i])+i*tracking*SCALE for i in range(len(text))]


def text_bounds(text, f, tracking=0):
    boxes=[]
    for char,x in zip(text,text_positions(text,f,tracking)):
        b=f.getbbox(char,anchor='ls')
        if char.strip(): boxes.append((x+b[0],b[1],x+b[2],b[3]))
    require(bool(boxes),'Cannot lay out empty text')
    return (min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes))


def text_width(text,f,tracking=0):
    b=text_bounds(text,f,tracking)
    return max(b[2],f.getlength(text)+max(0,len(text)-1)*tracking*SCALE)


def wrap(text, f, width, tracking=0):
    lines, current = [], ''
    for word in text.split():
        candidate = (current + ' ' + word).strip()
        if text_width(candidate,f,tracking) > width*SCALE:
            require(bool(current) and text_width(word,f,tracking)<=width*SCALE, 'A single word exceeds the quote region')
            lines.append(current); current = word
        else:
            current = candidate
    if current: lines.append(current)
    return lines


def layout(job, spec):
    region=spec['quote'];quote=job['quote'];text=quote['text']
    starts=quote.get('paragraph_starts',[])
    profiles=['short','medium','long'] if job['profile']=='auto' else [job['profile']]
    for name in profiles:
        p=spec['profiles'][name];f=font(job,'bold',p['size']);tracking=p.get('tracking',0)
        if quote['lines']: lines=quote['lines']
        else:
            cuts=[0]+starts+[len(text)];lines=[]
            for start,end in zip(cuts,cuts[1:]): lines.extend(wrap(text[start:end].strip(),f,region['width'],tracking))
        if len(lines)>p['max_lines'] or any(text_width(line,f,tracking)>region['width']*SCALE for line in lines): continue
        cursor=0;line_starts=[]
        for line in lines:
            start=text.find(line,cursor);require(start>=0,'Cannot map line breaks to quote text');line_starts.append(start);cursor=start+len(line)
        require(all(v in line_starts for v in starts),'An explicit paragraph must begin on a new line')
        baseline=region['y']-text_bounds(lines[0],f,tracking)[1]/SCALE
        boxes=[];baselines=[];extra=0
        for i,line in enumerate(lines):
            if line_starts[i] in starts: extra+=p.get('paragraph_gap',0)
            by=baseline+i*p['leading']+extra;baselines.append(by);b=text_bounds(line,f,tracking)
            boxes.append([region['x']+b[0]/SCALE,by+b[1]/SCALE,region['x']+b[2]/SCALE,by+b[3]/SCALE])
        block_height=boxes[-1][3]-boxes[0][1]
        if block_height>p['max_height']: continue
        shift=(p['balance_bottom']-region['y']-block_height)/2 if p['alignment']=='center' else 0
        baselines=[v+shift for v in baselines]
        boxes=[[b[0],b[1]+shift,b[2],b[3]+shift] for b in boxes]
        if boxes[-1][3]>region['bottom']: continue
        a=spec['attribution'];divider_y=p['divider_y']
        if boxes[-1][3]+a['gap']>divider_y: continue
        name_y=divider_y+a['divider_height']+a['name_gap'];role_y=name_y+a.get('role_gap',33)
        if role_y+2*a['role_leading']>a['bottom']: continue
        for label,role,size,track in [(job['episode']['guest'].upper(),'bold',a['name_size'],a.get('name_tracking',0)),(job['attribution']['role'],'regular',a['role_size'],a.get('role_tracking',0)),(job['attribution']['company'],'regular',a['role_size'],a.get('role_tracking',0))]:
            require(text_width(label,font(job,role,size),track)<=region['width']*SCALE,'Attribution exceeds its region; use reviewed shorter wording')
        return {'profile':name,'lines':lines,'line_starts':line_starts,'baselines':baselines,'quote_boxes':boxes,'divider_y':divider_y,'name_y':name_y,'role_y':role_y,'block_height':block_height,'vertical_shift':shift,'font_size':p['size'],'tracking':tracking,'leading':p['leading'],'paragraph_gap':p.get('paragraph_gap',0)}
    raise ValidationError('Quote overflows the configured short/long regions; select a shorter quote or reviewed line breaks')


def gradient(size, top, bottom):
    from PIL import ImageColor
    ramp = Image.linear_gradient('L').resize(size)
    return Image.composite(Image.new('RGB', size, ImageColor.getrgb(bottom)), Image.new('RGB', size, ImageColor.getrgb(top)), ramp).convert('RGBA')


def rect(draw, box, color):
    draw.rectangle([round(v*SCALE) for v in box], fill=color)


def glow(image, settings, origin=(0,0)):
    """Deterministic elliptical falloff, measured in logical canvas coordinates."""
    import math
    from PIL import ImageColor
    width,height=image.size
    logical=(round(width/SCALE),round(height/SCALE))
    cx,cy=settings['center'];rx,ry=settings['radius']
    values=[]
    for y in range(logical[1]):
        for x in range(logical[0]):
            distance=((x+origin[0]-cx)/rx)**2+((y+origin[1]-cy)/ry)**2
            values.append(round(255*settings['strength']*math.exp(-2*distance)))
    mask=Image.new('L',logical);mask.putdata(values)
    mask=mask.resize(image.size,Image.Resampling.BILINEAR)
    return Image.composite(Image.new('RGBA',image.size,ImageColor.getrgb(settings['color'])+(255,)),image,mask)


def decoration(spec):
    w,h=spec['canvas'];colors=spec['colors']
    im=gradient((w*SCALE,h*SCALE),colors['background_top'],colors['background_bottom'])
    for settings in spec.get('background_glows',[]):im=glow(im,settings)
    dots=spec['dots'];cx,cy=dots['center'];step=dots['step']
    layer=Image.new('RGBA',im.size);d=ImageDraw.Draw(layer)
    for xi in range(int((w-450)/step)+1):
        x=450+xi*step
        for yi in range(int(600/step)+1):
            y=yi*step;distance=((x-cx)**2+(y-cy)**2)**.5
            if dots['radius_inner']<distance<dots['radius_outer']:
                strength=min(1,(dots['radius_outer']-distance)/dots['outer_fade'],(distance-dots['radius_inner'])/dots['inner_fade'])
                fade_start,fade_end=dots['vertical_fade']
                strength*=max(0,min(1,(fade_end-y)/(fade_end-fade_start)))
                r=dots['radius']
                d.ellipse(tuple(round(v*SCALE) for v in (x-r,y-r,x+r,y+r)),fill=(60,218,245,round(255*strength)))
    im.alpha_composite(layer)
    box=spec['disc']; size=(round((box[2]-box[0])*SCALE),round((box[3]-box[1])*SCALE))
    disc=gradient(size,colors['disc_top'],colors['disc_bottom'])
    disc=glow(disc,spec['disc_glow'],origin=box[:2]); mask=Image.new('L',size)
    ImageDraw.Draw(mask).ellipse((0,0,size[0]-1,size[1]-1),fill=255); disc.putalpha(mask)
    im.alpha_composite(disc,(round(box[0]*SCALE),round(box[1]*SCALE)))
    d=ImageDraw.Draw(im); rect(d,spec['rule'],colors['cyan'])
    # Cubic outline in mark-local coordinates, fixed from the raster references.
    def curve(a,b,c,e):
        return [tuple((1-t)**3*a[k]+3*(1-t)**2*t*b[k]+3*(1-t)*t*t*c[k]+t**3*e[k] for k in (0,1)) for t in [v/24 for v in range(25)]]
    shape=[(36,0),(38,4)]
    for segment in [((38,4),(20,15),(10,29),(10,40)),((10,40),(18,28),(39,32),(43,46)),((43,46),(49,63),(35,75),(20,72)),((20,72),(4,73),(-1,61),(1,43)),((1,43),(2,25),(16,9),(36,0))]:
        shape.extend(curve(*segment))
    marks=spec['marks']
    for offset in [0,54]:
        points=[((marks['x']+(x+offset)*marks['width']/99)*SCALE,(marks['y']+y*marks['height']/73)*SCALE) for x,y in shape]
        d.polygon(points,fill=colors['cyan'])
    return im


def draw_card(job, spec, plan):
    im=decoration(spec); colors=spec['colors']; portrait=job['portrait']
    photo=Image.open(resolve(portrait['cutout']['path'])).convert('RGBA')
    # Reusable master stays full-size; downstream fitting uses its alpha bounds.
    photo=photo.crop(photo.getbbox())
    width=round(portrait['width']*SCALE); height=round(width*photo.height/photo.width)
    # A cropped source must reach the footer, or its rectangular bottom edge would be visible.
    left_y=spec['footer'][0][1]+(spec['footer'][1][1]-spec['footer'][0][1])*portrait['x']/spec['canvas'][0]
    require(portrait['y']+height/SCALE >= left_y, 'Portrait bottom ends above the footer; enlarge or use a taller original')
    photo=photo.resize((width,height),Image.Resampling.LANCZOS)
    alpha=Image.new('L',im.size);alpha.paste(photo.getchannel('A'),(round(portrait['x']*SCALE),round(portrait['y']*SCALE)))
    for box in plan['quote_boxes']:
        area=alpha.crop(tuple(round(v*SCALE) for v in box))
        require(area.getextrema()[1] < 240, 'Portrait overlaps quote text; adjust the crop within the portrait region')
    im.alpha_composite(photo,(round(portrait['x']*SCALE),round(portrait['y']*SCALE)))
    d=ImageDraw.Draw(im); p=spec['profiles'][plan['profile']]; f=font(job,'bold',p['size'])
    original=job['quote']['text'];tracking=p.get('tracking',0)
    for i,line in enumerate(plan['lines']):
        start=plan['line_starts'][i];baseline=plan['baselines'][i]*SCALE
        for offset,(char,x) in enumerate(zip(line,text_positions(line,f,tracking))):
            highlight=any(span['start']<=start+offset<span['end'] for span in job['quote']['emphasis'])
            d.text((spec['quote']['x']*SCALE+x,baseline),char,font=f,anchor='ls',fill=colors['cyan'] if highlight else colors['white'])
    a=spec['attribution']; x=spec['quote']['x']; dy=plan['divider_y']
    rect(d,[x,dy,x+a['divider_width'],dy+a['divider_height']],colors['cyan'])
    for txt,role,size,y,color in [(job['episode']['guest'].upper(),'bold',a['name_size'],plan['name_y'],colors['cyan']),
                                (job['attribution']['role'],'regular',a['role_size'],plan['role_y'],colors['white']),
                                (job['attribution']['company'],'regular',a['role_size'],plan['role_y']+a['role_leading'],colors['white'])]:
        af=font(job,role,size);tracking=a.get('name_tracking',0) if role=='bold' else a.get('role_tracking',0)
        baseline=y*SCALE-text_bounds(txt,af,tracking)[1]
        for char,advance in zip(txt,text_positions(txt,af,tracking)):
            d.text((x*SCALE+advance,baseline),char,font=af,anchor='ls',fill=color)
    logo=Image.open(resolve(spec['logo']['path'])).convert('RGBA')
    logo=logo.crop(logo.getbbox()); lw=round(spec['logo']['width']*SCALE); lh=round(lw*logo.height/logo.width)
    require(lh<=spec['logo']['max_height']*SCALE,'Logo exceeds template height')
    im.alpha_composite(logo.resize((lw,lh),Image.Resampling.LANCZOS),(round(spec['logo']['x']*SCALE),round(spec['logo']['y']*SCALE)))
    top,bottom=spec['footer_gradient_region']
    strip=gradient((im.width,round((bottom-top)*SCALE)),colors['footer_top'],colors['footer_bottom'])
    footer=Image.new('RGBA',im.size,colors['footer_top']);footer.alpha_composite(strip,(0,round(top*SCALE))); mask=Image.new('L',im.size)
    ImageDraw.Draw(mask).polygon([(x*SCALE,y*SCALE) for x,y in spec['footer']],fill=255);footer.putalpha(mask);im.alpha_composite(footer)
    return im.convert('RGB').resize(tuple(spec['export']),Image.Resampling.LANCZOS)


def dependencies(job, spec):
    paths=[SPEC_PATH,SCHEMA_PATH,Path(__file__),ROOT/'publishing/requirements.txt',resolve(spec['logo']['path']),resolve(job['episode']['record_path']),resolve(job['quote']['source']['path'])]
    paths += [resolve(job['fonts'][r]['path']) for r in ['bold','regular']]
    paths += [resolve(job['portrait'][r]['path']) for r in ['original','cutout']]
    candidate=resolve(job['portrait']['approval_candidate'])
    paths += [Path(__file__).with_name('portrait_assets.py'),candidate,candidate.parent/'review.json']
    return {str(p.resolve()):digest(p) for p in paths}


def runtime():
    return {'python':platform.python_version(),'pillow':PIL_VERSION,'freetype':features.version('freetype2'),'layout_engine':'BASIC','supersampling':SCALE}


def render(job_path, out):
    job=read(job_path);spec=read(SPEC_PATH)
    blockers=validate_input(job,spec);plan=layout(job,spec)
    out=Path(out);require(not out.exists(),'Run directory already exists; use a new directory to preserve review history')
    im=draw_card(job,spec,plan)
    require(im.size==tuple(spec['export']),'Canvas dimensions are incorrect')
    require(abs(im.width/im.height-spec['canvas'][0]/spec['canvas'][1])<1e-9,'Canvas aspect ratio changed')
    out.mkdir(parents=True)
    name=filename(job);im.save(out/name,format='PNG',compress_level=9)
    with Image.open(resolve(job['portrait']['original']['path'])) as original_photo:
        photo_size=original_photo.size
    warnings=[]
    if photo_size[0] < job['portrait']['width']*spec['export'][0]/spec['canvas'][0]:
        warnings.append('Portrait is upscaled beyond source resolution; inspect sharpness and supply a higher-resolution authentic original when possible')
    report={'warnings':warnings,'automated_checks':'passed','approval_blockers':blockers,'geometry':plan,'dimensions':list(im.size),'filename':name,'format':'PNG',
            'quote_classification':job['quote']['classification'],'quote_diff':list(difflib.unified_diff(job['quote']['source']['excerpt'].splitlines(),job['quote']['text'].splitlines(),fromfile='source',tofile='display',lineterm=''))}
    (out/'input.json').write_text(json.dumps(job,indent=2,ensure_ascii=False)+'\n')
    (out/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    manifest={'state':'validated','history':['draft','rendered','validated'],'input_hash':value_hash(job),'dependencies':dependencies(job,spec),'runtime':runtime(),
              'output':name,'output_sha256':digest(out/name),'validation_sha256':digest(out/'validation.json'),'approval_blockers':blockers}
    manifest['run_id']=value_hash(manifest)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    issues=''.join('<li>'+html.escape(b)+'</li>' for b in blockers)
    preview=f'<!doctype html><meta charset="utf-8"><title>TSSE review</title><style>body{{background:#eee;font:16px sans-serif;margin:24px}}img{{max-width:940px;width:100%}}.notice{{background:#fff0cc;padding:16px}}</style><h1>UNAPPROVED REVIEW — {html.escape(job["episode"]["guest"])}</h1><p>Classification: {job["quote"]["classification"]} · Run {manifest["run_id"]}</p><div class="notice"><ul>{issues or "<li>Human review required</li>"}</ul></div><img src="{html.escape(name,quote=True)}"><p>Approval binds to the PNG and input hashes; this page is not a production approval.</p>'
    (out/'preview.html').write_text(preview)
    return manifest


def verify_run(out):
    out=Path(out);m=read(out/'manifest.json')
    require(m['state'] in {'validated','approved'}, 'Invalid review state')
    expected=['draft','rendered','validated']+(['approved'] if m['state']=='approved' else [])
    require(m['history']==expected, 'Invalid review state history')
    if m['state']=='approved':
        require(read(out/'approval.json')==m.get('approval'), 'Approval receipt changed')
        require(m['approval'].get('run_id')==m['run_id'] and m['approval'].get('decision')=='approved', 'Approval does not bind to this run')
    original={k:v for k,v in m.items() if k not in {'run_id','approval'}}
    original['state']='validated';original['history']=['draft','rendered','validated']
    require(value_hash(original)==m['run_id'],'Review manifest changed')
    require(value_hash(read(out/'input.json'))==m['input_hash'],'Review input changed')
    require(Path(m['output']).name==m['output'],'Unsafe output filename')
    require(digest(out/m['output'])==m['output_sha256'],'Rendered image changed after validation')
    require(digest(out/'validation.json')==m['validation_sha256'],'Validation report changed')
    for path,sha in m['dependencies'].items():
        require(Path(path).is_file() and digest(path)==sha,f'Input/template changed since rendering: {path}')
    require(runtime()==m['runtime'],'Renderer runtime changed; rerender before approval')
    validate_input(read(out/'input.json'),read(SPEC_PATH))
    return m


def approve(out,decision_path):
    out=Path(out);m=verify_run(out);decision=read(decision_path)
    require(m['state']=='validated','Only a validated, not already approved run can be approved')
    require(not m['approval_blockers'],'Unresolved brand/source specifications prevent approval: '+'; '.join(m['approval_blockers']))
    require(decision.get('run_id')==m['run_id'] and decision.get('decision')=='approved','Decision must explicitly approve this exact run ID')
    require(bool(str(decision.get('reviewer','')).strip()),'A human reviewer name is required')
    m['state']='approved';m['history'].append('approved')
    m['approval']={**decision,'recorded_at':datetime.now(timezone.utc).isoformat()}
    (out/'approval.json').write_text(json.dumps(m['approval'],indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    return m


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('render');p.add_argument('input');p.add_argument('--out',required=True)
    p=commands.add_parser('verify');p.add_argument('run')
    p=commands.add_parser('approve');p.add_argument('run');p.add_argument('--decision',required=True)
    args=parser.parse_args()
    try:
        result=render(args.input,args.out) if args.command=='render' else approve(args.run,args.decision) if args.command=='approve' else verify_run(args.run)
        print(json.dumps({'state':result['state'],'run_id':result['run_id'],'approval_blockers':result['approval_blockers']},indent=2))
    except (ValidationError,OSError,KeyError,ValueError) as exc:
        parser.exit(2,f'Quote card blocked: {exc}\n')


if __name__=='__main__':
    main()
