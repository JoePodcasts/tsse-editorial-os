# Startup Intelligence Design

## Purpose

Startup Corner needs its own intelligence layer before recommendation logic is implemented.

Connected Insights v3 now has a complete Rank 4 episode intelligence corpus. Startup Corner should follow the same pattern: create structured, reviewable data first, then build a scoring engine that recommends watchlist companies based on episode relevance, Sure relationship context, recent company activity, and newsletter freshness.

This document defines the architecture for Startup Corner Intelligence. It does not implement recommendation logic yet.

## Current Context

Inputs already available in the repository:

- `data/episodes/rank4/`: 54 transcript-derived episode intelligence records.
- `data/newsletter_history.csv`: 45 parsed newsletter issues, with `startup_corner_company` values.
- `docs/startup-recommendation-engine.md`: existing editorial philosophy and high-level recommendation process.
- `docs/project-milestone-report.md`: current repository status and outstanding data gaps.

Approved Startup Watchlist:

- Lumber
- TrustLayer
- PAXAFE
- Coterie
- Hi Marley
- Ava
- Insurate
- Juno
- FirstShift
- Balance Cash
- Rigor.ai
- Honeycomb
- Konfyd
- Weav

Newsletter history currently shows Startup Corner usage, but the values are not fully normalized. For example, some rows use company names, while others use headline-style values such as `Transforming Construction Workforce Management With AI` or milestone phrasing such as `PAXAFE Named a FreightTech 100 company`.

## Startup Intelligence Schema

Startup intelligence records should live under a new data directory, for example:

```text
data/startups/
  lumber.json
  trustlayer.json
  paxafe.json
  coterie.json
  hi_marley.json
  ava.json
  insurate.json
  juno.json
  firstshift.json
  balance_cash.json
  rigor_ai.json
  honeycomb.json
  konfyd.json
  weav.json
```

Each record should be a JSON object using the following schema.

```json
{
  "company_name": "PAXAFE",
  "canonical_slug": "paxafe",
  "aliases": ["PAXAFE Named a FreightTech 100 company"],
  "website": "",
  "category": "",
  "industries": [],
  "themes": [],
  "founder_names": [],
  "founder_background": "",
  "sure_relationship": {
    "relationship_type": "",
    "relationship_notes": "",
    "evidence": []
  },
  "guest_relationships": [
    {
      "guest_name": "",
      "episode_number": null,
      "relationship_type": "",
      "relationship_notes": "",
      "evidence": []
    }
  ],
  "notable_milestones": [
    {
      "date": "",
      "title": "",
      "summary": "",
      "source_url": "",
      "source_type": "",
      "review_status": "unreviewed"
    }
  ],
  "last_news_date": "",
  "previous_newsletter_appearances": [
    {
      "issue_number": 73,
      "raw_value": "PAXAFE",
      "normalized_company": "PAXAFE"
    }
  ],
  "evidence_status": {
    "company_profile_reviewed": false,
    "sure_relationship_reviewed": false,
    "newsletter_history_reviewed": false,
    "last_manual_review_date": ""
  }
}
```

### Field Definitions

| Field | Purpose |
|---|---|
| `company_name` | Human-facing company name. |
| `canonical_slug` | Stable lowercase identifier used by tooling. |
| `aliases` | Alternate names, historical labels, headline variants, and spacing/case variants from newsletter history. |
| `website` | Official company website. |
| `category` | Short editorial category, such as InsurTech, Construction Tech, Logistics, AI, or FinTech. |
| `industries` | Searchable industry tags used for episode-to-startup matching. |
| `themes` | Editorial themes, such as operational efficiency, insurance modernization, supply-chain visibility, workforce management, risk infrastructure, AI automation, or financial access. |
| `founder_names` | Founder or key executive names, if verified. |
| `founder_background` | Concise manually reviewed founder context. |
| `sure_relationship` | Structured description of the Sure relationship, with evidence and review status. |
| `guest_relationships` | Links to podcast guests, investors, co-investors, advisors, customers, or thematic relationships where verified. |
| `notable_milestones` | Product launches, partnerships, funding, awards, customer milestones, major posts, or founder commentary. |
| `last_news_date` | Most recent reviewed public activity date. |
| `previous_newsletter_appearances` | Normalized appearances from `data/newsletter_history.csv`. |
| `evidence_status` | Manual review flags so tooling can distinguish verified data from empty or unreviewed data. |

## Initial Newsletter History Normalization

The first automation pass should normalize existing `startup_corner_company` values against the approved watchlist.

Observed watchlist appearance counts from `data/newsletter_history.csv`:

