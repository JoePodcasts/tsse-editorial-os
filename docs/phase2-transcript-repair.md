# Phase 2 Transcript Repair

## Summary

Phase 2 Episode Intelligence has been upgraded from metadata-inferred records to transcript-derived records.

- Phase 2 episodes repaired: 15
- Rendered transcripts retrieved: 15
- Retrieval success rate: 100%
- Static HTML shell replacements: 15 transcript text files now available
- Episode intelligence records updated: 15
- Total rendered transcript corpus size: 468,836 bytes

The repaired records are in `data/episodes/rank4/` for episodes 25, 26, 34, 50, 51, 53, 54, 55, 60, 63, 70, 73, 74, 75, and 79.

## Retrieval Method

Rendered transcripts were retrieved with `phase2_transcript_retrieval.mjs`, which extends the Episode 73 Playwright prototype into a Phase 2 batch retrieval pass.

The retriever:

- Launches Chromium through Playwright.
- Opens each `/transcript` SPA route.
- Waits for rendered body text containing `Gopi Rangan:`.
- Extracts transcript paragraphs from rendered `<p>` elements.
- Handles both timestamped and non-timestamped speaker labels.
- Stops before the Simplecast footer and cookie content.
- Saves plain-text transcript artifacts under `data/transcripts/`.
- Validates transcript size, speaker labels, host presence, and absence of HTML shell markers.

## Retrieval Validation

| Episode | Transcript File | Bytes | Paragraphs | Confidence |
|---|---|---:|---:|---|
| 25 | `x-factor_transcript.txt` | 33,464 | 103 | High |
| 26 | `chief-engineer_transcript.txt` | 31,810 | 119 | High |
| 34 | `commerce_transcript.txt` | 35,458 | 140 | High |
| 50 | `childhood-not-resume_transcript.txt` | 32,462 | 113 | High |
| 51 | `persuasive-fintech_transcript.txt` | 29,570 | 114 | High |
| 53 | `ubiquity_transcript.txt` | 38,243 | 127 | High |
| 54 | `homebrew_transcript.txt` | 31,423 | 109 | High |
| 55 | `look-where-others-are-not-looking_transcript.txt` | 23,657 | 81 | High |
| 60 | `prioritize-cash-team-and-momentum-in-that-order_transcript.txt` | 33,584 | 108 | High |
| 63 | `show-your-assumptions_transcript.txt` | 37,872 | 118 | High |
| 70 | `tsse70-cvcs-not-devil-patrick-counterpart_transcript.txt` | 30,917 | 69 | High |
| 73 | `tsse73-pre-revenue-startups-charles-precursor_transcript.txt` | 23,288 | 67 | High |
| 74 | `tsse74-business-with-gratitude-heather-humanvc_transcript.txt` | 27,442 | 69 | High |
| 75 | `tsse75-fintech-startup-ideas-dan-rosen-commercevc_transcript.txt` | 27,073 | 56 | High |
| 79 | `tsse79-sell-authentically-nuno-goncalves-chamaeleonvc_transcript.txt` | 32,573 | 64 | High |

All 15 retrieved files passed validation:

- File size greater than 10 KB.
- Host speaker label present.
- At least two speaker labels detected.
- No Vite SPA shell markers such as `<!DOCTYPE html>`, `<div id="app"></div>`, `polyfills-legacy`, or Simplecast asset-shell references.

## Intelligence Confidence

Overall confidence is high because every repaired record was derived from a full rendered transcript, not a title, URL slug, or static HTML shell.

Confidence by field:

- `primary_theme`: High. Derived from host framing plus recurring guest discussion.
- `secondary_themes`: High. Derived from repeated transcript topics and supporting examples.
- `founder_lessons`: High. Derived from explicit advice sections and guest examples.
- `industries`: High. Derived from named sectors, portfolio examples, and guest firm focus.
- `community_organizations`: High when a named organization was present; high-empty when the guest discussed community interests without naming a specific organization.
- `notable_quotes`: High. Selected as short transcript-faithful passages.

## Notable Changes from Metadata-Derived Records

