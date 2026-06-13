# Episode Intelligence Phase 3

## Summary

Phase 3 expanded the Rank 4 Episode Intelligence Dataset from 25 completed records to all 54 Rank 4 records.

- Total Rank 4 guests in `data/guest_rankings.csv`: 54
- Previously completed transcript-derived records: 25
- Newly completed Phase 3 records: 29
- Total completed Rank 4 records after Phase 3: 54
- Failed or skipped episodes: 0
- URL-bearing Phase 3 transcripts attempted: 29
- URL-bearing Phase 3 transcripts retrieved: 29
- URL-bearing Phase 3 retrieval success rate: 100%
- Overall Rank 4 intelligence completion rate: 54 of 54 records, or 100%

Episode 179, Steve Kim, was completed after the transcript source was supplied and the missing `data/guest_rankings.csv` URL was backfilled.

## Retrieval Method

Phase 3 used the Playwright rendered-transcript approach in `phase3_transcript_retrieval.mjs`.

The retriever:

- Reads Rank 4 targets from `data/guest_rankings.csv`.
- Skips Rank 4 episodes that already have records in `data/episodes/rank4/`.
- Derives transcript URLs by appending `/transcript` to the episode URL.
- Launches Chromium through Playwright.
- Waits for rendered paragraph content with speaker labels.
- Extracts transcript paragraphs from rendered `<p>` elements.
- Saves plain-text transcripts under `data/transcripts/`.
- Validates transcript size, speaker labels, and absence of SPA shell markers.

The first retrieval pass used the Phase 2 host-specific wait condition and saved eight transcripts. Episodes 106 and 113 timed out because their rendered transcript labels use shortened speaker names (`Gopi:` / `Ryan:` and `Gopi:` / `Alex:`). The retriever was patched to wait for any rendered speaker-labeled transcript paragraph, while preserving shell and speaker validation. The resumed pass retrieved all remaining URL-bearing Phase 3 transcripts.

## Newly Completed Records

| Episode | Guest | Transcript File | Status |
|---:|---|---|---|
| 81 | Matt Harris | `tsse81-competition-is-irrelevant-matth-bcv_transcript.txt` | Complete |
| 83 | Mark Suster | `tsse83-relationship-before-fundraising-msuster-upfrontvc_transcript.txt` | Complete |
| 93 | Jake Gibson | `tsse93-fintech-better-tomorrow_transcript.txt` | Complete |
| 100 | Guy Kawasaki | `tsse100-listen-to-remarkable-people-guy-kawasaki_transcript.txt` | Complete |
| 105 | Semil Shah | `tsse105-no-fundraising-future-semil-shah_transcript.txt` | Complete |
| 106 | Ryan Falvey | `tsse106-fintech-startups-innovate-ryan-falvey_transcript.txt` | Complete |
| 107 | Karthee Madasamy | `tsse107-deep-tech-startups-karthee-madasamy_transcript.txt` | Complete |
| 110 | David Thacker | `tsse110-grow-responsibly-david-thacker_transcript.txt` | Complete |
| 111 | Manu Kumar | `tsse111-contact-with-investors-manu-kumar_transcript.txt` | Complete |
| 113 | Alex Edelson | `tsse-113-strategies-around-you-alex-edelson_transcript.txt` | Complete |
| 117 | David Gritz | `tsse117-future-of-insurance-bryan-falchuk-david-gritz_transcript.txt` | Complete |
| 121 | David York | `tsse121-no-means-not-now-david-york-top-tier_transcript.txt` | Complete |
| 122 | Oren Zeev | `tsse122-vcs-catch-liars-oren-zeev_transcript.txt` | Complete |
| 124 | Eric Ver Ploeg | `tsse124-category-defining-companies-eric-ver-ploeg_transcript.txt` | Complete |
| 128 | Aram Verdiyan | `tsse-128-concentrated-investments-aram-verdiyan_transcript.txt` | Complete |
| 129 | Miles Dieffenbach | `tsse129-vc-generates-alpha-miles-dieffenbach_transcript.txt` | Complete |
| 135 | Aakar Vachhani | `tsse135-path-to-success-aakar-vachhani_transcript.txt` | Complete |
| 136 | Eric Sippel | `tsse-136-concentrated-portfolios-win-eric-sippel_transcript.txt` | Complete |
| 144 | Dan Kimerling | `tsse144-courageous-entrepreneurs-dan-kimerling_transcript.txt` | Complete |
| 153 | Jessie Guo | `tsse153-use-your-superpowers-jessie-guo_transcript.txt` | Complete |
| 158 | Pablo Srugo | `tsse158-early-believers-pablo-srugo_transcript.txt` | Complete |
| 167 | Geoff Ralston | `tsse167-safer-ai-future-geoff-ralston_transcript.txt` | Complete |
| 169 | Dave McClure | `tsse169-secondaries-are-essential-dave-mcclure_transcript.txt` | Complete |
| 172 | Zach Noorani | `tsse-172-dont-ditch-the-pitch-deck-zach-noorani_transcript.txt` | Complete |
| 173 | Bhaskar Ghosh | `tsse-173-intentional-networking-bhaskar-ghosh_transcript.txt` | Complete |
| 174 | Tim Guleri | `tsse174-dont-overstretch-funding-tim-guleri_transcript.txt` | Complete |
| 175 | Maryam Haque | `tsse175-venture-capital-positive-power-maryam-haque_transcript.txt` | Complete |
| 176 | Adam Draper | `tsse176-the-quirky-underdog-adam-draper_transcript.txt` | Complete |
| 179 | Steve Kim | `tsse179-start-early-stay-consistent-steve-kim_transcript.txt` | Complete |

## Failed or Skipped

| Episode | Guest | Reason | Action |
|---:|---|---|---|
| None | None | None | All Rank 4 episode intelligence records are complete. |

## Validation Results

Phase 3 validation passed.

- All 29 new JSON files parse successfully.
- All 29 completed Phase 3 records contain the required schema fields.
- All Phase 3 `notable_quotes` appear verbatim in the retrieved transcript files.
- All 29 retrieved transcript files are larger than 10 KB.
- No Phase 3 transcript file contains SPA shell markers such as `<!DOCTYPE html>`, `<div id="app"></div>`, `polyfills-legacy`, or Simplecast shell asset references.
- All 54 JSON files currently in `data/episodes/rank4/` parse successfully.

The stricter Phase 3 validation was scoped to newly created Phase 3 records and transcripts. Episode 179 now passes transcript retrieval, schema, JSON parse, shell-marker, and quote-verbatim validation.
