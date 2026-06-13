# Connected Insights Recommendation Engine v3

## Purpose

Connected Insights v3 recommends Rank 4 guests whose transcript-derived episode intelligence can deepen the current newsletter issue.

The engine is implemented in `connected_insights_recommender_v3.py` and uses the full Rank 4 intelligence dataset in `data/episodes/rank4/`.

## Data Sources

- `data/episodes/rank4/*.json`: completed Rank 4 episode intelligence records.
- `data/newsletter_history.csv`: historical Connected Insights labels and issue numbers.

No external APIs are used. The engine does not scrape websites.

## Inputs

The recommender can use an existing Rank 4 episode as current context:

```bash
python3 connected_insights_recommender_v3.py --current-episode 179 --top-n 5
```

It can also accept a standalone current episode JSON file:

```bash
python3 connected_insights_recommender_v3.py --current-record path/to/current_episode.json
```

Or explicit fields:

```bash
python3 connected_insights_recommender_v3.py --top-n 5 \
  --current-guest "Current Guest" \
  --primary-theme "Founder conviction in early markets" \
  --secondary-theme "Founder-market fit" \
  --founder-lesson "Build relationships before fundraising." \
  --industry "Venture Capital" \
  --industry "FinTech"
```

## Candidate Pool

The candidate pool is all 54 Rank 4 records in `data/episodes/rank4/`.

When the current episode is one of those records, v3 excludes that same episode and guest from the candidate list.

## Scoring Methodology

Each candidate receives a weighted score across seven signals:

| Signal | Weighting |
|---|---:|
| Primary theme similarity | up to 40 per direct match, plus cross-theme matches |
| Secondary theme overlap | up to 14 per exact match |
| Founder lesson overlap | up to 10 per exact match |
| Industry overlap | 7 per exact industry |
| Community organization overlap | 5 per exact organization |
| Appearance recency | -20 to +8 |
| Historical usage frequency | 0 to +16 |

### Primary Theme Similarity

Primary theme is the strongest editorial anchor.

- Exact primary theme match: +40
- Strong token overlap: +24
- Medium token overlap: +16
- Light token overlap: +8
- Current primary theme to candidate secondary theme: up to +24
- Current secondary theme to candidate primary theme: up to +20

### Secondary Theme Overlap

Secondary themes refine the editorial match.

- Exact secondary theme match: +14
- Strong token overlap: +8
- Medium token overlap: +5
- Light token overlap: +2

### Founder Lesson Overlap

Founder lessons capture practical advice alignment.

- Exact lesson match: +10
- Strong token overlap: +6
- Medium token overlap: +4
- Light token overlap: +2

### Industry Overlap

Industries are supporting context, not the main driver.

- Exact industry match: +7 per shared industry

### Community Organization Overlap

Community overlap is intentionally modest because it is useful when relevant but should not dominate editorial theme fit.

- Exact organization match: +5 per shared organization

### Appearance Recency

Recency uses `data/newsletter_history.csv` when the historical Connected Insights label can be conservatively matched to a guest name.

- Featured in last 4 issues: -20
- Featured 5-8 issues ago: -10
- Featured 9-12 issues ago: -3
- Featured 13+ issues ago: +8
- No normalized appearance found: +8

### Historical Usage Frequency

Frequency is a modest trust signal.

- +4 per normalized historical appearance
- capped at +16

## Explainable Output

Each recommendation returns:

- `guest_name`
- `episode_number`
- `score`
- `matched_themes`
- `matched_founder_lessons`
- `matched_industries`
- `matched_community_organizations`
- `recency_note`
- `frequency_note`
- `score_breakdown`
- `plain_english_rationale`

Example command:

```bash
python3 connected_insights_recommender_v3.py --current-episode 179 --top-n 3
```

Example result shape:

```json
{
  "guest_name": "Aakar Vachhani",
  "episode_number": 135,
  "score": 54,
  "matched_themes": [
    {
      "current": "Data-driven emerging manager investing as a consistent asset allocation discipline",
      "candidate": "Emerging manager success through conviction, community, and team cohesion",
      "score": 8
    }
  ],
  "matched_founder_lessons": [
    {
      "current": "Reference-check investors for responsiveness and useful help rather than relying on ownership percentage or narrative.",
      "candidate": "Avoid teams that feel like a collection of people rather than a cohesive unit.",
      "score": 2
    }
  ],
  "matched_industries": [
    "Emerging Managers",
    "Fund of Funds",
    "Venture Capital"
  ],
  "recency_note": "No normalized Connected Insights appearance found; treated as fresh.",
  "plain_english_rationale": "Aakar Vachhani is relevant because Episode 135 shares the theme of Emerging manager success through conviction, community, and team cohesion..."
}
```

## Example Observations

Using Episode 179, Steve Kim, as the current episode, v3 surfaces LP and emerging-manager adjacent candidates such as Aakar Vachhani, Eric Sippel, Maryam Haque, Jessie Guo, and Aram Verdiyan.

Using Episode 20, Sheel Mohnot, as the current episode, v3 surfaces seed, founder-quality, and FinTech adjacent candidates such as Dan Kimerling, Zach Noorani, and Shruti Gandhi.

These examples show that the engine is using the expanded 54-record corpus rather than relying on historical newsletter frequency.

## Limitations

- Historical usage is conservative because `connected_insight_guest` often stores a section headline, not a canonical guest name.
- The scorer is lexical and token-based. It does not use embeddings or external semantic APIs.
- Common industries such as `Venture Capital` can add noise, so editorial review remains necessary.
- The engine does not yet use notable quotes in scoring, though quotes can be used later to enrich rationale.
- Current episode quality matters: sparse input fields produce weaker recommendations.

## Future Improvements

- Normalize Connected Insights history to canonical guest names and episode numbers.
- Add controlled theme cluster labels to reduce lexical noise.
- Add quote-backed rationale snippets after quote validation is clean across Phase 1.
- Add an editorial feedback file so accepted/rejected recommendations can tune weights.
- Consider local-only semantic similarity after string-based behavior is stable.