| Episode | Metadata-Derived Version | Transcript-Derived Repair |
|---|---|---|
| 25 | Generic founder X-factor and founder-market fit. | Reframed around market conviction plus intellectual/physical horsepower, solo GP decision-making, applied data science, APIs, and creative liquidity. No named community organization was present. |
| 26 | Generic technical founder leadership. | Reframed around earliest-stage technical risk, VC as a service business, careful disclosure of proprietary technology, teaser decks, and public-market liquidity. |
| 34 | Incorrectly centered on e-commerce and consumer behavior. | Corrected to FinTech personal finance autopilot, insurance data portability, founder market fluency, and Moneythink. |
| 50 | Broad founder formation. | Repaired as mission-driven financial health investing, impact measurement, founder origin stories, and Compton Community Development Corporation / Compton Pledge. |
| 51 | Persuasion retained but under-specified. | Expanded to precision in complex FinTech markets, consumer emotional connection, data governance, founder-investor fit, and MASS MoCA. |
| 53 | Generic ubiquity and distribution. | Corrected to "software beyond the screen," technical fluency, customer demand signals, pitch clarity, and Astronomical Society of the Pacific. |
| 54 | Community-driven venture capital with a non-transcript "Homebrew Fund Community." | Repaired to mission-driven seed-phase company building, product-market fit, founder motivation, diverse check writers, and KIPP. |
| 55 | Generic contrarian market identification. | Repaired to large opportunity assessment, execution capacity, investment team diversity, and elder mentorship/education. No named nonprofit was present. |
| 60 | Cash/team/momentum was directionally correct. | Strengthened with transcript-specific lessons on customer discovery, CXO networks, recruiting, and India Literacy Project. |
| 63 | Generic assumptions and transparency. | Corrected to health investing with empathy, assumption testing, patient capital, healthcare-specific value curves, and GAIA Global Health / Global AIDS Interfaith Alliance. |
| 70 | Corporate VC theme was directionally correct. | Expanded to balanced syndicates, CVC community-building, internal narrative coaching for founders, Counter Club context, and UCSF pediatric heart research. |
| 73 | Pre-revenue/founder quality was directionally correct but had an invented community entry. | Repaired to pre-seed capital for product-market fit finding, product clarity, bridge funding, selection skill, and San Francisco-Marin Food Bank. |
| 74 | Human-centered VC was directionally correct but had an invented community entry. | Repaired to futurist founders, gratitude, venture studio support, rapid iteration, specialized healthcare examples, and David Lynch Foundation. |
| 75 | FinTech opportunity identification retained but generalized. | Repaired around founder journey, regulated-market complexity, outsider learning, strategic investor fit, embedded financial services, and diversity in venture. No named nonprofit was present. |
| 79 | Authentic communication retained but generalized. | Repaired around investor communication as dialogue, tech-augmented VC, product/technical diligence, authentic sales cadence, West to West, and Partnership for Children and Youth. |

## Files Updated

Transcript artifacts added:

- `data/transcripts/x-factor_transcript.txt`
- `data/transcripts/chief-engineer_transcript.txt`
- `data/transcripts/commerce_transcript.txt`
- `data/transcripts/childhood-not-resume_transcript.txt`
- `data/transcripts/persuasive-fintech_transcript.txt`
- `data/transcripts/ubiquity_transcript.txt`
- `data/transcripts/homebrew_transcript.txt`
- `data/transcripts/look-where-others-are-not-looking_transcript.txt`
- `data/transcripts/prioritize-cash-team-and-momentum-in-that-order_transcript.txt`
- `data/transcripts/show-your-assumptions_transcript.txt`
- `data/transcripts/tsse70-cvcs-not-devil-patrick-counterpart_transcript.txt`
- `data/transcripts/tsse73-pre-revenue-startups-charles-precursor_transcript.txt`
- `data/transcripts/tsse74-business-with-gratitude-heather-humanvc_transcript.txt`
- `data/transcripts/tsse75-fintech-startup-ideas-dan-rosen-commercevc_transcript.txt`
- `data/transcripts/tsse79-sell-authentically-nuno-goncalves-chamaeleonvc_transcript.txt`

Episode intelligence records repaired:

- `data/episodes/rank4/episode_25.json`
- `data/episodes/rank4/episode_26.json`
- `data/episodes/rank4/episode_34.json`
- `data/episodes/rank4/episode_50.json`
- `data/episodes/rank4/episode_51.json`
- `data/episodes/rank4/episode_53.json`
- `data/episodes/rank4/episode_54.json`
- `data/episodes/rank4/episode_55.json`
- `data/episodes/rank4/episode_60.json`
- `data/episodes/rank4/episode_63.json`
- `data/episodes/rank4/episode_70.json`
- `data/episodes/rank4/episode_73.json`
- `data/episodes/rank4/episode_74.json`
- `data/episodes/rank4/episode_75.json`
- `data/episodes/rank4/episode_79.json`

## Follow-Up

The Phase 2 records are now safe to treat as transcript-derived for downstream recommendation and newsletter workflows. A future cleanup pass can update older audit docs that still describe Phase 2 as shell-only, but those docs should remain useful as historical context for why this repair was necessary.
