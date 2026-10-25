"""Local, non-generative portrait segmentation, native-resolution matting and RGB recovery.

No layout dependency, guest coordinates, automatic downloads, painting or image synthesis.
Every result requires visual approval. Run with the isolated portrait requirements.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path

# Fixed CPU execution avoids device-dependent defaults. Set before importing numba/BLAS.
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS']:
    os.environ[key] = '1'

import numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import binary_erosion, label
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'publishing/portraits/config.json'
MODEL_RECORD = ROOT/'publishing/portraits/model.json'


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for part in iter(lambda: f.read(1024*1024), b''): h.update(part)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def original(path):
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if 'A' in im.getbands():
            a = np.asarray(im.getchannel('A'))
            # Some authentic web exports have a partial-alpha outermost pixel row/column.
            # Permit that framing artifact, but reject pre-existing interior cutouts.
            if a[1:-1,1:-1].min() < 255:
                raise ValueError('Use the authentic opaque original, not an existing cutout')
        return im.convert('RGB')


def validate_config(c):
    if c['model'] != 'birefnet-portrait' or c['model_input'] != 1024:
        raise ValueError('Unsupported model/input contract')
    if not 0 < c['background_threshold'] < c['foreground_threshold'] < 1:
        raise ValueError('Invalid trimap thresholds')
    if c['alpha_solver'] != 'closed_form' or c['foreground_solver'] != 'multilevel':
        raise ValueError('Unsupported matting solver')
    if not 1 <= c['unknown_radius_min'] <= c['unknown_radius_max'] <= 32:
        raise ValueError('Invalid unknown-band radius')


def segment(image, model_path, config):
    import onnxruntime as ort
    ort.disable_telemetry_events()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session = ort.InferenceSession(str(model_path), sess_options=options, providers=['CPUExecutionProvider'])
    size = config['model_input']
    # Model contract uses square 1024 input. Only this inference copy is resized.
    x = np.asarray(image.resize((size, size), Image.Resampling.LANCZOS), dtype=np.float32)/255
    x = (x-np.array([.485,.456,.406], np.float32))/np.array([.229,.224,.225], np.float32)
    x = np.ascontiguousarray(x.transpose(2,0,1)[None])
    logits = session.run(None, {session.get_inputs()[0].name:x})[0]
    probability = expit(np.asarray(logits).squeeze()).astype(np.float32)
    if probability.ndim != 2 or not np.isfinite(probability).all():
        raise ValueError('Model returned invalid segmentation')
    # Keep floating precision; no binary thresholding of the returned mask.
    return np.clip(np.asarray(Image.fromarray(probability).resize(image.size, Image.Resampling.BILINEAR)), 0, 1)


def trimap_from_probability(probability, config):
    radius = max(config['unknown_radius_min'], min(config['unknown_radius_max'], round(min(probability.shape)*config['unknown_radius_fraction'])))
    yy,xx = np.ogrid[-radius:radius+1,-radius:radius+1]
    structure = xx*xx+yy*yy <= radius*radius
    # Erode the CERTAINTY regions to expand the unknown band, not the final alpha.
    fg = binary_erosion(probability >= config['foreground_threshold'], structure=structure, border_value=1)
    bg = binary_erosion(probability <= config['background_threshold'], structure=structure, border_value=1)
    if not fg.any() or not bg.any():
        raise ValueError('No reliable foreground/background seed; portrait_requires_review')
    trimap = np.full(probability.shape, .5, dtype=np.float64)
    trimap[bg] = 0
    trimap[fg] = 1
    return trimap, radius


def recover_foreground(rgb, alpha, config):
    from pymatting import estimate_foreground_ml
    foreground = estimate_foreground_ml(rgb, alpha)
    foreground = np.clip(foreground, 0, 1).astype(np.float64)
    # Do not recolor opaque skin, eyes or clothing. Only mixed edges need unmixing.
    opaque = alpha >= config['opaque_preservation_threshold']
    foreground[opaque] = rgb[opaque]
    foreground[alpha == 0] = 0
    return foreground


def matte(rgb, probability, config):
    from pymatting import estimate_alpha_cf
    trimap, radius = trimap_from_probability(probability, config)
    alpha = estimate_alpha_cf(rgb, trimap, cg_kwargs={'rtol':config['solver_rtol'], 'maxiter':config['solver_maxiter']})
    if not np.isfinite(alpha).all(): raise ValueError('Non-finite matte; portrait_requires_review')
    alpha = np.clip(alpha, 0, 1)
    foreground = recover_foreground(rgb, alpha, config)
    return alpha, foreground, trimap, radius


def rgba_image(foreground, alpha):
    return Image.fromarray(np.rint(np.dstack((foreground,alpha))*255).clip(0,255).astype(np.uint8))


def inspect_master(master, source_size, config, probability=None):
    if master.mode != 'RGBA': raise ValueError('Transparent master must be RGBA')
    alpha = np.asarray(master.getchannel('A'))
    if master.size != tuple(source_size): raise ValueError('Master must retain original dimensions')
    warnings = []
    foreground = alpha > 8
    bbox = master.getchannel('A').getbbox()
    fraction = float(foreground.mean())
    soft = int(((alpha > 0)&(alpha < 255)).sum())
    if alpha.min() != 0 or alpha.max() != 255: warnings.append('missing_transparent_background_or_opaque_foreground')
    if not config['minimum_subject_fraction'] < fraction < config['maximum_subject_fraction']: warnings.append('implausible_subject_area')
    if soft == 0: warnings.append('no_partial_alpha_boundary')
    if min(source_size) < config['minimum_source_short_side']: warnings.append('low_resolution_source')
    corners = {name:int(alpha[y,x]) for name,y,x in [('top_left',0,0),('top_right',0,-1),('bottom_left',-1,0),('bottom_right',-1,-1)]}
    # A shoulder can genuinely extend into a bottom corner: flag, never erase it.
    if any(corners.values()): warnings.append('subject_or_background_at_image_corner_review_source')
    touched = []
    for name,edge in [('top',alpha[0]),('bottom',alpha[-1]),('left',alpha[:,0]),('right',alpha[:,-1])]:
        if np.any(edge>8): touched.append(name)
    if 'top' in touched: warnings.append('head_may_touch_source_boundary')
    if probability is not None:
        missing = float(np.mean(alpha[probability>.98]<128)) if np.any(probability>.98) else 1.0
        if missing>.01: warnings.append('foreground_loss_vs_segmentation')
    else: missing = None
    _,components = label(foreground)
    return {'state':'portrait_requires_review','checks':{'dimensions':list(master.size),'alpha_extrema':[int(alpha.min()),int(alpha.max())], 'partial_alpha_pixels':soft,'subject_fraction':fraction,'alpha_bbox':list(bbox) if bbox else None,'corners':corners,'source_edges_touched':touched,'connected_components':components,'foreground_loss_fraction':missing},'warnings':warnings,'review_required':['hair and fine edges','ears, shoulders, clothing, glasses if present','foreground color recovery on dark and cyan backgrounds','source identity and crop']}


def runtime():
    packages=['Pillow','numpy','scipy','pymatting','numba','llvmlite','onnxruntime']
    return {'python':platform.python_version(),'machine':platform.machine(),'provider':'CPUExecutionProvider','threads':1,'packages':{p:importlib.metadata.version(p) for p in packages}}


def process(source, model, out, config_path=CONFIG, model_record_path=MODEL_RECORD):
    source,model,out = Path(source).resolve(),Path(model).resolve(),Path(out).resolve()
    if out.exists(): raise ValueError('Output directory already exists; preserve previous runs')
    c = read(config_path);validate_config(c)
    record = read(model_record_path)
    if digest(model) != record['sha256']: raise ValueError('Model checksum mismatch')
    im = original(source)
    out.mkdir(parents=True)
    write(out/'config.json', c)
    try:
        probability = segment(im,model,c)
        np.save(out/'segmentation.npy',probability)
        Image.fromarray(np.rint(probability*255).astype(np.uint8)).save(out/'segmentation.png')
        rgb = np.asarray(im,dtype=np.float64)/255
        alpha,foreground,trimap,radius = matte(rgb,probability,c)
        np.save(out/'alpha.npy', alpha)
        Image.fromarray(np.rint(trimap*255).astype(np.uint8)).save(out/'trimap.png')
        Image.fromarray(np.rint(alpha*65535).astype(np.uint16)).save(out/'alpha-16bit.png')
        Image.fromarray(np.rint(foreground*255).astype(np.uint8)).save(out/'foreground.png')
        with Image.open(source) as source_image:
            source_image = ImageOps.exif_transpose(source_image)
            source_alpha = np.asarray(source_image.getchannel('A'),dtype=np.float64)/255 if 'A' in source_image.getbands() else np.ones(alpha.shape)
        # Preserve any original export-frame transparency; do not invent opaque border pixels.
        master = rgba_image(foreground,alpha*source_alpha);master.save(out/'master.png')
        report = inspect_master(master,im.size,c,probability)
        report.update({'segmentation_input':[1024,1024],'matting_resolution':list(im.size),'unknown_radius_px':radius,'final_alpha_blur':False,'source_sha256':digest(source),'source_partial_alpha_pixels':int((source_alpha<1).sum())})
        bbox = master.getbbox()
        if bbox:
            pad = c['crop_padding'];w,h = master.size
            crop = [max(0,bbox[0]-pad),max(0,bbox[1]-pad),min(w,bbox[2]+pad),min(h,bbox[3]+pad)]
            master.crop(crop).save(out/'trimmed.png')
            report['optional_trimmed_asset_box'] = crop
        write(out/'report.json',report)
        dependencies = [source,model,Path(config_path).resolve(),Path(model_record_path).resolve(),Path(__file__).resolve(),ROOT/'publishing/portraits/requirements.lock']
        manifest = {'state':'portrait_requires_review','source':str(source),'config':c,'runtime':runtime(),'dependencies':{str(p):digest(p) for p in dependencies},'artifacts':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}}
        write(out/'manifest.json',manifest)
        return report
    except Exception as error:
        write(out/'failure.json',{'state':'portrait_requires_review','error':str(error),'source_sha256':digest(source),'source_partial_alpha_pixels':int((source_alpha<1).sum())})
        raise


def verify(out):
    out = Path(out);m = read(out/'manifest.json')
    for path,expected in m['dependencies'].items():
        if digest(path)!=expected: raise ValueError('Portrait dependency changed: '+path)
    for name,expected in m['artifacts'].items():
        if digest(out/name)!=expected: raise ValueError('Portrait artifact changed: '+name)
    if runtime()!=m['runtime']: raise ValueError('Portrait runtime changed')
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__);sub = p.add_subparsers(dest='command',required=True)
    run = sub.add_parser('process');run.add_argument('source');run.add_argument('--model',required=True);run.add_argument('--out',required=True);run.add_argument('--config',default=str(CONFIG))
    check = sub.add_parser('verify');check.add_argument('out')
    args = p.parse_args()
    result = process(args.source,args.model,args.out,args.config) if args.command=='process' else verify(args.out)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
