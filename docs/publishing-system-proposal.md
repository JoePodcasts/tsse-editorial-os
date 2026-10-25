> Final status (2026-10-25): Milestone 1 approved and complete. See [closing implementation guide](quote-card-milestone-1.md). Pending-review statements below describe the historical review stage; source/editorial limitations remain recorded.

# TSSE publishing system: first-pass audit and proposal

## Approved collaboration principle — 2026-10-25

**Automate what is deterministic. Surface what requires judgment. Preserve human override. Record the decision.**

This applies to quote selection and paraphrase judgment, Connected Insights choices, Startup Corner
selection, official logo replacement, final card composition and newsletter editorial approval.
Automated verification supports human decisions; it does not imply permission to publish.
Portraits have an independent approval lifecycle; see [portrait asset lifecycle](portrait-asset-lifecycle.md).
The original audit below is historical. Milestone 1 remains pending final card approval.

Review date: 2026-10-24. Status: proposed, not an approved brand specification.

Extend `tsse-editorial-os`. Its existing intelligence, recommendations, history, and transcript pipeline are the right foundation. Add an asset-production layer beside those capabilities; do not create another repository or recommendation engine. Milestone 1 should be a local, deterministic quote-card workflow ending in a review package and explicit approval record. Drive delivery follows later.

This review adds documentation only. No production assets, source records, scripts, or repository structure have been changed. Existing untracked episode 192 material and output packages were left intact. Findings describe the local checkout, not a fresh audit of remote GitHub or Drive. No external sources or APIs were tested.

## 1. Observed architecture

The application consists of root-level Python command-line scripts, Node/Playwright transcript retrieval scripts, JSON/CSV/text datasets, Markdown documentation, and saved output packages. It has no checked-in dependency lockfile, executable test suite, CI workflow, brand assets, visual templates, or image renderer in the inspected tree.

| Layer | Existing implementation | Reuse and limitation |
| --- | --- | --- |
| Episode discovery | `episode_discovery.py` | Simplecast discovery and comparison with newsletter coverage; live service availability not verified in this review. |
| Transcript ingestion | `phase3_transcript_retrieval.mjs`, earlier retrieval scripts, `data/transcripts/` | Rendered text retrieval with validation; 56 TXT and 16 legacy HTML files. Retain transcript snapshots; HTML existence is not evidence of a usable transcript. |
| Episode intelligence | `episode_intelligence_generator.py`, `data/episodes/` | 54 Rank 4 records and 3 active records (190–192, including untracked 192). Structured themes, lessons, industries, organizations, and quote strings. |
| Connected Insights | `connected_insights_recommender_v3.py` | Existing theme/lesson/industry/community matching, frequency and recency scoring, rationale; keep this engine. Earlier versions also remain. |
| Startup Corner | `startup_recommender_v1.py`, 14 startup JSON records | Existing themes, aliases, source URLs, review notes, historical appearances, milestone and shared-investment evidence. No reusable logo registry. |
| Newsletter memory | `newsletter_archive_importer.py`, `newsletter_history.py`, CSV | 46 rows. Existing fields cover recurring modules, but the data is incomplete and often contains headlines instead of entity names. |
| Briefing assembly | `newsletter_briefing_generator_v1.py` | Local structured briefing and Markdown assembled from existing recommenders. |
| Production draft | `newsletter_production_pipeline_v1.py` | Cached/fresh transcript handling, intelligence creation, recommendations, JSON/Markdown briefing, newsletter draft. “Production” in its filename does not mean publish-ready. |
| Editorial policy | `docs/workflows.md`, `docs/sources.md`, architecture/data-model and evaluation documents | Valuable editorial requirements and review worksheets; not a central validated publishing configuration. |

The draft pipeline already separates Intro, Podcast Entries, Connected Insights, Startup Corner, and Community Involvement at the heading level. However, it selects the first recommendation to populate a draft, leaves URL placeholders, and emits generic intro copy in third person. It does not implement Gopi's final voice, independent module contracts, approved quote selection, image generation, or delivery.

Community extraction is heuristic organization detection, not a maintained organization/update/asset workflow. YouTube descriptions, chapters, keywords, Shorts, social packages, and the requested visual production system are not implemented as dedicated workflows in this tree.

### Checks performed

Parsed and inventoried episode/startup JSON and CSV files; inspected current orchestration, both active recommenders, transcript parsers, representative records/output packages, architecture and historical validation documentation. Ran current transcript validation and recommendation functions without writing outputs for episodes 75 and 179. Both cached transcripts passed; each produced three Connected Insights and three startup candidates. Episode 75's Connected Insights leaders were episodes 34, 106, and 51; episode 179's were 135, 136, and 175. These are smoke checks, not editorial endorsement or fresh-source verification.