| Company | Normalized count | Most recent issue | Issues since latest issue 75 |
|---|---:|---:|---:|
| Lumber | 3 | 70 | 5 |
| TrustLayer | 1 | 45 | 30 |
| PAXAFE | 4 | 73 | 2 |
| Coterie | Needs alias review | Needs alias review | Needs alias review |
| Hi Marley | 1 | 67 | 8 |
| Ava | 3 | 72 | 3 |
| Insurate | 2 | 68 | 7 |
| Juno | 3 | 74 | 1 |
| FirstShift | 3 | 75 | 0 |
| Balance Cash | 0 | None found | None found |
| Rigor.ai | 0 | None found | None found |
| Honeycomb | 3 | 71 | 4 |
| Konfyd | 0 | None found | None found |
| Weav | 0 | None found | None found |

Known alias cleanup examples:

- `HoneyComb` should normalize to `Honeycomb`.
- `Firstshift AI` should normalize to `FirstShift`.
- `Coterie Insurance` and `Coterie - a vision driven by AI and human creativity` should be reviewed as likely Coterie appearances.
- Headline-style entries should be mapped only when the company identity is clear.

The normalization layer should preserve the raw newsletter value even when a canonical company match is assigned.

## Data Collection Workflow

### Automated Collection

Automation can safely handle structured repository and public-source collection when sources are explicit and reviewable:

- Parse `data/newsletter_history.csv` for previous Startup Corner appearances.
- Normalize known aliases to approved watchlist companies.
- Compute appearance count, most recent issue, and issues since last appearance.
- Read `data/episodes/rank4/*.json` to collect episode themes, founder lessons, industries, and community organizations for matching.
- Maintain startup JSON schema validation.
- Detect missing required fields and stale `last_news_date` values.
- Collect candidate URLs from manually approved source lists.
- Store source URLs and retrieved dates for later review.

Automated tooling should not invent categories, founder backgrounds, Sure relationships, milestones, or guest relationships when evidence is absent.

### Manual Review

Manual review is required for fields where editorial accuracy and relationship sensitivity matter:

- Confirm each company's official website.
- Confirm company category and industry tags.
- Confirm founder names and founder background.
- Confirm Sure relationship details.
- Confirm co-investor, advisor, customer, or guest relationships.
- Decide whether a public company update is newsletter-worthy.
- Resolve ambiguous newsletter history rows.
- Approve aliases that map headline-style rows to canonical companies.
- Decide whether a company should be temporarily excluded because it was too recently featured.

Manual review should update `evidence_status` fields so the recommender can distinguish reviewed intelligence from incomplete records.

### Recommended Sources

Use sources in this order:

1. Existing repository data:
   - `data/newsletter_history.csv`
   - `data/episodes/rank4/*.json`
   - existing project docs
2. Official company sources:
   - company website
   - company blog
   - press page
   - careers or about page for product positioning
3. Sure Ventures internal or approved materials:
   - portfolio notes
   - investment memo excerpts approved for editorial use
   - partner notes on relationship context
4. Public third-party sources, reviewed manually:
   - reputable business press
   - award announcements
   - conference pages
   - founder interviews or podcasts
5. Professional profile sources, reviewed manually:
   - founder LinkedIn pages
   - company LinkedIn updates

For public web sources, the data layer should store source URLs and a short evidence summary rather than relying on untraceable pasted notes.

## Recommendation Scoring Framework

Startup Recommendation Engine v1 should score only approved watchlist companies with reviewed or explicitly available intelligence.

Proposed total: 100 base points before penalties.

| Signal | Weight | Purpose |
|---|---:|---|
| Episode relevance | 45 | Match startup themes and industries to the current episode's primary theme, secondary themes, founder lessons, and industries. |
| Co-investment or Sure relationship | 20 | Reward verified relationship strength when it improves editorial relevance. |
| Recent company activity | 20 | Reward recent, meaningful, source-backed company milestones. |
| Newsletter recency and frequency | 15 | Prefer fresh companies and penalize recent or repeated appearances. |

### Episode Relevance: 45 Points

Recommended subweights:

- Primary theme to startup theme match: up to 20.
- Secondary theme overlap: up to 10.
- Founder lesson to startup story match: up to 8.
- Industry overlap: up to 7.

Theme fit should matter more than broad industry overlap. A construction workforce company that directly reinforces an episode about operational decision-making should beat a generic AI company with only a loose industry match.

### Co-Investment or Sure Relationship: 20 Points

Recommended subweights:

- Direct Sure portfolio or investment relationship: up to 10.
- Verified co-investor, advisor, LP, or guest relationship: up to 5.
- Strong strategic relationship to the episode's guest, market, or customer profile: up to 5.

This signal should require reviewed evidence. Unknown relationship fields should score zero, not an assumed connection.

### Recent Company Activity: 20 Points

Recommended subweights:

- Major product, funding, partnership, award, customer, or market milestone in the last 90 days: up to 10.
- Meaningful founder insight, public commentary, or thought-leadership update in the last 180 days: up to 5.
- Editorial usefulness of the milestone to Startup Corner: up to 5, assigned manually or from a reviewed milestone rating.

Activity scoring should reward usable newsletter substance, not volume of minor updates.

### Newsletter Recency and Frequency: 15 Points

Recommended scoring:

| Prior appearance status | Score effect |
|---|---:|
| Never featured or no normalized appearance found | +15 |
| Last featured 13+ issues ago | +12 |
| Last featured 9-12 issues ago | +6 |
| Last featured 5-8 issues ago | 0 |
| Last featured 0-4 issues ago | -20 or exclude by default |

Frequency adjustment:

- 0-1 prior appearances: no penalty.
- 2-3 prior appearances: -3.
- 4+ prior appearances: -6.

The first version should expose both the raw recency score and the reason, so editors can override it when a company has unusually strong news.

## Recommendation Output

Startup Recommendation Engine v1 should return a ranked list with enough context for editorial review:

```json
{
  "company_name": "FirstShift",
  "score": 82,
  "score_breakdown": {
    "episode_relevance": 34,
    "sure_relationship": 16,
    "recent_company_activity": 17,
    "newsletter_recency": 15
  },
  "matched_episode_themes": [],
  "matched_industries": [],
  "matched_founder_lessons": [],
  "relationship_note": "",
  "recent_activity_note": "",
  "newsletter_recency_note": "",
  "plain_english_rationale": ""
}
```

Recommended CLI shape:

```bash
python3 startup_recommender_v1.py --current-episode 188 --top-n 5
python3 startup_recommender_v1.py --current-record path/to/current_episode.json --top-n 5
```

The engine should also support a manual brief mode for future newsletter planning:

```bash
python3 startup_recommender_v1.py \
  --primary-theme "Operational decision-making under uncertainty" \
  --industry "Construction Technology" \
  --founder-lesson "Use workflow data to improve frontline execution" \
  --top-n 5
```

## Validation Rules

Before using startup recommendations editorially, validate:

- Every startup JSON file parses successfully.
- Every approved watchlist company has exactly one record.
- Required fields exist for every record.
- Empty or unreviewed fields are represented as empty values or explicit review flags, not invented text.
- Newsletter history aliases map to canonical companies only when clear.
- Recommendations include score breakdowns and plain-English rationale.
- Recently featured companies are penalized or excluded according to the configured rule.
- The engine never recommends companies outside the approved watchlist.

## Implementation Roadmap

### Phase 1: Startup Intelligence Layer

Deliverables:

- Create `data/startups/`.
- Create one JSON record for each approved watchlist company.
- Add aliases from `data/newsletter_history.csv`.
- Populate previous newsletter appearances from normalized history.
- Add manual review placeholders for websites, categories, founder data, Sure relationship, guest relationships, and milestones.
- Add a validation script for schema completeness and watchlist coverage.

Success criteria:

- 14 startup records exist.
- All records parse cleanly.
- All approved watchlist companies are represented.
- Newsletter appearances are normalized and preserved with raw values.
- Unknown fields remain blank or explicitly unreviewed.

### Phase 2: Startup Recommendation Engine v1

Deliverables:

- Create `startup_recommender_v1.py`.
- Load current episode context from `data/episodes/rank4/` or a standalone brief.
- Load startup intelligence records from `data/startups/`.
- Score episode relevance, Sure relationship, recent activity, and newsletter recency.
- Return ranked, explainable recommendations.
- Add documentation for scoring methodology and CLI usage.

Success criteria:

- Given an episode intelligence record, the engine returns ranked watchlist startups.
- Every recommendation includes score breakdown, matched evidence, recency note, and rationale.
- The engine does not recommend companies outside the watchlist.
- The engine handles incomplete startup intelligence without fabricating missing evidence.

### Phase 3: Editorial Evaluation Process

Deliverables:

- Create a Startup Corner editorial evaluation worksheet.
- Select a small test set of current episodes or briefs across distinct themes.
- Capture top 5 recommendations for each.
- Add Joe/Gopi review fields for relevance, newsworthiness, freshness, and newsletter usability.
- Use feedback to tune weights and exclusion rules.

Suggested review fields:

- Strong candidate? Yes/No:
- Plausible candidate? Yes/No:
- Newsworthy enough for Startup Corner? Yes/No:
- Best recommendation among top 5:
- Notes:
- Would use in newsletter? Yes/No:

Success criteria:

- Editors can identify at least one publishable Startup Corner candidate in most test cases.
- Rationale is useful without requiring the reviewer to inspect raw JSON.
- Failure modes are clear enough to guide the next weight-tuning pass.

## Open Questions

- Which watchlist companies are confirmed Sure portfolio companies versus broader ecosystem companies?
- Which relationship details are approved for editorial use?
- Should a company featured in the last 0-4 issues be excluded by default, or only heavily penalized?
- Should recently featured companies be eligible when they have major news?
- Should startup categories be controlled vocabulary values or free-form tags?
- Should public source collection be manual-only at first, or should a reviewed source list drive limited automated retrieval?

## Guiding Principle

Startup Corner should recommend the company whose current story best strengthens the newsletter issue.

The best candidate is not necessarily the newest update or the closest industry label. It is the watchlist company with a verified, timely, and editorially useful connection to the episode's theme.
