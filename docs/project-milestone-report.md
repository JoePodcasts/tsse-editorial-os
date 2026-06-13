# Project Milestone Report

## Current Project State

TSSE Editorial OS is ready to enter the recommendation-engine phase with a substantially complete Rank 4 episode intelligence base.

The most important milestone is that Rank 4 episode intelligence is no longer metadata-inferred. The dataset now contains all 54 Rank 4 intelligence records, and the Phase 2 and Phase 3 records were built from rendered transcript text retrieved through Playwright.

Current state:

- Guest ranking data exists in `data/guest_rankings.csv`.
- Newsletter history exists in `data/newsletter_history.csv`.
- Rank 4 episode intelligence records exist in `data/episodes/rank4/`.
- Rendered plain-text transcripts exist in `data/transcripts/`.
- Connected Insights recommendation prototypes exist in `connected_insights_recommender.py` and `connected_insights_recommender_v2.py`.
- Startup Corner recommendation logic is specified in `docs/startup-recommendation-engine.md`, but no executable startup recommender exists yet.

The repository is in a strong state for recommendation work, but the recommendation phase should begin with data cleanup and validation rather than weight tuning alone.

## Dataset Inventory

### Guest Rankings

Source: `data/guest_rankings.csv`

- Total rows: 179
- Rank 4 guests: 54
- Rank 1 guests: 124
- Malformed trailing row: 1 row with only `GUEST RANK = 54`
- Duplicate guest names noted in prior summary:
  - Scott Barclay appears twice.
  - Geoff Ralston appears twice.
- Rank 4 missing URLs: 0

The Rank 4 set is the authoritative Connected Insights eligibility pool. Episode 179 is now complete after the Steve Kim episode URL was added.

### Newsletter History

Source: `data/newsletter_history.csv`

- Total parsed newsletter issues: 45
- Issue range: 31 through 75
- Unique Connected Insights values: 44
- Unique Startup Corner company values: 26
- Unique Community Involvement organization values: 36

Missing field counts:

| Field | Missing Count |
|---|---:|
| `issue_number` | 0 |
| `featured_episode` | 27 |
| `featured_guest` | 26 |
| `connected_insight_guest` | 0 |
| `startup_corner_company` | 3 |
| `community_organization` | 7 |
| `publication_date` | 45 |
| `central_theme` | 45 |

Important limitation: `connected_insight_guest` often stores a section title rather than a normalized guest name. This makes historical exact-match validation unreliable until Connected Insights labels are normalized.

### Episode Intelligence

Source: `data/episodes/rank4/`

- Rank 4 guests: 54
- Completed intelligence records: 54
- Missing intelligence records: 0
- Completion rate: 100%
- Records with all required schema fields: 54
- JSON parse errors: 0
- Total notable quotes across completed records: 162
- Records with at least one named community organization: 43

Missing record:

| Episode | Guest | Reason |
|---:|---|---|
| None | None | All Rank 4 intelligence records are complete. |

### Transcript Corpus

Source: `data/transcripts/`

- Rendered plain-text transcript files: 53
- Plain-text transcript corpus size: 1,692,080 bytes
- Plain-text SPA shell hits: 0
- Legacy HTML shell files: 16
- Legacy HTML shell size: 3,281 bytes each
- Legacy HTML shell hits: 16

The `.txt` files are the usable transcript corpus. The `.html` files are retained historical artifacts from static retrieval and should not be used as transcript evidence.

## Transcript Coverage Statistics

Rank 4 coverage:

- Total Rank 4 guests: 54
- Rank 4 guests with episode URLs: 54
- Rank 4 guests with completed intelligence records: 54
- Rank 4 guests with rendered `.txt` transcript files: 53

Known transcript gap:

| Episode | Guest | Status |
|---:|---|---|
| 2 | Gokul Rajaram | Intelligence record exists, but no rendered `.txt` transcript artifact is present; only the legacy 3.2 KB HTML shell exists. |

Phase 2 and Phase 3 rendered transcript retrieval is strong:

- Phase 2 URL-bearing records retrieved: 15 of 15
- Phase 3 URL-bearing records retrieved: 29 of 29
- Phase 2 and Phase 3 combined rendered transcript retrieval: 44 of 44

## Episode Intelligence Coverage Statistics

Completed records by phase:

| Phase | Records | Notes |
|---|---:|---|
| Phase 1 | 10 | Initial Rank 4 records. One rendered transcript artifact gap remains for Episode 2. |
| Phase 2 | 15 | Repaired from metadata-inferred to transcript-derived intelligence. |
| Phase 3 | 29 | Newly created from rendered transcripts. |
| Total | 54 | All Rank 4 episode intelligence records are complete. |

Validation status:

- All 54 JSON records parse successfully.
- All 54 records contain the required schema fields.
- Phase 2 and Phase 3 notable quotes were validated against retrieved transcripts.
- Full-corpus strict quote validation still reports older Phase 1 quote-string mismatches for Episodes 8, 9, 10, 11, 12, 14, 16, and 17.
- Episode 2 cannot be quote-validated locally until its rendered `.txt` transcript is retrieved.

Recommendation-engine readiness:

- The candidate pool for Connected Insights is now 54 records, which is enough to begin real recommendation experiments.
- The historical benchmark remains weak because newsletter Connected Insights values are not normalized guest names and many issues lack featured episode metadata.

## Theme Analysis Summary

The completed Rank 4 corpus is venture-heavy by design, but it now has enough structure for meaningful recommendation clusters.

Top industry labels:

| Industry | Completed Records |
|---|---:|
| Venture Capital | 51 |
| Enterprise Software | 17 |
| FinTech | 17 |
| Artificial Intelligence | 9 |
| Fund of Funds | 7 |
| InsurTech | 6 |
| Emerging Managers | 6 |
| Education | 6 |
| Deep Tech | 5 |
| Insurance | 5 |
| Payments | 5 |

Primary theme clusters:

- Founder evaluation and early-stage conviction.
- FinTech and financial infrastructure.
- LPs, emerging managers, and fund construction.
- Enterprise, deep tech, and technical diligence.
- Community, access, and mission.
- AI safety, data infrastructure, and technical frontier investing.

Founder lesson patterns:

- Be precise about the market, customer problem, and why-now.
- Show learning velocity rather than only pitch polish.
- Build investor relationships before fundraising pressure.
- Choose investors for the specific next company-building hurdle.
- Preserve capital discipline and avoid letting round size define strategy.
- Use lived experience, customer evidence, and non-obvious insight to create founder-market fit.

These themes are directly usable by Connected Insights because the records now include `primary_theme`, `secondary_themes`, `founder_lessons`, `industries`, `community_organizations`, and verbatim `notable_quotes`.

## Recommendation Engines

### Connected Insights

Implemented:

- `connected_insights_recommender.py`
- `connected_insights_recommender_v2.py`

The v2 engine is the current candidate because it uses the Rank 4 intelligence records in `data/episodes/rank4/` as the candidate pool and scores:

- primary theme similarity
- secondary theme overlap
- founder lesson overlap
- industry overlap
- newsletter recency
- newsletter frequency

Current validation baseline:

- Historical validation issues: 66 through 75
- Top-3 exact guest-name matches: 0 of 10
- Hit rate: 0%

This is not yet a meaningful failure of recommendation quality because the benchmark is noisy. The historical `connected_insight_guest` field often stores a headline such as `Leadership Is More Human Than Corporate`, not the actual guest name. Several validation issues also lack `featured_episode` and `featured_guest`, causing the engine to score from sparse or empty current-episode context.

Important note: `docs/connected-insights-v2.md` still contains an old limitation saying the dataset has only 10 Rank 4 records. That document should be refreshed now that the candidate pool has 54 records.

### Startup Corner

Implemented:

- Specification only: `docs/startup-recommendation-engine.md`

Not yet implemented:

- Executable startup recommendation engine.
- Startup intelligence records.
- Watchlist data model in repository data files.
- Recent-news or company-update ingestion.

Startup Corner should be treated as a design-ready but implementation-pending phase.

## Outstanding Gaps

1. Episode 2 needs a rendered `.txt` transcript artifact.
   - The intelligence record exists, but local transcript evidence is incomplete because only the legacy HTML shell is present.

2. Phase 1 quote validation needs cleanup.
   - Strict quote validation reports mismatches for Episodes 8, 9, 10, 11, 12, 14, 16, and 17.
   - These are likely quote-string exactness issues, but they should be repaired before using notable quotes as evidence in recommendation explanations.

3. Legacy HTML shell files remain in `data/transcripts/`.
   - There are 16 shell files at 3,281 bytes each.
   - They should be ignored by tooling or moved to an archive/error directory.

4. Newsletter history needs normalization.
   - Connected Insights labels need canonical guest names.
   - Featured episode and featured guest fields are missing in many older issues.
   - Publication dates and central themes are empty for every parsed issue.

5. Guest rankings need cleanup.
   - Remove or correct the malformed trailing `54` row.

6. Connected Insights v2 needs revalidation after data expansion.
   - The engine now has a strong candidate pool, but historical validation data is still weak.
   - Evaluation should shift from raw exact-match hit rate to editorial review until history normalization is complete.

7. Startup recommendation engine is not yet executable.
   - The spec exists, but the data model, watchlist records, scoring code, and validation workflow are still missing.

## Recommended Next Priorities

1. Normalize newsletter history.
   - Add canonical Connected Insights guest names and episode numbers where recoverable.
   - Backfill `featured_episode`, `featured_guest`, `publication_date`, and `central_theme` where possible.

2. Finish evidence hygiene for Rank 4.
   - Retrieve rendered Episode 2 transcript text.
   - Repair Phase 1 quote exactness.
   - Ensure transcript tooling only consumes `.txt` files.

3. Refresh Connected Insights v2 documentation and validation.
   - Update `docs/connected-insights-v2.md` for the 54-record candidate pool.
   - Re-run validation with normalized history.
   - Add an editorial-review validation set that judges whether top recommendations are useful, not only exact historical matches.

4. Improve Connected Insights scoring.
   - Use normalized theme clusters.
   - Add quote-backed rationale generation.
   - Penalize recently featured guests only after history fields are normalized.
   - Consider lightweight semantic similarity after string-based scoring is stable.

5. Implement Startup Corner recommendation data.
   - Create a startup watchlist dataset.
   - Add company intelligence records and recent-news fields.
   - Implement an executable recommender using the existing spec.

6. Add repository validation scripts.
   - Validate Rank 4 schema completeness.
   - Validate transcript artifact coverage.
   - Validate quote exactness.
   - Validate newsletter normalization completeness.

7. Treat recommendation output as editorial assistive.
   - The engine should generate ranked candidates and rationale.
   - Final Connected Insights and Startup Corner choices should remain human-reviewed until enough historical data exists for reliable automated evaluation.

## Bottom Line

TSSE Editorial OS has crossed the main data-readiness threshold for Connected Insights. The Rank 4 intelligence dataset is 100% complete, 54 records parse cleanly, and the Phase 2 and Phase 3 records are transcript-derived.

The next phase should focus on turning this strong episode intelligence layer into reliable recommendations by cleaning newsletter history, fixing the remaining transcript and quote gaps, and then revalidating Connected Insights v2 against normalized editorial history.