## 2. Technical debt and expansion risks

1. **Quote provenance is insufficient for publication.** `notable_quotes` contains strings without passage locators, speaker evidence, classification, source hashes, or approval records. The generator strips timestamps; `guest_sentences()` can fall back to other non-host speakers if the requested guest does not match. Do not feed these strings directly into attributed graphics. Add evidence at the quote selection boundary; refuse unverified direct attribution.
2. **History quality affects recommendations and discovery.** All 46 rows lack publication dates and central themes; 28 lack featured episode numbers. A missing match is sometimes treated as “fresh.” Discovery cannot reliably equate missing coverage with never published. Preserve raw history, add reviewed entity/episode links and explicit unknown status incrementally.
3. **Duplicated historical usage can drift.** Startup appearance history is copied into startup records; `appearance_stats()` reads that copy while the recommender also loads newsletter history. Establish history as the canonical usage source and reconcile copied values before relying on them for publishing decisions.
4. **Rank eligibility is largely structural.** v3 reads the Rank 4 directory and does not independently reject arbitrary supplied candidate records by rank. Existing 54 records have `guest_rank`; validate eligibility at the adapter boundary. The rankings file is tab-delimited despite its `.csv` extension and contains 178 numbered rows plus a malformed summary row. Use a deliberate parser and reject the trailing summary from entity imports.
5. **Duplicated code and stale documentation.** Recommender v1/v2/v3 coexist; extraction/briefing logic exists in multiple scripts; old static ingestion accepts HTML that can be an SPA shell. `docs/codex-handoff.md` describes a blocker that later work addressed, and README documents only early entry points. Document active entry points and mark historical implementations before targeted consolidation. Do not delete historical code in this first pass.
6. **Reproducibility is incomplete.** Playwright is dynamically located, including a bundled-runtime fallback; there is no locked project toolchain. Existing outputs mix examples, validation runs, and active drafts. New builds need pinned tools, explicit input manifests, immutable run directories, and a retention policy.
7. **Validation reports are not enforced gates.** Existing Markdown checks and editorial worksheets are useful evidence, but do not replace executable tests or approval enforcement. Milestone scoring recognizes evidence status without ensuring a development is recent. Existing “review required” labels must not become implicit publishing permission.

Before Milestone 1, address only the new workflow's input contracts, toolchain, quote provenance, and approval gate. The history reconciliation and legacy consolidation can be incremental; neither should block an isolated quote-card renderer.

## 3. Reference graphics: measured facts and visual estimates

The supplied graphics are approved examples according to the brief. That establishes their role as references, not the provenance or verbatim accuracy of their printed quotations.

| Reference | Pixel dimensions | Mode | Width/height |
| --- | --- | --- | --- |
| Kapil | 940 × 788 | RGBA | 1.192893 |
| Pavel | 1370 × 1148 | RGB | 1.193380 |

The ratios differ by approximately 0.041%. Scaling Pavel to 940 pixels wide gives a height of 787.68 pixels. This is consistent with differently sized exports of one layout, but does not prove the original master dimensions. Confirm the intended production size before freezing a template.

Reference SHA-256:

- Kapil: `4f49ad5374c233d542df9e2cab9006dee817ac735d65714984b5d1c888341683`
- Pavel: `818146a2d7728a7bb2c966fe73195879ab8929a5da6e4ceb521e8e016fb45353`

The following coordinates are **approximate visible bounds**, read from the supplied raster images, not original design-layer measurements. Origin is top left; use them to reconstruct and review a candidate template, not as already-approved constants.

