> Final status (2026-10-25): Milestone 1 approved and complete. See [closing implementation guide](quote-card-milestone-1.md). Pending-review statements below describe the historical review stage; source/editorial limitations remain recorded.

# Bounded canonical-template refinement — awaiting human approval

This pass follows the user's approval of the architecture and portrait assets. It changes shared
template rules only. No portrait processing, manual retouching, logo distortion, final commit or
production delivery. The authentic supplied logo remains the same hash and uniform scaling.
The compact wordmark in older references appears to be a historical variant; it is not recreated
by stretching the current master.

## Quote modes

Canvas coordinates below are logical units on 940 × 788; export is 1880 × 1576.
Source Sans Pro Bold (700) is shared for quote text and names; Regular (400) for roles/company.
Reference stroke density informed the change from Semibold; there is no horizontal font scaling.

| Mode | Font size / baseline spacing | Maximum lines / measured ink height | Vertical treatment | Attribution divider |
|---|---|---|---|---|
| Short | 58.5 / 63 | 4 / 245 | Center ink block between y=165 and y=470 | y=499 |
| Medium | 58.5 / 63 | 5 / 310 | Top-align ink at y=165 | y=499 |
| Long | 43.25 / 46 | 7 / 337 | Top-align ink at y=165 | y=516 |

All modes use x=73, width=440; tracking is -0.5 in short/medium and -0.55 in long. Paragraphs add
15 units. Names use Bold 26.5 with 0.6 tracking; roles use Regular 22.5 with 24-unit baseline spacing.

`profile: auto` measures actual shaped text advances and painted bounds, testing short, medium,
then long. No character-count thresholds. Explicit line breaks and paragraph boundaries participate
in measurements. A mode must satisfy width, line count, ink-height limit, quote bottom y=502,
at least 16 units before its divider and attribution bounds. The tightest constraint wins.
A manual `short`, `medium` or `long` choice is supported but cannot bypass safety/overflow checks.
Oversize copy fails visibly rather than silently shrinking or clipping.

Patrick selects short: four lines centered in the quote region, with the name/role block anchored
near the canonical short-quote reference. Pavel selects long and retains seven reference lines
plus the paragraph boundary. These are shared rules, not guest-name branches.

## Portrait placement

No evidence established that Pavel's reference difference was caused by a faulty shared region
rule: the reference has a different, AI-recreated portrait with different head/body proportions.
The existing framing is retained. Each approved full-size master is cropped to its alpha bounds
in memory, uniformly scaled to the specified width and placed at reviewed x/y coordinates within
the template's bounded right-side region. Quote overlap and footer reach are validated. The
coordinates remain explicit human-adjustable framing inputs, not hidden guest-name exceptions.
Portrait masters are never rewritten, sharpened, reconstructed or automatically reprocessed.

## Decoration

- Dots: 14.5-unit spacing, 1.15-unit radius, annular field centered at (850,330), radii 240–410;
  smooth inner/outer opacity fades plus a vertical fade from y=380 to y=570. This fills the overly
  sparse previous field without leaving strong dots behind the lower attribution region.
- Background: dark navy gradient with an elliptical, localized blue glow centered at (280,150).
- Portrait circle: original shared geometry (514,128)–(1060,674), dark blue base and localized
  cyan-blue glow centered at (880,220). The falloff is a deterministic elliptical exponential.
- Footer: unchanged diagonal shape. Cyan ramp spans y=664–788, the footer region, rather than
  sampling only the bottom of a full-canvas gradient. This restores a visible cyan-to-light-cyan ramp.
- Authentic logo: unchanged master, aspect ratio, size and placement. Historical proportions are
  documented as a source/template-version difference.

These are deterministic reconstructions from flattened references, not recovery of the original
Canva layers. Minor curvature/falloff differences remain; this bounded pass does not pursue pixel
identity across different source photographs, raster scales and historical logo variants.

## Final review and validation

- `outputs/quote_cards/pavel-final-template/`
- `outputs/quote_cards/patrick-final-template/`
- `outputs/quote_cards/final-template-review/final-pair.png`
- `outputs/quote_cards/final-template-review/pavel-reference-output.png`
- `outputs/quote_cards/final-template-review/patrick-template-output.png` (approved Kapil canonical
  short-quote graphic, not the unapproved historical Patrick card)

All 41 tests pass, including new checks for automatic measured-mode selection, short-block
centering, fixed attribution across short/medium modes, manual mode override and localized glow.
Existing paragraph-spacing, deterministic PNG, overflow, provenance, portrait approval, asset
reuse and tamper tests pass. Current run manifests verify. Portrait master bytes remain unchanged.

Remaining asset limitations: Pavel's 400 × 400 grayscale photo is soft and has low-contrast
boundary detail; its proportions differ from the recreated color reference. Patrick's accepted
outer curls remain partly soft. The authentic logo differs from the historical reference variant.
Pavel's wording stays editorial_paraphrase; a visual template approval does not turn it into a
verified transcript quote or authorize direct-quote publication.

Milestone 1 remains pending explicit final human approval and is uncommitted.
