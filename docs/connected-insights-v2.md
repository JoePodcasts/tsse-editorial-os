# Connected Insights Recommendation Engine v2

This document describes the Phase 2 Connected Insights recommendation engine for TSSE Editorial OS. It is designed to use structured episode intelligence records as the primary signal instead of relying primarily on newsletter appearance frequency.

## Goals

- Recommend Rank 4 guests whose episode intelligence is topically aligned with the current newsletter issue.
- Use episode metadata to capture editorial similarity beyond raw historical counts.
- Preserve appearance recency and frequency as secondary diversification signals.

## Data sources

- `data/episodes/rank4/*.json` — Rank 4 episode intelligence records.
- `data/newsletter_history.csv` — historical newsletter issues, including previous Connected Insights selections and issue numbering.

## Input signals

The engine accepts a current episode context with:

- `primary_theme`
- `secondary_themes`
- `founder_lessons`
- `industries`
- `guest_name` (optional)

When available, the engine can also derive the current episode from newsletter history using `featured_episode` or `featured_guest`.

## Candidate pool

Recommendations are generated from the complete set of Rank 4 episode intelligence records in `data/episodes/rank4/`.

This prevents the system from recommending only guests that have already appeared frequently in the newsletter, and instead allows the engine to surface thematically relevant candidates even if they have not been recently featured.

## Usage

Run the new engine locally from the repository root:

```bash
python3 connected_insights_recommender_v2.py --top-n 5 \
  --primary-theme "Seed investing guided by founder quality and intuitive signals" \
  --secondary-theme "Founder-first seed investing" \
  --secondary-theme "Fintech opportunity assessment" \
  --founder-lesson "At seed stage, the team is the most important asset" \
  --industry "Venture Capital" \
  --industry "Fintech"
```

To validate against the original historical benchmark set:

```bash
python3 connected_insights_recommender_v2.py --validate-historical
```

## Scoring methodology

The final recommendation score combines six components:

1. Primary theme similarity
2. Secondary theme overlap
3. Founder lesson overlap
4. Industry overlap
5. Guest appearance recency
6. Guest appearance frequency

### 1. Primary theme similarity

Primary theme matching is the strongest signal.

- Exact primary theme match: +40
- Primary theme found in the candidate's secondary themes, or vice versa: +25
- Partial primary theme substring match: +15
- Shared primary theme tokens: up to +10

This prioritizes candidates that carry the same core editorial idea as the current issue.

### 2. Secondary theme overlap

Secondary themes are supporting context.

- Exact secondary theme overlap: +6 per theme
- Token-level overlap between secondary themes: +4 for strong overlap, +2 for moderate overlap, +1 for light overlap

This allows the engine to recognize related subtopics even when phraseology differs.

### 3. Founder lesson overlap

Founder lessons capture practical editorial nuance.

- Exact lesson overlap: +3 per lesson
- Token-level overlap between lesson statements: +3 for strong overlap, +2 for moderate overlap, +1 for light overlap

This reinforces recommendations that share applied founder investing or operating lessons.

### 4. Industry overlap

Industries support thematic similarity without dominating it.

- +5 per shared industry

Industry overlap is useful when the same sector appears in both the current episode and candidate history.

### 5. Guest appearance recency

Recency is a secondary signal to promote variety.

- Last 4 issues: -20
- 5–8 issues: -8
- 9–12 issues: +0
- 13+ issues: +10
- No recorded history: +8

This helps the engine avoid recommending guests who were featured too recently while still allowing strong thematic matches.

### 6. Guest appearance frequency

Frequency is a modest positive signal.

- +5 per historical Connected Insights appearance, capped at +25

This rewards guests that have been valuable in the newsletter before, while keeping the focus on episode intelligence.

## Weighting rationale

- **Primary theme** is the main editorial anchor, so it receives the highest weight.
- **Secondary themes** and **founder lessons** are context signals that refine the recommendation.
- **Industry overlap** is supportive metadata rather than the core driver.
- **Recency** and **frequency** are included to maintain diversity and acknowledge newsletter experience, but they are intentionally weaker than the episode intelligence signals.

## Limitations

- The current dataset contains only 10 Rank 4 episode intelligence records in `data/episodes/rank4/`, which limits recommendation diversity.
- Historical `connected_insight_guest` values in `data/newsletter_history.csv` are often section titles rather than normalized guest names, which makes historical frequency and recency noisy.
- Current episode metadata may be sparse for historical validation issues, so the engine may fall back to weaker signals.
- Exact lesson and theme matching is still string-based; semantic relationships are only approximated with token overlap.

## Future improvements

- Add canonical guest normalization for `connected_insight_guest` values in newsletter history.
- Expand the episode intelligence dataset beyond Phase 1 to provide more candidate coverage.
- Add semantic similarity scoring with embeddings for themes, lessons, and industries.
- Incorporate natural language processing to derive current issue context from newsletter copy when structured metadata is missing.
- Introduce a small manual review layer for early recommendations to refine weights and editorial fit.
