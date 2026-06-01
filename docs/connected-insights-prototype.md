# Connected Insights Recommendation Prototype

This document describes the first Connected Insights recommendation prototype for TSSE Editorial OS.

## Purpose

The prototype ranks historical Connected Insights candidates based on the current episode’s editorial context and the newsletter history dataset.

It is designed to help the system recommend guests who can reinforce the current episode’s theme while avoiding repeated historical selections.

## Inputs

- `data/newsletter_history.csv`
- episode intelligence records (structured episode metadata)

## Recommendation Logic

### 1. Historical appearance analysis

The prototype extracts historical Connected Insights guests from the newsletter history dataset and computes:

- appearance frequency
- last appearance issue
- issues since last appearance

This provides a foundation for candidate scoring and diversity control.

### 2. Scoring components

The recommendation score is built from three core components:

- `frequency`: how many times the guest has been featured historically.
- `recency`: how long it has been since the guest last appeared.
- `metadata alignment`: how well the candidate’s episode metadata aligns with the current episode.

### 3. Appearance recency

The prototype applies a recency bias to avoid recommending guests who were featured too recently.

Recency scoring rules:

- 0–4 issues since last appearance: strong penalty
- 5–8 issues since last appearance: mild penalty
- 9–12 issues since last appearance: small boost
- 13+ issues since last appearance: larger boost

This encourages variety while still using historically strong guests.

### 4. Theme and industry alignment

If candidate episode metadata is available, the prototype adds bonus points for:

- matching primary theme
- overlapping secondary themes
- shared industry labels

These bonuses help surface historically relevant guests rather than only popular ones.

### 5. Candidate ranking

The final recommendation ranking is based on the combined score from:

- frequency weight
- recency weight
- metadata alignment weight

Each candidate is returned with a transparent rationale explaining the score factors.

## Output format

The recommender returns a ranked list of candidates with fields such as:

- `guest`
- `score`
- `frequency`
- `last_issue`
- `issues_since_last`
- `theme_match_score`
- `rationale`

## Limitations

- The prototype currently depends on exact string matches for guest names and historical candidates.
- If episode intelligence records are not available, recommendations rely solely on newsletter history.
- Historical candidate quality depends on the cleanliness of `data/newsletter_history.csv`.
- Theme matching is simplistic and string-based; it does not use embeddings or semantic similarity.

## Future improvements

1. Normalize and canonicalize guest names before matching.
2. Add richer theme matching with controlled vocabulary or semantic similarity.
3. Incorporate guest ranking data from the Guest Ranking Database.
4. Add a diversity penalty for candidates that appear too frequently overall.
5. Use episode transcript analysis to generate better founder lesson and theme alignment signals.
6. Add explainable output for why each candidate was scored as it was.

## How to use

Run the prototype with CLI arguments:

```bash
python3 connected_insights_recommender.py \
  --primary-theme "Human-Centered Leadership" \
  --secondary-theme "Relationship Building" \
  --industry "Venture Capital"
```

This produces a ranked list of Connected Insights candidates and their score rationales.
