> Final status (2026-10-25): Milestone 1 approved and complete. See [closing implementation guide](quote-card-milestone-1.md). Pending-review statements below describe the historical review stage; source/editorial limitations remain recorded.

# Local portrait-processing pipeline — review candidate, 2026-10-25

Milestone 1 remains pending. These masters must be visually approved before replacing any
quote-card input. Neither quote-card layout nor the existing portrait assets is changed.

## Audit of the previous pipeline

`publishing/prepare_examples.py` used Pillow, with manually entered, guest-specific polygon
coordinates. `ImageDraw.polygon` created a binary mask; GaussianBlur(radius=1.1) then made a
soft alpha edge. This is feathering, not image-aware alpha matting. There was no segmentation
model, trimap, foreground estimation, erosion, dilation, or threshold cleanup.

The polygon was drawn at the original source resolution: Patrick 843 × 1064; authentic Pavel
400 × 400. Pixels outside the feathered polygon were discarded regardless of hair detail.
The cutout was cropped to its nonzero-alpha bounding box (Patrick 799 × 1020, Pavel 384 × 341).
RGB was copied unchanged. The quote renderer later resizes the cropped image into its portrait
region using Lanczos at 4× internal canvas scale, then downsamples the entire card to 1880 × 1576.
There was no resize before the original polygon operation.

Patrick's white residue has two causes: inaccurate polygon boundaries retain actual window
background, and mixed hair/background RGB values remain white-contaminated when alpha is added.
Blur changes coverage but cannot unmix those colors. Pavel's dark halo has the analogous problem
on a dark source; source softness and limited resolution are separate limitations.

## Dependency evaluation

| Approach | Strengths | Limitations / decision |
|---|---|---|
| Existing polygons + blur | Small, deterministic | Cannot recover strands or unmix RGB; rejected for new processing |
| U²-Net through rembg | Mature local ONNX option | Lower-resolution coarse segmentation; not selected for fine portrait boundaries |
| MODNet | Portrait-specific, trimap-free, real-time emphasis; Apache-2.0 repository | Useful lighter alternative, but does not by itself solve foreground-color contamination; not benchmarked on these photos |
| BiRefNet portrait + native-resolution PyMatting | Portrait-trained segmentation, soft probabilities, local CPU; separate alpha and color estimation | Large model (~927 MiB ONNX), more CPU/RAM; selected candidate |
| ViTMatte refinement | Learned trimap-conditioned alpha refinement | Additional model and runtime; fixed-resolution rembg export would resize again; reserve for cases where native closed-form refinement fails |
| Cloud removal | Potential convenience | Not evaluated or used; no portrait uploads |

