# TSSE quote cards — Milestone 1 complete

Final human approval received 2026-10-25. The canonical template, complete-card appearance,
implementation architecture and human review workflow are approved. The receipt is
`publishing/templates/quote-card/v1/approval.json`; it binds approval to the reviewed PNG hashes.
This milestone is local only. No Google Drive delivery, production publishing or Milestone 2 work.

## Approved implementation

- Deterministic PNG rendering at 1880 × 1576 using vendored, licensed Source Sans Pro.
- Measured short/medium/long layout modes with explicit human override and overflow checks.
- Canonical decoration, localized glows, dots and footer; authentic logo preserved without distortion.
- Independent portrait lifecycle: source, versioned candidate, human decision, approved reusable master.
- Local segmentation, alpha matting and foreground recovery, with supplied-transparent assets as an
  equally supported human option. Approved masters are reused without reprocessing.
- Transcript/source hashes, speaker/wording validation, explicit editorial-paraphrase classification,
  immutable review packages and explicit final human decisions.

The governing principle is **Automate what is deterministic. Surface what requires judgment.
Preserve human override. Record the decision.**

## Setup and checks

Use Python 3.12. Rendering alone requires `publishing/requirements.txt`. The complete suite,
including portrait processing, uses the isolated environment:

```sh
python3.12 -m venv .venv-portraits
.venv-portraits/bin/python -m pip install -r publishing/portraits/requirements.lock
.venv-portraits/bin/python -m unittest discover -s tests/publishing -v
```

The full suite has 41 tests. Model weights and authentic guest photographs remain local, outside
Git. The ONNX download source and checksum are in `publishing/portraits/model.json`.
No model is needed to render with an approved master or run synthetic unit tests.

## Workflow

1. Obtain an authentic photograph or officially supplied transparent PNG and retain provenance.
2. Process only if needed; register a versioned candidate and inspect light/dark/TSSE backgrounds.
3. Record the human decision using the independent portrait lifecycle. Never treat technical
   validity as visual approval. Preserve rejected candidates and replacement relationships.
4. Prepare an input matching `schemas/publishing/quote-card.schema.json`, including the explicit
   approved portrait candidate, source/master hashes, fonts and transcript evidence.
5. Render, verify, inspect the complete card and record explicit human approval of that run.

```sh
.venv-portraits/bin/python -m publishing.quote_card render /path/to/input.json --out /path/to/new-run
.venv-portraits/bin/python -m publishing.quote_card verify /path/to/new-run
.venv-portraits/bin/python -m publishing.quote_card approve /path/to/new-run --decision /path/to/human-decision.json
```

A human decision contains `run_id`, `decision: approved`, and `reviewer`. Approval refuses unresolved
source/editorial blockers. Do not generate approvals without authorization. Hashes detect drift;
this local audit trail is not an authentication system against someone controlling the filesystem.

`prepare_examples.py` is a historical polygon-preparation utility from the initial investigation,
not the approved portrait workflow. Use `portrait.py` and `portrait_assets.py` for new assets.

## Approved examples and boundaries

The closing metadata-only renders are in `outputs/quote_cards/patrick-milestone-1/` and
`outputs/quote_cards/pavel-milestone-1/`. Their PNGs match the approved final-review PNGs byte-for-byte.
Patrick has an approved complete-card receipt and verified transcript wording. Pavel has a visual
fixture approval and retains `editorial_paraphrase`; his public website source remains unresolved.
His visual approval does not authorize presenting editorial copy as a verified direct quote.
Those content limitations do not prevent completion of the implementation milestone.

Approved portrait sources and decisions remain in `data/publishing/local/portrait-library/`.
Pavel's 400 × 400 source softness is recorded; Patrick's remaining curls were accepted. Future
inadequate sources should be replaced with better authentic photographs, not reconstructed.

See [final template rules](quote-card-final-template.md), [portrait lifecycle](portrait-asset-lifecycle.md)
and [portrait processing](portrait-processing.md). Earlier calibration/review documents are retained
as historical evidence; their pending statuses are superseded by the final approval receipt.
