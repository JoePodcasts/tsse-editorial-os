> Final status (2026-10-25): Milestone 1 approved and complete. See [closing implementation guide](quote-card-milestone-1.md). Pending-review statements below describe the historical review stage; source/editorial limitations remain recorded.

> Superseded typography and preview details: see [current Source Sans Pro calibration](quote-card-source-sans-calibration.md). The earlier Arial notes below are historical. Current full suite: 22 passed; Milestone 1 remains pending.

# Current-state visual review — 2026-10-24

## Typography confirmation — 2026-10-24

The user confirmed **Source Sans Pro** as the font family after supplying a Canva screenshot of the selected quote text. This supersedes earlier statements that the family was unidentified. The screenshot displays a Canva size value of **38.9** for the Bhaskar example; that value is not yet mapped to renderer pixels or established as the size for every quote-length profile.

Still unresolved: the font-file version and usable files, weight/style for each text role and approved reference, letter spacing, line spacing, and design-size-to-export scaling. The family confirmation alone does not establish the attribution font or every reference's weight. Source Sans 3 must not silently replace Source Sans Pro.

Current Arial previews, renderer inputs, and template geometry remain unchanged for review. The provisional 39-unit long-profile workaround is not a canonical Source Sans Pro measurement. Replace it through shared typography/layout rules once the remaining evidence is resolved, then rerender both cards and run the full suite. Milestone 1 remains pending explicit approval; no final commit or production upload.

Milestone 1 remains pending. No renderer, template, job, mask, font, or generated card was changed for this review. The existing `pavel-review-2` and `patrick-review-2` runs passed integrity verification; their PNG hashes were checked unchanged after producing comparison sheets. No commit, production upload, or Milestone 2 work occurred. Comparison sheets only scale existing images for display and add labels outside them.

## Reference identity

The supplied Kapil and Pavel graphics are the confirmed approved design references. A separately approved Patrick reference has not been established in this conversation. Patrick's current output therefore tests the shared short-quote design against Kapil, not an asserted approved same-guest original.

The existing Patrick Drive graphic (file ID `1NZd7FWX9oL75Bb9XQ281QtNOpcS-RNk3`) was downloaded read-only for context. It is 1370 × 1148 and has a circular photo crop, retained photo background, rectangular dot field, angular quotation marks and different wording: “What are you bringing to the table that's unique and different?” Its approval status is not established. The current render uses “Capital is a commodity. So you need a real edge.” It cannot be evaluated as a same-content reproduction of that older card. Neither its circular crop nor other differences have been adopted as canonical rules.

## Comparison files

All are under `outputs/quote_cards/visual-review/`:

- `pavel-reference-output.png`: approved Pavel design → unchanged Pavel output.
- `patrick-template-output.png`: approved Kapil short-quote design → unchanged Patrick output.
- `patrick-existing-output.png`: existing Patrick Drive card → unchanged Patrick output; not labelled approved.
- `pavel-mask-native.png`, `patrick-mask-native.png`: exact current cutouts at native pixel dimensions, over checkerboard, white, and as raw alpha.
- `pavel-edge-detail.png`, `patrick-edge-detail.png`: enlarged hair/face and shoulder/arm inspection crops. Enlargement exposes existing defects; it does not recover source detail.
- `review-evidence.json`: unchanged card hashes and reference-status notes.

The unchanged current pair is `outputs/quote_cards/review-pair-2.png`.

## Visible differences

Measurements below use a 940 × 788 comparison coordinate system. Reference bounds are approximate raster observations; output values come from the existing specification and validation reports. Pixel glyph height is not equivalent to a font's nominal size.