| Element | Kapil pixels | Pavel pixels | Interpretation |
| --- | --- | --- | --- |
| Left text edge | x ≈ 73 | x ≈ 107 | About 7.8% of width |
| Oversized quotation marks | x ≈ 70–169, y ≈ 56–129 | x ≈ 105–246, y ≈ 81–187 | Fixed cyan opening ornament |
| Thin top rule | x ≈ 191–498, y ≈ 95 | x ≈ 278–727, y ≈ 139 | Nearly identical normalized anchor and length |
| Quote region, visible ink | x ≈ 72–478, y ≈ 167–465 | x ≈ 106–746, y ≈ 240–713 | Top aligned near 21% height; variable lower extent |
| Attribution divider | x ≈ 74–122, y ≈ 499–504 | x ≈ 107–178, y ≈ 752–759 | Moves with quote length |
| Name, visible ink | y ≈ 525–545 | y ≈ 790–818 | Uppercase cyan |
| Role/company | y ≈ 558–599 | y ≈ 831–889 | Two white lines in each supplied example |
| TSSE logo | x ≈ 73–239, y ≈ 653–713 | x ≈ 107–348, y ≈ 966–1054 | Similar normalized width; vertical anchor differs slightly |
| Portrait visible top | y ≈ 101 | y ≈ 171 | Photo-specific scale and crop, not a single fixed bounding box |
| Footer upper edge | (0, ≈781) to (940, ≈664) | (0, ≈1141) to (1370, ≈975) | Cyan diagonal covers portrait base; similar slope |

Portraits occupy the right side, overlap the circular background and dot decoration, and extend behind the footer. Their visible left silhouette begins near x ≈ 480 at Kapil's lower body and x ≈ 590 at Pavel's lower body. Hair and shoulder edges indicate isolated subjects; the removal technique and original photo extent cannot be determined from these exports. Preserve approved original portraits and their separate masks; do not extract a portrait from a finished reference as the master source.

The circle's visible upper edge is approximately (780, 128) for Kapil and (1130, 185) for Pavel. Both suggest a broad blue/cyan disc behind the right portrait. Much of its boundary is obscured, so center, radius and gradient parameters remain estimates. The cyan dot field curves around the upper/right portrait area, with a fading lower/outer extent; apparent grid spacing is roughly 15 pixels in Kapil and 21–22 pixels in Pavel. Exact pattern, opacity mask, and layering need the original template or an approved reconstruction.

Kapil uses five large quote lines with no cyan emphasis. Pavel uses four initial white lines, a paragraph gap, then three lines with “Only founders can tell you” in cyan across a line break. Relative to canvas width, Pavel's type is smaller. Approximate line spacing is 63 pixels versus 67 pixels in the native exports (Pavel ≈46 pixels at Kapil scale). This supports controlled short/long profiles; it does not justify unconstrained shrinking or arbitrary reflow.

Typeface identity, font weight, font size, tracking, and line-height cannot be established exactly from flattened images. Visible quote lettering is a bold sans serif; attribution is smaller sans serif. The TSSE wordmark is artwork, not ordinary replacement text. Request fonts and original logo rather than asserting a font match.

Pixel samples establish a textured/gradient palette, not authoritative flat brand colors. Kapil's top-left pixel is `#002436`, with a frequent background value `#002235`; Pavel's top-left pixel is `#03283B`, with a frequent background value `#012539`. Near the bottom center the samples are `#5DE1FF` and `#5DDFFD`. White quote text and cyan accents coexist with antialiasing and tonal variations. Brand hex values and exact gradients remain unconfirmed. Do not promote sampled colors into official brand tokens without review.

## 4. Proposed additive architecture

Keep all existing datasets and entry points. Add only when implementation is approved:

```text
publishing/                    # validation, naming, rendering, review-package CLI
publishing/templates/quote-card/v1/
                              # fixed artwork, layout tokens, approved fonts/references
schemas/publishing/           # versioned input, asset, quote and approval contracts
config/publishing/            # naming and reviewed editorial/brand rules
data/assets/manifest.json     # shared asset registry
data/publishing/              # quote jobs, source/claim records, approval receipts
outputs/quote_cards/           # ignored run builds and previews
tests/publishing/             # tests and selected golden fixtures
```

Names are proposals. The two existing episode directories remain authoritative; a small read-only adapter resolves episode IDs from them and detects conflicting records rather than copying the corpus. Publishing jobs reference episode records. Do not modify legacy recommender contracts merely to add imagery.

Use one Python orchestration layer and one pinned local browser renderer, building on the repository's existing Playwright experience. Fixed SVG artwork plus local HTML/CSS text provides measurable geometry and font rendering. Choose the exact renderer versions during implementation and lock browser, fonts, dependencies, viewport, device scale, color handling, and export settings. No live network fonts or assets during rendering. Background removal is a separate preparation step: use an approved transparent portrait/mask for deterministic rendering; retain any manually cleaned mask as a versioned input.

For each quote, resolve and hash inputs, validate identity and evidence, select an approved layout profile, render, check geometry, and write a review package. The renderer must use real text metrics. Approved explicit line breaks and emphasis ranges are metadata. If neither approved short nor long profile fits, fail with an editor-readable explanation; do not truncate, rewrite, shrink below limits, move the logo, or cover the face. Freeze decoration and footer geometry per template version. Store photo-specific crop/scale/anchor values and check a face-safe region.

