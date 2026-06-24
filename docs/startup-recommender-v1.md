# Startup Recommender v1

## Purpose

`startup_recommender_v1.py` recommends Startup Corner candidates from the approved watchlist using only repository data.

Inputs:

- `data/startups/*.json`
- `data/episodes/rank4/*.json`
- `data/newsletter_history.csv`

The engine does not browse the web and does not use external APIs.

## CLI Usage

Use an existing Rank 4 episode record:

```bash
python3 startup_recommender_v1.py --current-episode 117 --top-n 5
```

Use a standalone current episode JSON file:

```bash
python3 startup_recommender_v1.py --current-record path/to/current_episode.json --top-n 5
```

Use a manual editorial brief:

```bash
python3 startup_recommender_v1.py \
  --primary-theme "Insurance infrastructure and risk management" \
  --secondary-theme "Carrier workflow modernization" \
  --founder-lesson "Use automation to reduce operational risk" \
  --industry "InsurTech" \
  --industry "Insurance" \
  --top-n 5
```

## Output

Every recommendation includes:

- `startup_name`
- `score`
- `matched_themes`
- `matched_industries`
- `matched_founder_background`
- `matched_shared_investments`
- `notable_milestones`
- `recency_status`
- `frequency_status`
- `score_breakdown`
- `plain_english_rationale`

## Scoring Methodology

Startup Recommender v1 is a local lexical scorer. It compares the current episode intelligence record to approved startup intelligence records.

### Episode Relevance

Episode relevance is the dominant signal.

| Signal | Maximum | Notes |
|---|---:|---|
| Primary theme to startup themes | 25 | Strongest narrative match. |
| Secondary themes to startup themes | 15 | Adds supporting editorial fit. |
| Founder lessons to startup themes | 12 | Captures practical founder-usefulness alignment. |
| Episode industries to startup industries | 18 | Supports topic fit, but should not dominate alone. |

The engine uses token overlap with light synonym expansion for local vocabulary such as:

- `FinTech` -> financial technology
- `InsurTech` -> insurance technology
- `AI` -> artificial intelligence

### Startup Intelligence

Startup intelligence adds supporting points when records contain evidence-backed fields.

| Signal | Maximum | Notes |
|---|---:|---|
| Founder background alignment | 8 | Uses official-source founder background only where available. |
| Shared investment priority | 100 | If Gopi Rangan and the current guest have a verified shared investment in a startup, that startup is prioritized as the first Startup Corner choice. |
| Notable milestones | 8 | Gives more credit to official-site-supported milestones than newsletter-history items needing review. |

### Editorial Constraints

Newsletter history prevents overuse.

| Signal | Score effect |
|---|---:|
| No prior normalized appearance | +5 |
| Last featured 13+ issues ago | +4 |
| Last featured 9-12 issues ago | -3 |
| Last featured 5-8 issues ago | -10 |
| Last featured 0-4 issues ago | -25 |

Frequency:

| Prior appearances | Score effect |
|---:|---:|
| 0 | 0 |
| 1 | 0 |
| 2-3 | -4 |
| 4+ | -8 |

## Weighting Rationale

Startup Corner should strengthen the issue narrative, not simply feature the freshest company.

For that reason:

- Episode relevance carries the most available points.
- Verified shared-investment relationships override ordinary relevance scoring because they are an established editorial rule for Startup Corner selection.
- Startup intelligence helps break ties and add editorial substance.
- Recency and frequency can strongly penalize recently featured companies.
- Freshness helps never-featured companies, but it is intentionally modest so low-relevance startups do not win only because they are unused.

## Examples

Episode 117, David Gritz, is an InsurTech episode. A sample command:

```bash
python3 startup_recommender_v1.py --current-episode 117 --top-n 5
```

The v1 scorer surfaces insurance-adjacent candidates such as Weav, Coterie, TrustLayer, and other approved watchlist companies, while exposing recency and frequency penalties for historically used startups.

Episode 75, Dan Rosen, is a FinTech episode. A sample command:

```bash
python3 startup_recommender_v1.py --current-episode 75 --top-n 5
```

The v1 scorer surfaces FinTech and payments-adjacent companies such as Konfyd and Balance Cash, and explains whether each candidate is fresh or historically used.

Episode 167, Geoff Ralston, is an AI safety episode. A sample command:

```bash
python3 startup_recommender_v1.py --current-episode 167 --top-n 5
```

The scorer surfaces AI-adjacent companies, but this case also shows a v1 limitation: generic `AI` overlap can be broad and needs human review.

## Limitations

- The scorer is lexical and does not use embeddings or semantic APIs.
- Generic `AI`, `FinTech`, and `InsurTech` tags can produce broad matches.
- Shared-investment scoring only activates when a startup record has a verified `guest_relationships` entry for the current guest.
- Newsletter history has missing `publication_date`, `central_theme`, and many `featured_episode` values.
- Some Startup Corner history rows are headline-style values rather than canonical company names.
- Notable milestones are sparse across the startup records.

## Future Improvements

- Add controlled startup theme clusters.
- Normalize `data/newsletter_history.csv` with canonical startup names and issue dates.
- Continue enriching Sure relationship and guest relationship fields so the shared-investment priority can be applied consistently.
- Add editorial feedback capture for accepted and rejected Startup Corner recommendations.
- Add local-only semantic similarity if lexical scoring proves too brittle.
