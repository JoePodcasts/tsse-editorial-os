> Final status (2026-10-25): Milestone 1 approved and complete. See [closing implementation guide](quote-card-milestone-1.md). Pending-review statements below describe the historical review stage; source/editorial limitations remain recorded.

# Source Sans Pro calibration — 2026-10-24

Milestone 1 remains pending. No implementation commit, delivery or upload is authorized yet.
This report supersedes the earlier Arial visual review. The font family is user-confirmed;
weight, size and spacing are calibrated candidates awaiting visual approval.

Adobe's original Source Sans Pro 2.045 OTF release is vendored with its SIL OFL license and
SHA-256 provenance in the template fonts directory. This is not Source Sans 3.
Regular, Semibold, Bold and Black were compared with normalized 940 × 788 references.
Line silhouettes, ink width/height, line spacing and visual comparison informed selection;
Canva's 38.9 value was not interpreted as renderer pixels. Raster comparisons are approximate,
not proof of the original weight: antialiasing, scaling and mixed weights limit inference.
Semibold (600) gave the closest overall fit; role/company text uses Regular (400).

| Shared rule | Short quote | Long quote |
|---|---:|---:|
| Font size, logical units | 60.75 | 45 |
| Baseline spacing | 63 | 46 |
| Letter spacing | -0.5 | -0.65 |
| Additional paragraph spacing | 15 | 15 |
| Maximum lines | 5 | 7 |

Logical canvas: 940 × 788; export: 1880 × 1576. The same template selects profiles by
fit. These are quote-length profiles, not guest-specific font settings. Explicit reference
line breaks and a paragraph boundary are content metadata; no guest-specific baseline offsets.
The common first text ink top is 165; quote width 440. Attribution follows the measured text
bottom with a 20-unit gap, then the divider and name. Name uses Semibold 28 with tracking 0.6;
roles use Regular 22.5 with 24-unit leading. Highlight spans share baselines and advances.
Pavel keeps editorial_paraphrase metadata. Patrick retains the verified verbatim passage.
Authentic photographs and existing candidate masks are unchanged.

## Review files

- `outputs/quote_cards/pavel-source-sans-review/`
- `outputs/quote_cards/patrick-source-sans-review/`
- Comparison sheets and native mask inspections: `outputs/quote_cards/source-sans-review/`
- `revised-pair.png`: both revised renders.
- `pavel-reference-output.png`: approved Pavel reference versus revised.
- `patrick-template-output.png`: approved Kapil short-quote design versus Patrick.
- `patrick-existing-output.png`: existing Patrick graphic versus revised; approval unconfirmed.

The supplied approved references are Pavel and Kapil. The older Patrick graphic has a different
quote, circular crop, quotation marks and decoration. It is contextual evidence, not a verified
approved target for this revised card.

## Remaining visible differences

Template differences: Pavel's revised type is still slightly narrower/lighter in places,
particularly the highlighted words and name. The seven reference lines and paragraph division
are preserved; descenders and text bounds still differ. Quote top/left margins, quotation-mark
placement and cyan rule are close, but mark contours differ. Dots are smaller/sparser and their
fade differs; the background and disc lack the reference's localized glow. Disc placement is
shared, but different masks reveal different amounts of it. The authentic supplied logo has
different proportions and appears narrower than the reference wordmark. Footer angle is close;
its current gradient is flatter. These remain template decisions, not guest-specific corrections.

Input/content differences: Pavel is grayscale and visibly soft because the authentic source is
400 × 400. His portrait and crop cannot reproduce the AI-recreated color reference exactly.
That is an input-quality limitation. Patrick's shorter quote naturally produces four larger
lines and a higher attribution, leaving more space above the logo. His portrait has a different
pose and shoulder shape. Both masks need refinement: Pavel has a dark halo, Patrick has white
residue around hair and some abrupt shoulder edges. Native-resolution masks and enlarged edge
panels are included for review. No generative reconstruction was used.

## Validation

Full repository test inventory contains `tests/publishing/test_quote_card.py`.
`python -m unittest discover -s tests/publishing -v`: 22 passed, no skips.
Both current run manifests verified during comparison-sheet generation. Repeat-render tests
confirm byte-identical PNGs. Tests cover provenance, quote classification, geometry, paragraph
baselines, overflow, asset tampering and approval gates. They do not establish aesthetic approval.