## 5. Metadata, provenance, and approval

Extend through linked records rather than embedding every field in existing episode JSON.

| Record | Required proposed information |
| --- | --- |
| Source | Stable ID; kind; actual URL or supplied-file provenance; snapshot path/Drive ID; retrieval date when known; SHA-256; source status; rights/usage notes where supplied |
| Asset | Stable ID/version; organization or guest ID; type; source ID; original and derivative hashes; filename; dimensions; MIME type; alpha validation; transformation/mask recipe; current approval status; local/Drive locations |
| Quote | ID; episode and speaker; exact source excerpt; transcript hash and passage offsets/timestamp; displayed text; classification; editorial changes and rationale; emphasis ranges; quote approval |
| Render job | Schema version; episode record reference/hash; quote and portrait IDs; approved attribution; template/font/artwork hashes; layout profile; crop; line breaks; quote number; code revision and working-tree patch/hash; toolchain digest |
| Review/release | Run ID; input/output/validation-report hashes; preview; reviewer identity and time; decision; unresolved warnings; delivery receipt and destination version |

Quote classification is one of `verbatim`, `lightly_cleaned`, `editorial_paraphrase`, or `promotional_copy`. Verbatim requires a matching source passage and speaker, with narrowly documented normalization only. Cleaned quotations retain the original excerpt and a reviewable diff. Paraphrases and promotional text must not silently receive direct-quotation marks/attribution: require an approved alternative presentation or block them in this direct-quote template. Existing quote strings start as unverified candidates.

Proposed lifecycle: draft → generated → validated → in review → approved → delivered. Rejection returns work to draft. Approval binds to exact input, template, output and validation hashes; any change invalidates it. A successful render is never approval. CLI cannot self-approve as a side effect of generation. The publishing gate verifies a recorded human decision and all blocking checks. The current brief authorizes the proposal, not production delivery.

## 6. GitHub and Google Drive asset policy

Git stores rules, schemas, template code, small approved brand components, source text where appropriate, manifests, provenance, review decisions, and a small curated set of golden reference images. Keep high-resolution originals, reusable production images and final distribution assets in Drive when that suits existing collaboration. Record Drive file IDs and exact content hashes; a mutable URL alone cannot reproduce a build. Preserve an immutable retrievable copy of every input version needed by retained releases. Consider Git LFS only if the actual binary volume warrants it.

Generated previews, browser files, caches and routine PNG builds should be ignored. Keep intentionally selected outputs through explicit release records; do not purge the existing `outputs/` tree during this milestone. Define later which historical packages are examples versus disposable builds.

Use a single asset manifest and lookup service for company and community logos, keyed by canonical entity ID and asset role. Look up the currently approved asset before retrieval; deduplicate by hash, but do not merge distinct brands solely because names resemble one another. Usage records link assets to issues/modules/releases. Record known missing provenance as unknown; do not invent official URLs for imported Drive assets.

Preserve the existing Startup Corner filename `[Startupname] logo without bg.png`. Proposed Community Involvement equivalent: `[Organizationname] logo without bg.png`. Canonical display names come from reviewed entity records. If duplicate names require disambiguation, resolve the convention explicitly rather than silently adding suffixes. Quote naming is exactly `TSSE[episode number] [guest name] quote [number].png`; derive it from structured fields, including approved capitalization and filesystem-safe validation.

Drive folder IDs, current library organization, sharing policy and destination permissions remain unknown. Do not invent or create them. Later delivery should reuse the existing library and designated review/production locations. Where updating a file ID is needed to preserve links, first verify expected prior content/version, preserve the old bytes and receipt, upload only the approved hash, and verify the resulting file. Confirm the chosen Drive API/connector supports the required content update and concurrency checks before implementation; do not promise preserved IDs through an unsupported operation.

## 7. Validation and tests

Separate automated blocking checks, review warnings, and human decisions. Produce readable failures such as “Quote does not match the selected guest's transcript passage” or “Portrait file changed after approval.”

