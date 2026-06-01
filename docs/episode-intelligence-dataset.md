# Episode Intelligence Dataset

This document defines the design, storage, and population strategy for the Episode Intelligence Dataset focused on Rank 4 guests only.

## Purpose

The Episode Intelligence Dataset is the structured source of truth for episode-level metadata used by Connected Insights recommendations.

Rank 4 guests are the highest-priority candidates for Connected Insights, so this dataset is intentionally limited to the 54 currently identified Rank 4 guest episodes.

## Scope

- Dataset includes only episodes whose guest has `guest_rank = 4` in `data/guest_rankings.csv`.
- The dataset supports recommendation scoring, newsletter drafting, and editorial review.
- It is not a transcript repository; it is a metadata layer derived from TSSE transcripts.

## Dataset structure

Each record in the dataset represents one Rank 4 guest episode and includes the following minimum intelligence fields:

- `guest_name` (string)
- `episode_number` (integer)
- `episode_url` (string)
- `primary_theme` (string)
- `secondary_themes` (array of strings)
- `founder_lessons` (array of strings)
- `industries` (array of strings)
- `community_organizations` (array of strings)

Optional support fields:

- `title` (string)
- `guest_rank` (integer)
- `publication_date` (string, ISO 8601)
- `transcript_url` (string)
- `notable_quotes` (array of strings)
- `source_notes` (string)

## Storage format

Recommended storage model:

- `data/episodes/rank4/` directory containing one JSON file per episode, named `episode_<episode_number>.json`
- A shared template is stored in `data/episodes/episode_template.json`
- Optionally, an index file at `data/episodes/rank4_index.json` for fast lookup

Example file structure:

- `data/episodes/rank4/episode_2.json`
- `data/episodes/rank4/episode_8.json`
- `data/episodes/rank4_index.json`

Example record schema (JSON):

```json
{
  "episode_number": 2,
  "guest_name": "Gokul Rajaram",
  "episode_url": "https://podcast.sure.ventures/episodes/100-angel-investments",
  "primary_theme": "Founder Strategy for Long-Term Growth",
  "secondary_themes": ["Product Market Fit", "Capital Efficiency"],
  "founder_lessons": [
    "Focus on durable tailwinds rather than short-term trends.",
    "Align capital use with the business model before scaling."
  ],
  "industries": ["Venture Capital", "Enterprise Software"],
  "community_organizations": ["Riley’s Way Foundation"]
}
```

## Update workflow

The workflow for populating and maintaining the Rank 4 dataset should be:

1. Identify the target Rank 4 episodes from `data/guest_rankings.csv`.
2. Retrieve the authoritative transcript for each target episode from the TSSE podcast source.
3. Extract the minimum intelligence fields using the episode analysis rules in `docs/episode-analysis-framework.md`.
4. Create or update the per-episode JSON file in `data/episodes/rank4/`.
5. Add any optional metadata fields that support recommendation matching.
6. Commit the updated JSON files and refresh `data/episodes/rank4_index.json`.

## Validation process

Validation should be a lightweight, deterministic check performed before data is accepted into the dataset.

Validation rules:

- Required fields must be present and non-empty:
  - `guest_name`
  - `episode_number`
  - `episode_url`
  - `primary_theme`
  - `secondary_themes`
  - `founder_lessons`
  - `industries`
  - `community_organizations`
- `episode_number` must match a Rank 4 episode in `data/guest_rankings.csv`.
- `guest_name` must match the Rank 4 guest name from the CSV.
- `episode_url` must be a valid URL string.
- `secondary_themes`, `founder_lessons`, `industries`, and `community_organizations` must be arrays.
- `secondary_themes` should contain 2–4 items.
- `founder_lessons` should contain at least 2 items.
- `industries` should contain at least 1 item.
- `community_organizations` may be empty, but if present should contain actual organization names.

Validation output should report:

- missing required fields
- mismatched episode or guest values
- schema violations
- stale or obsolete records for episodes no longer ranked 4

## Phased population strategy

A phased rollout reduces risk and allows the recommendation engine to learn from early Rank 4 records.

