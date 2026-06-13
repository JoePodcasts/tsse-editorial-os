# Connected Insights v3 Evaluation Plan

## Purpose

Connected Insights v3 should be evaluated as an editorial decision-support tool, not only as a historical hit-rate predictor.

Earlier newsletter history often stores Connected Insights headlines instead of normalized guest names, and the current Rank 4 intelligence framework did not exist when many historical choices were made. A pure exact-match benchmark would therefore understate recommendation quality.

## Evaluation Goals

The evaluation should answer:

- Are the top recommendations thematically relevant?
- Do the rationales make editorial sense?
- Are strong candidates surfaced from across the full 54-guest Rank 4 dataset?
- Are recently used guests handled appropriately when history is reliable?
- Does the output help an editor choose a Connected Insights guest faster?

## Evaluation Set

Create a review set of 15-20 current episode contexts:

- 5 recent newsletter issues with known episode context.
- 5 historical Rank 4 records with strong themes, such as FinTech, AI, or founder conviction.
- 5 synthetic editorial briefs based on likely future newsletter themes.
- Optional: 3 edge cases with sparse context to test graceful degradation.

Each evaluation item should include:

- current guest or episode number
- primary theme
- secondary themes
- founder lessons
- industries
- expected editorial intent

## Review Workflow

1. Run v3 for each evaluation item:

```bash
python3 connected_insights_recommender_v3.py --current-episode 179 --top-n 5
```

2. Give the editor the top 5 recommendations with:

- guest name
- episode number
- score
- matched themes
- matched founder lessons
- matched industries
- recency note
- rationale

3. The editor rates each candidate:

| Rating | Meaning |
|---:|---|
| 5 | Excellent Connected Insights candidate |
| 4 | Strong and usable |
| 3 | Plausible but not preferred |
| 2 | Weak connection |
| 1 | Not relevant |

4. The editor marks whether at least one of the top 3 is publishable.

5. The editor optionally selects the best candidate and writes one sentence explaining why.

## Metrics

Primary metrics:

- Top-1 editorial rating average.
- Top-3 contains at least one publishable candidate.
- Top-5 contains at least one publishable candidate.
- Rationale usefulness rating.

Secondary metrics:

- Diversity of recommended guests.
- Diversity of recommended theme clusters.
- Frequency of over-recommending generic venture-capital matches.
- Frequency of missing obvious topical matches.
- Recency penalty correctness where history has normalized guest names.

Historical exact-match can be tracked, but it should not be the primary metric until newsletter history is normalized.

## Suggested Acceptance Thresholds

For the first editorial evaluation pass:

- Average top-1 rating: at least 3.5 out of 5.
- Top-3 publishable candidate rate: at least 70%.
- Top-5 publishable candidate rate: at least 85%.
- Rationale usefulness rating: at least 3.5 out of 5.

These thresholds are intended to validate usefulness, not perfection.

## Reviewer Rubric

Editors should consider:

- Theme fit: Does the recommended episode deepen the same idea?
- Contrast value: Does it add a useful second perspective rather than repeating the same point?
- Founder usefulness: Would the recommendation produce useful advice for founders?
- Specificity: Is the connection more specific than broad `Venture Capital` overlap?
- Freshness: Has this guest been overused recently?
- Explainability: Does the rationale make it easy to defend the recommendation?

## Feedback Capture

Create a simple CSV or JSON file after the first review pass:

```csv
evaluation_id,current_episode,recommended_episode,guest,rating,publishable,notes
```

Use this feedback to tune:

- theme weights
- industry weights
- recency penalties
- generic industry dampening
- controlled theme cluster mappings

## Known Evaluation Risks

- Historical Connected Insights labels are noisy.
- Some older episode intelligence records have Phase 1 quote exactness gaps, though the intelligence fields still parse.
- Common industry labels can make broad venture-capital recommendations look stronger than they are.
- Synthetic briefs may not capture the nuance of actual newsletter writing.

## Next Step

Run an initial 15-item editorial review, tune weights only after reviewing the failure modes, and then repeat with a second holdout set.