| Area | Automated checks | Human checks |
| --- | --- | --- |
| Identity/evidence | Episode lookup; source and asset IDs/hashes; passage and speaker match; required classification and attribution | Correct guest photo, quote context, spelling, approved title/company and editorial wording |
| Layout | Canvas/ratio; font load and font hashes; text bounds; line count; safe regions; crop geometry; logo/decorative layer presence and coordinates; palette/token version | Portrait edge quality, emphasis, balance, authentic appearance, exact brand fidelity |
| File/release | Programmatic filename; valid PNG; input references; reproducibility manifest; approval hash binding; no production writes without approval | Final visual approval and destination choice |
| Logos (later shared workflow) | Format; real alpha variation and transparent border regions; dimensions; aspect ratio versus approved original; naming/provenance; duplicate detection | Correct official mark and entity, no damaging removal of white logo details, no accidental white box or distortion |

An RGBA mode alone is not proof of transparency. Automated background heuristics can flag suspicious opaque corners; they cannot certify the correct official logo. Preserve proportions by uniform scaling; set minimum resolution from actual intended display dimensions, rather than inventing a threshold now.

Milestone 1 tests: both approved quote-length profiles, mixed emphasis across line breaks, long names/titles, Unicode and punctuation, overlong quote rejection, missing/font-substituted asset failure, wrong guest/episode, quote mismatch, stale source hash, changed file after approval, and publishing refusal without approval. Include text bounds and region-specific pixel regressions for decorations/logo/footer. Golden images must be human-approved, never automatically updated on failure. Same pinned environment and inputs should reproduce identical pixels; separate variable timestamps from rendered content. Test byte hashes too once PNG metadata is controlled.

## 8. Phases and acceptance gates

1. **Architecture and source-asset confirmation (this review).** Agree the additive boundary, canonical export size, source assets and approval responsibilities. No broad restructure.
2. **Milestone 1: reliable quote cards.** Lock the design with short and long reference reconstructions, build structured input and source verification, renderer, validation, preview, manifest and explicit approval record. Exit only when the editor approves visual fidelity, both profiles reproduce consistently, overflow and provenance failures stop the workflow, and changed assets invalidate approval. No Drive publishing is necessary to demonstrate this milestone.
3. **Shared asset library.** Read-only inventory/reconcile existing Drive logos, establish entity IDs, provenance and current approval versions; implement one logo validator. Wire Startup Corner and Community Involvement to the same workflow.
4. **Episode materials and newsletter module contracts.** Centralize existing guidelines, add titles/descriptions/chapters/keywords and approved source claims. Give each newsletter module its own inputs, required fields, asset references and review state. Reuse v3 Connected Insights with passage-level quote evidence; improve history reconciliation. Assemble only reviewed modules; unresolved links/placeholders fail readiness.
5. **Shorts and social.** Add transcript time ranges, editorial selections, titles/descriptions, media references and platform-specific validations after source contracts are reliable.
6. **Drive delivery/synchronization.** Validate connector capabilities, implement explicitly approved delivery, stable-ID updates where supported, conflict checks, receipts and recovery. Introduce automated CI checks with Milestone 1 and extend them throughout; do not postpone validation until synchronization.

Module contracts should distinguish inputs from final copy: Email Intro needs an approved current observation/engagement and Gopi-voice rules; Podcast Entry needs episode/title/framing/takeaways/CTA and quote asset; Connected Insights needs current theme, previous episode, passage, connection explanation and visual; Startup Corner needs sourced development and shared logo; Community Involvement needs sourced organization/program/event and shared visual; optional Upcoming Events needs verified date/time/URL. Missing personal experiences or current facts remain missing rather than being generated.

## 9. Needed before faithful rendering

- Original editable design or clean fixed background/decorations export, if available; otherwise review and approve a measured reconstruction.
- Exact font families, weights and usable font files, plus any existing brand specification. Font identity is currently unknown.
- Approved TSSE logo master (preferably vector or high-resolution transparent artwork).
- Original approved Kapil and Pavel portraits, ideally transparent cutouts plus originals; provenance and any existing crop/mask information.
- Confirm canonical export dimensions and acceptable short/long layout profiles; provide additional examples if there are other approved variants.
- Verified episode number for Kapil; the Pavel filename indicates 196 but neither attached reference establishes transcript provenance. Supply source transcripts/passages and classification/approval for both printed quotes before using them as publication fixtures.
- Existing editorial guidelines beyond repository documents, and the intended human approver(s). Current repository documentation names Joe and Gopi, with final approval by Gopi; confirm applicability to visual releases.
- Later: link/ID for the existing Drive logo library and designated distribution destinations. These are not prerequisites for a local quote-card prototype.

The missing master assets limit exact reconstruction, not architectural planning. Do not use generative portrait recreation, invented font names, guessed source URLs, or an approximate template presented as canonical to bridge those gaps.