Primary sources: [BiRefNet portrait model card](https://huggingface.co/ZhengPeng7/BiRefNet-portrait),
[rembg](https://github.com/danielgatis/rembg), [MODNet](https://github.com/ZHKKKe/MODNet),
[PyMatting alpha documentation](https://pymatting.github.io/alpha.html),
[PyMatting foreground documentation](https://pymatting.github.io/foreground.html).

BiRefNet's portrait model card labels the weights MIT. PyMatting and ONNX Runtime are MIT;
NumPy/SciPy use BSD licenses; Pillow uses HPND. Exact model source/checksums/license references
are recorded beside the configuration. rembg 2.0.86 was installed for evaluation, but the
runtime does not import it: a narrow ONNX adapter avoids implicit downloads and retains floating
mask precision. The final runtime dependency lock is `publishing/portraits/requirements.lock`;
the larger evaluation environment is recorded separately in ignored local data.

## Reproducible stages

1. Read the authentic source, apply EXIF orientation, retain source resolution and hash. Reject interior cutout alpha; preserve original export-frame alpha (Patrick has a half-transparent last column).
2. BiRefNet portrait predicts coverage from the required 1024 × 1024 normalized inference copy.
   The original RGB remains untouched. Native floating probability is retained in `segmentation.npy`.
3. Map probabilities back to source size. Build an automatic trimap with foreground ≥0.98 and
   background ≤0.02. Erode both certainty regions by a disk radius 0.4% of the shorter source side,
   clamped to 2–12 pixels. This expands the unknown region; it does not erode the final subject.
4. Closed-form PyMatting solves alpha at the original dimensions using source RGB and trimap.
   No final-alpha feathering, binary clipping or blur. Save float alpha and 16-bit diagnostic alpha.
5. Multilevel foreground estimation separates foreground color from background contamination
   under the compositing model I = alpha F + (1-alpha) B. Preserve original RGB where alpha ≥0.999;
   recover mixed boundary RGB elsewhere. This is numerical estimation, not generative replacement.
6. Save full-source-size straight-alpha RGBA `master.png`. Also save an optional bounding-box crop
   with 8-pixel padding as `trimmed.png`; no card resizing occurs in this stage.
7. Review on white, black, gray, TSSE navy/cyan and the actual template decoration.
   Only a later explicit approval may authorize renderer integration.

The same configuration is used for both guests. There are no guest names, polygon coordinates,
paint masks or portrait-specific cleanup settings in the processor.

CPU provider, sequential ONNX execution and one thread are pinned. Hashes cover source, model,
configuration, code, dependency lock and artifacts; runtime package versions are recorded.
Repeatability is verified on the tested platform, not promised bit-for-bit across different
hardware/library versions. A changed dependency invalidates verification. Failed matting creates
a `portrait_requires_review` failure record rather than silently falling back to the old polygon.

## Use

```sh
python3.12 -m venv .venv-portraits
.venv-portraits/bin/python -m pip install -r publishing/portraits/requirements.lock
# Download model from model.json into local storage and verify its recorded SHA-256.
.venv-portraits/bin/python -m publishing.portrait process /path/to/authentic-source.png \
  --model data/publishing/local/models/birefnet-portrait.onnx --out outputs/portraits/new-run
.venv-portraits/bin/python -m publishing.portrait verify outputs/portraits/new-run
.venv-portraits/bin/python -m publishing.portrait_review outputs/portraits/new-run \
  --previous-job data/publishing/local/patrick-source-sans.json --out outputs/portraits/new-review
.venv-portraits/bin/python -m unittest discover -s tests/publishing -v
```

Review preview coordinates are generic inspection rules, not mask edits. Full-resolution exports
and 2× nearest-neighbor detail files make edge defects visible. The portrait-only TSSE composite
uses the existing decoration function; it does not create a revised quote card.

## Approval and limits

Every master remains `portrait_requires_review` even when structural tests pass. Tests can check
real alpha, dimensions, plausible subject coverage, corners, clipping indicators and deterministic
reproduction. They cannot certify fine hair, glasses, identity, color recovery or attractive edges.
Occupied corners are reported, never forced transparent: a shoulder may genuinely occupy them.
Source-edge contact similarly needs interpretation against the original photograph.

The 400 × 400 Pavel original is soft and dark-on-dark. Numerical estimation cannot restore missing
hair strands or facial detail. The AI-recreated color portrait is excluded. Glasses and additional
background types are not represented by these two inputs and need future review cases.

## Results for this review

Current masters: `outputs/portraits/patrick-matting-v2/master.png` and
`outputs/portraits/pavel-matting-v1/master.png`. Before/after, background and enlarged edge
sheets are in `outputs/portraits/review/patrick/` and `outputs/portraits/review/pavel/`.
The earlier Patrick v1 run is historical (the runtime telemetry-disable change invalidates its
manifest); it is not the current review asset. ONNX telemetry is explicitly disabled in the
current adapter. Processing uses local files only and never uploads guest photographs.

Patrick: broad white polygon residue around the crown, hair sides and shoulders is removed.
Many fine strands are retained. Some outer curls remain slightly soft/translucent; small bright
hair highlights can be authentic reflections or residual contamination and require visual judgment.
Pavel: large polygon halo around the ear/neck is reduced and more crown detail is retained. The
original 400 × 400 photograph is intrinsically soft. Fine jagged texture around dark hair and
clothing against white/cyan is a processing limitation in uncertain, low-contrast boundary regions,
not newly recovered detail. It remains flagged for review; no detail has been fabricated.

Both use identical shared settings, no manual edits, no generative operations. Transparent masters
retain original dimensions. Patrick has 34,229 partial-alpha pixels; Pavel 5,342. Patrick's lower-right
corner stays partially occupied because the original sleeve reaches it (and the original export's
last column has alpha 128). His other corners and all four Pavel corners are transparent.
Both subjects extend through the bottom of their source photographs; the pipeline does not pretend
to recover missing body pixels beyond that boundary.

We also visually compared Patrick's raw model alpha plus foreground recovery with the native
closed-form refinement. The refined version retains a softer fringe of fine strands; the raw
version is slightly tighter/darker around those edges. The selected shared pipeline retains the
native refinement and exposes its artifacts for review rather than hiding them with blur.

Validation: all 32 tests passed (22 existing quote-card tests + 10 portrait tests). Added checks
cover trimap expansion, invalid seeds, synthetic white-fringe recovery, unchanged opaque pixels,
soft alpha, native dimensions, rectangular masks, occupied corners, repeatable matting, rejecting
interior pre-cut alpha, accepting export-frame alpha, and tamper detection. Some tests exercise
several related checks. Structural checks are not aesthetic approval.

Independent full inference/matting reruns for each photograph reproduced identical bytes for
segmentation arrays, alpha arrays, recovered foreground PNGs, master PNGs and trimmed PNGs.
Real-image opaque RGB was checked against each original and is unchanged. Evidence is retained
in `outputs/portraits/review/validation.json`; test output in `tests.txt` in that directory.

The next decision is human portrait-quality approval. No quote-card inputs were replaced,
no quote cards rerendered, no final implementation committed and nothing uploaded to production.