### Phase 1: Top 10 Rank 4 guests

Populate the first 10 Rank 4 episodes by episode number.
These episodes should establish the canonical record shape and validation cadence.

Top 10 Rank 4 episodes:

1. Episode 2 — Gokul Rajaram
2. Episode 8 — Naeem Zafar
3. Episode 9 — Ian Rountree
4. Episode 10 — Kamal Hassan
5. Episode 11 — Pat Matthews
6. Episode 12 — Ravi Belani
7. Episode 14 — Shruti Gandhi
8. Episode 16 — Manan Mehta
9. Episode 17 — Lo Toney
10. Episode 20 — Sheel Mohnot

### Phase 2: Top 25 Rank 4 guests

Expand to the first 25 Rank 4 episodes by episode number.
This adds broader topical coverage while still keeping the initial dataset manageable.

Top 25 Rank 4 episodes includes the first 10 plus:

11. Episode 25 — Ullas Naik
12. Episode 26 — Ashmeet Sidana
13. Episode 34 — Vivek Krishnamurthy
14. Episode 50 — Arjan Schutte
15. Episode 51 — Hans Morris
16. Episode 53 — Sunil Nagaraj
17. Episode 54 — Satya Patel
18. Episode 55 — Ramneek Gupta
19. Episode 60 — Mark Fernandes
20. Episode 63 — Galym Imanbayev
21. Episode 70 — Patrick Eggen
22. Episode 73 — Charles Hudson
23. Episode 74 — Heather Hartnett
24. Episode 75 — Dan Rosen
25. Episode 79 — Nuno Gonçalves Pedro

### Phase 3: All 54 Rank 4 guests

Complete the dataset across all 54 current Rank 4 episodes.
At this stage, the dataset can fully support Connected Insights recommendations and begin seeding historical episode intelligence.

## Minimum intelligence record

Each Rank 4 episode record must include the following minimum fields:

- `guest_name`
- `episode_number`
- `episode_url`
- `primary_theme`
- `secondary_themes`
- `founder_lessons`
- `industries`
- `community_organizations`

These fields are deliberately aligned with `docs/episode-analysis-framework.md` and the `episode` and `analysis` sections of `docs/data-model.md`.

## Recommended process for generating records from transcripts

The most efficient process is manual transcript extraction with structured note capture.

1. Use the TSSE transcript as the authoritative source.
2. Read the episode introduction, host framing, and guest thesis to identify the `primary_theme`.
3. Scan the transcript for 2–4 supporting concepts and fill `secondary_themes`.
4. Extract 2–4 founder-oriented lessons from explicit guidance, tradeoffs, or strategic rules.
5. Identify the main industry labels referenced by the guest.
6. Capture any named community organizations mentioned in the episode.
7. Record the episode URL, guest name, and episode number from `data/guest_rankings.csv`.
8. Write the record directly into the `data/episodes/rank4/episode_<n>.json` file using the agreed schema.
9. Run validation to ensure schema consistency and Rank 4 alignment.

### Efficiency recommendations

- Start with the episode summary and transcript sections that most clearly contain themes and advice.
- Use the same normalized theme vocabulary across records to support later recommendation matching.
- Keep lessons concise and episode-specific.
- Use a consistent industry taxonomy drawn from `docs/episode-analysis-framework.md`.
- If a transcript mentions a community organization, include it even when the mention is brief.

## Practical plan for the repository

1. Create `data/episodes/rank4/` and place one JSON record per Rank 4 episode.
2. Use `data/episodes/episode_template.json` as the schema blueprint.
3. Populate Phase 1 records first and validate them.
4. Expand to Phase 2 once the schema and validation process are stable.
5. Complete Phase 3 with the remaining Rank 4 episodes.
6. Keep `docs/episode-intelligence-dataset.md` as the policy and process reference for episode intelligence population.

## Why this matters

Rank 4 guests are the editorially approved candidates for Connected Insights. A focused Rank 4 Episode Intelligence Dataset creates a high-signal metadata layer that can be consumed by recommendation logic without needing external APIs or scraping.
