> Final status (2026-10-25): Milestone 1 approved and complete. See [closing implementation guide](quote-card-milestone-1.md). Pending-review statements below describe the historical review stage; source/editorial limitations remain recorded.

# Independent portrait asset lifecycle

Approved architectural principle: **Automate what is deterministic. Surface what requires judgment.
Preserve human override. Record the decision.**

`source → processed or supplied candidate → portrait_requires_review → human decision`

Decisions: `approve`, `try_another_approach`, `use_another_source`,
`provide_transparent_portrait`, or `reject`. Only approval creates an `approved_master` review
receipt. Other decisions retain the original candidate; another processing attempt or source
becomes a new ID linked through `parent_candidate`. A new candidate is never implicitly approved.

## Model

Each candidate directory contains:

- `candidate.json`: guest, candidate ID, creation timestamp, source path/provenance, origin kind,
  processing run where applicable, predecessor, source-quality limitations and file hashes.
- `source.*`: preserved authentic input file.
- `master.png`: reusable, full-size transparent master, copied without reprocessing.
- `validation.json`: technical checks and warnings; always requires visual review.
- `processing.json` and `processing-report.json`: snapshots for algorithmically processed assets.
- `review.json`: explicit reviewer, authorization evidence, decision, recorded timestamp, notes
  and the exact candidate hash. Written once; never silently replaced.

State is derived from immutable candidate plus separate review receipt. The initial candidate
record remains `portrait_requires_review` as history; an approving receipt yields `approved_master`.
`current.json` is an explicit per-guest selection index, not a latest-file heuristic. Selecting a
replacement preserves previous approvals. Downstream jobs pin the selected candidate version.

Supplied transparent portraits are first-class candidates: use `supplied_transparent`, provide
source provenance, and skip automated segmentation. They receive PNG/alpha/dimension checks and
human review like any other candidate; they do not claim an algorithmic processing history.
Technical checks cannot determine natural hair, flattering composition, identity or final visual fit.

## CLI

```sh
# Human-supplied transparent candidate (no segmentation dependency required):
python -m publishing.portrait_assets register --root /path/to/portrait-library \
  --id guest-transparent-01 --guest 'Guest Name' --source /path/to/source.png \
  --master /path/to/transparent.png --provenance 'Official source URL or documented origin'
# For a processed candidate, add --kind algorithmically_processed --processing-run /path/to/run.
# For a replacement, add --parent /path/to/previous/candidate.json.
# Add source limitations using --limitation 'Description'.
python -m publishing.portrait_assets decide /path/to/candidate.json \
  --decision approve --reviewer 'Human reviewer' --evidence 'Explicit authorization reference' \
  --note 'Visual review notes'
python -m publishing.portrait_assets select-current /path/to/candidate.json
```

Never generate a review decision without human authorization. These commands record decisions;
they do not authenticate the human. Local file hashes detect accidental drift, not malicious edits
by someone controlling the entire filesystem.

## Renderer contract

`portrait.approval_candidate` pins an approved candidate. Validation requires the guest, master
hash and source hash to match its approval. Merely setting `status: approved` on a file is insufficient.
Candidate and review receipt are included in card dependencies. Reuse verifies approved asset files,
not the original inference runtime or current model: no segmentation is needed for a new graphic.
The processing evidence snapshot remains with the asset for traceability.

The renderer crops to alpha bounds in memory, then applies the existing portrait region sizing.
This is a shared downstream fitting rule; the transparent master is never cropped or overwritten.
Original portrait positioning values and typography/decorative rules remain unchanged in this review.

## Current approvals and complete-card review

On 2026-10-25 the user authorized integration of Patrick's improved master and Pavel's authentic
400 × 400 grayscale master with its source-quality limitation. Receipts and assets are stored in
`data/publishing/local/portrait-library/{patrick,pavel}-candidate-01/`. Source URLs/provenance are
retained. Pavel must not be sharpened or reconstructed to invent missing detail; future inadequate
sources should be replaced with better authentic photographs. Patrick's remaining curls were
accepted without manual painting.

New jobs: `data/publishing/local/{patrick,pavel}-approved-master.json`.
Rendered runs: `outputs/quote_cards/{patrick,pavel}-complete-review/`.
Comparisons: `outputs/quote_cards/complete-review/`.
Both source masters were reused byte-for-byte, without running portrait processing.

Pavel's wording remains `editorial_paraphrase`; portrait approval does not approve direct-quote
publication. Patrick remains the verified transcript-quote example. Complete-card visual approval
and the final Milestone 1 implementation commit remain pending.