| Feature | Current difference | Classification |
| --- | --- | --- |
| Typeface | Arial/Arial Bold differs in letter shapes and metrics; the reference face remains unidentified. | Template/typography |
| Font weight | Current text has a more uniform, heavier-looking bold treatment, especially Patrick; original weight cannot be named from raster evidence. | Template; visual assessment, not a measured font-weight number |
| Font size | Output nominal size is 56 for short, 39 for long. The 39 setting was a substitute-font fitting workaround, not a recovered reference size. Pavel's visible capitals are smaller than the reference. | Template; provisional |
| Line height | Output leading is 63/46. Reference short-quote spacing is approximately 63; Pavel's ordinary line spacing is near 46 with additional paragraph separation. Glyph ascenders/descenders prevent inferring line height from every ink-row gap. | Template |
| Paragraph spacing | Pavel lacks the larger gap before “Only founders…”; this compresses the second paragraph upward. | Template |
| Quote wrapping | Pavel preserves the reference's seven lines and cyan phrase split. Patrick uses four lines with “edge.” alone; Kapil has five and the existing Patrick card uses entirely different wording. | Pavel: matched wrapping but different font metrics; Patrick: content plus typography |
| Margins | Left quote x=73 matches both references within raster tolerance. Current top y=160 is about 5 px above Pavel's reference ink and about 7–9 px above Kapil's. | Template |
| Quotation marks | Position/overall footprint is close (~70/56, width 99, height 73), but the drawn bowls/tails have different contours and tonal treatment. | Template |
| Cyan rule | Start/end/height are close (~191–498 at y=95); current 1.5 px thickness, flat color and antialiasing are not exact reference matches. | Template |
| Dots | Current annular fade is visibly sparser and dimmer, with a large clear central area. References have a brighter, denser-looking curved field extending farther behind the portrait. Grid step alone does not reproduce the original density/fade. | Template |
| Portrait size | Pavel's head occupies a different footprint; current job scales the authentic cropped source to width 700. Patrick uses width 590. These are per-input values, not a validated shared head-size rule. | Measurable crop/scale decision influenced by source anatomy/framing |
| Portrait crop | Current Pavel includes an arm/hand near the footer and different shoulder framing. Patrick is a large cutout extending behind the footer, unlike the existing circular card. | Source composition plus layout choice; not all differences are inevitable |
| Portrait edges | Pavel is soft/blocky with a dark edge around parts of the head; Patrick retains pale background fragments/halos around hair and a stepped shoulder contour. | Input quality and mask-processing defect, not a desirable template variation |
| Circle | Output bounds are fixed at 514/128–1060/674, but the exposed disc looks more prominent and less integrated. Reference boundaries are partly hidden, so exact original radius/center remain uncertain; portrait differences also change visible area. | Template plus occlusion by content |
| Gradients | Current background is flatter; disc uses a simple vertical gradient instead of the reference's brighter cyan glow and deeper fade; current cyan is more uniform. | Template |
| Attribution | Pavel divider/name/role are roughly 16/19/14 px higher than the normalized reference (output y≈500/523/556 vs reference ≈516/542/570). This follows the compressed quote block. Patrick's attribution is higher because its quote has four rather than five lines; the proportional spacing rule still needs review. | Pavel: typography-driven template drift; Patrick: content-responsive placement |
| Logo | Left anchor and width are close (~73, 166). Current top y=657 is about 6 px above Pavel reference, about 4 px below Kapil. Supplied master has different inter-line/wordmark proportions and more visible height. Preserve its authentic proportions rather than stretching to match. | Template placement plus source-master difference |
| Bottom cyan band | Slope is close: output top edge (0,781)→(940,664); Pavel reference approximately (0,783)→(940,669). Current right edge is about 5 px higher/thicker versus Pavel. Color/gradient remains visibly flatter. | Template |
| Overall balance | Pavel's shorter text block/higher attribution and soft grayscale portrait shift the hierarchy. Patrick's short quote leaves more lower-left whitespace, while the large cutout dominates the right. Sparse dots and flatter gradients make both outputs feel less layered than the approved references. | Mixed template and content/input effects |

Natural differences include pose, hairstyle, shoulder shape, clothing, grayscale versus color, and total quote length. Exact head scale, crop anchors, paragraph spacing, and mask artifacts should not be dismissed as unavoidable guest differences. They need either a reusable measurable rule or an improved input.

## Font evidence

Repository search found no established TSSE font files or brand-font declaration; the Arial references are from the new provisional implementation itself. The supplied Kapil PNG contains XMP `CreatorTool: Canva (Lightspeed Local)`, but no font family, weight or text-layer metadata. The Pavel PNG contains no font-identifying metadata. The logo is raster artwork with a color profile, not evidence of the quote font. The supplied transcript DOCX does not establish the graphic font.

Therefore the exact typeface and weight cannot be identified confidently from the available source evidence. Helpful additional material would be, in order:

1. A screenshot from the original Canva design with the quote text selected, showing font family, weight/style, size, line spacing and letter spacing.
2. The original Canva design link or a style/brand specification, if recoverable.
3. A PDF export with live embedded text/fonts (an outlined/rasterized PDF will not identify the font reliably).
4. The designer's font name/weight or legally usable font files.

Arial remains explicitly provisional. The long-profile reduction to 39 must not become a canonical brand measurement. Once the true font is established, recompute quote bounds and responsive attribution spacing before approving downstream geometry. No such recomputation or adjustment was made during this review.

## Portrait input quality

Pavel's working original is the 400 × 400 grayscale `pavel_prata.jpeg`, provisionally associated with the user's LinkedIn download. Current cutout is 384 × 341; scaling it to a 1400-pixel export width enlarges it roughly 3.6×. That is an input-resolution limitation. It is not sufficient for reference-like facial detail at the proposed 1880 × 1576 output. A higher-resolution authentic photo or lower intended display size is needed; generative reconstruction is not an acceptable remedy. The AI-recreated color portrait is not used in the output. The approved colored graphic is displayed only as historical design ground truth.

Patrick's source is the official photograph supplied by the user. Its 843 × 1064 original has much more detail, but the manual mask retains background contamination around hair. A refined matte from the original would improve that without altering his likeness. No mask changes were made for this review.

## Quote roles and next action

- Pavel remains `editorial_paraphrase` in metadata and is valid as a visual-testing fixture. It is not a verified direct guest quote.
- Patrick remains `verbatim`; the source excerpt and displayed text match after whitespace normalization, with an empty quote diff.

Wait for visual feedback. Then encode approved corrections as shared template rules or documented quote-length/portrait-framing rules, rerender both examples, rerun the complete suite, show the revised pair, and wait for explicit final approval. Only after that may Milestone 1 be completed and committed. No Drive delivery or Milestone 2 work is authorized by this review.
