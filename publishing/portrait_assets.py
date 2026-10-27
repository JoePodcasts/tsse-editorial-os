"""Independent, versioned portrait candidates and explicit human review decisions.

Approved masters are reusable without the segmentation runtime or original model.
Files are immutable by convention and hash-checked; this is an editorial audit trail,
not an authentication service against someone with filesystem write access.
"""
import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image

DECISIONS={'approve','try_another_approach','use_another_source','provide_transparent_portrait','reject'}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write_new(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
def now():return datetime.now(timezone.utc).isoformat()


def validate_master(path):
    with Image.open(path) as im:
        if im.format!='PNG' or im.mode!='RGBA':raise ValueError('Master must be an RGBA PNG')
        a=im.getchannel('A');lo,hi=a.getextrema()
        if lo!=0 or hi!=255:raise ValueError('Master must contain transparent background and opaque foreground')
        warnings=[]
        if min(im.size)<600:warnings.append('low_resolution_source_or_master')
        if not any(0<v<255 for v in a.getdata()):warnings.append('no_partial_alpha_edges')
        return {'state':'portrait_requires_review','dimensions':list(im.size),'alpha_bbox':list(a.getbbox()),'warnings':warnings,'visual_review_required':True}


def register(root,candidate_id,guest,source,master,provenance,kind='supplied_transparent',processing_run=None,parent=None,limitations=None):
    root=Path(root).resolve();source=Path(source).resolve();master=Path(master).resolve()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*',candidate_id):raise ValueError('Invalid candidate ID')
    if not guest.strip() or not provenance.strip():raise ValueError('Guest and source provenance required')
    if kind not in {'algorithmically_processed','supplied_transparent'}:raise ValueError('Unknown origin kind')
    if parent:
        parent=Path(parent).resolve()
        if read(parent)['guest']!=guest:raise ValueError('Parent belongs to another guest')
    report=validate_master(master)
    if kind=='algorithmically_processed':
        if not processing_run:raise ValueError('Processing evidence required')
        from publishing.portrait import verify
        run=Path(processing_run).resolve();m=verify(run)
        if digest(master)!=m['artifacts']['master.png'] or digest(source)!=digest(m['source']):raise ValueError('Processing source/master mismatch')
    elif processing_run:raise ValueError('Supplied transparent master must not claim algorithmic processing')
    target=root/candidate_id;target.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(source,target/('source'+source.suffix.lower()))
    shutil.copyfile(master,target/'master.png')
    files={'master.png':digest(target/'master.png'),'source'+source.suffix.lower():digest(source)}
    if kind=='algorithmically_processed':
        for src,dst in [('manifest.json','processing.json'),('report.json','processing-report.json')]:
            shutil.copyfile(run/src,target/dst);files[dst]=digest(target/dst)
    write_new(target/'validation.json',report);files['validation.json']=digest(target/'validation.json')
    record={'schema_version':1,'candidate_id':candidate_id,'guest':guest,'state':'portrait_requires_review','created_at':now(),'origin_kind':kind,'source':{'original_path':str(source),'stored_file':'source'+source.suffix.lower(),'provenance':provenance},'processing_run':str(Path(processing_run).resolve()) if processing_run else None,'parent_candidate':str(parent) if parent else None,'source_quality_limitations':limitations or [],'files':files}
    write_new(target/'candidate.json',record)
    return target/'candidate.json'


def verify_candidate(path):
    path=Path(path).resolve();record=read(path)
    for name,sha in record['files'].items():
        if Path(name).name!=name:raise ValueError('Invalid asset path')
        if digest(path.parent/name)!=sha:raise ValueError('Portrait asset content changed: '+name)
    validate_master(path.parent/'master.png')
    return record


def decide(candidate,decision,reviewer,evidence,note=''):
    candidate=Path(candidate).resolve();record=verify_candidate(candidate)
    if decision not in DECISIONS:raise ValueError('Unknown review decision')
    if not reviewer.strip() or not evidence.strip():raise ValueError('Human reviewer and authorization evidence required')
    review={'candidate_sha256':digest(candidate),'candidate_id':record['candidate_id'],'decision':decision,'state':'approved_master' if decision=='approve' else 'rejected' if decision=='reject' else 'revision_requested','reviewer':reviewer,'authorization_evidence':evidence,'recorded_at':now(),'note':note}
    write_new(candidate.parent/'review.json',review)
    return review


def approved(candidate,guest=None):
    candidate=Path(candidate).resolve();record=verify_candidate(candidate)
    review=read(candidate.parent/'review.json')
    if review['candidate_sha256']!=digest(candidate):raise ValueError('Portrait candidate changed after review')
    if review['decision']!='approve' or review['state']!='approved_master':raise ValueError('Portrait master has not received human approval')
    if guest is not None and record['guest']!=guest:raise ValueError('Approved portrait guest mismatch')
    return record


def select_current(candidate):
    candidate=Path(candidate).resolve();record=approved(candidate)
    # Selection is explicit, never inferred from latest processing output. Prior versions remain.
    path=candidate.parent.parent/'current.json'
    current=read(path) if path.exists() else {}
    current[record['guest']]={'candidate':str(candidate),'candidate_sha256':digest(candidate),'selected_at':now()}
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(current,indent=2)+'\n');temporary.replace(path)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('register');r.add_argument('--root',required=True);r.add_argument('--id',required=True);r.add_argument('--guest',required=True);r.add_argument('--source',required=True);r.add_argument('--master',required=True);r.add_argument('--provenance',required=True);r.add_argument('--kind',choices=['algorithmically_processed','supplied_transparent'],default='supplied_transparent');r.add_argument('--processing-run');r.add_argument('--parent');r.add_argument('--limitation',action='append',default=[])
    d=sub.add_parser('decide');d.add_argument('candidate');d.add_argument('--decision',choices=sorted(DECISIONS),required=True);d.add_argument('--reviewer',required=True);d.add_argument('--evidence',required=True);d.add_argument('--note',default='')
    s=sub.add_parser('select-current');s.add_argument('candidate')
    a=p.parse_args()
    if a.command=='register':print(register(a.root,a.id,a.guest,a.source,a.master,a.provenance,a.kind,a.processing_run,a.parent,a.limitation))
    elif a.command=='decide':print(json.dumps(decide(a.candidate,a.decision,a.reviewer,a.evidence,a.note),indent=2))
    else:select_current(a.candidate)

if __name__=='__main__':main()
