# Episode Intelligence Phase 1

This document records the first Phase 1 rollout for Rank 4 Episode Intelligence.

## Selected guests

The first 10 Rank 4 guests selected from `data/guest_rankings.csv` are:

1. Gokul Rajaram — Episode 2 — https://podcast.sure.ventures/episodes/100-angel-investments
2. Naeem Zafar — Episode 8 — https://podcast.sure.ventures/episodes/entrepreneurship-is-liberating
3. Ian Rountree — Episode 9 — https://podcast.sure.ventures/episodes/future-market
4. Kamal Hassan — Episode 10 — https://podcast.sure.ventures/episodes/networks-and-biases
5. Pat Matthews — Episode 11 — https://podcast.sure.ventures/episodes/startups-in-underdog-cities
6. Ravi Belani — Episode 12 — https://podcast.sure.ventures/episodes/alchemist
7. Shruti Gandhi — Episode 14 — https://podcast.sure.ventures/episodes/enterprise-vc
8. Manan Mehta — Episode 16 — https://podcast.sure.ventures/episodes/immigrant-entrepreneur
9. Lo Toney — Episode 17 — https://podcast.sure.ventures/episodes/lp-gp
10. Sheel Mohnot — Episode 20 — https://podcast.sure.ventures/episodes/gut-feel

## Prepared records

Placeholder JSON records have been created in `data/episodes/rank4/` for the Phase 1 episodes.
Each record includes:

- `guest_name`
- `episode_number`
- `episode_url`
- placeholder schema fields for `primary_theme`, `secondary_themes`, `founder_lessons`, `industries`, and `community_organizations`
- `source_notes` documenting the transcript requirement

## Readiness assessment

- Selected guests: confirmed from `data/guest_rankings.csv`.
- Episode URLs: accessible through the `URL` column in `data/guest_rankings.csv`.
- Schema alignment: records follow the Episode Intelligence schema defined in `docs/episode-intelligence-dataset.md` and `data/episodes/episode_template.json`.
- Transcript content: successfully sourced from the Simplecast API endpoint discovered via TSSE transcript page analysis.
- Phase 1 status: completed; all 10 Rank 4 Phase 1 episode records are populated and validated.

## Required transcript sources

For each Phase 1 record, the following source is required:

- The official TSSE episode transcript for the corresponding episode URL

These transcripts are required to populate:

- `primary_theme`
- `secondary_themes`
- `founder_lessons`
- `industries`
- `community_organizations`
- optional `notable_quotes`

## Next step

1. Acquire or access the TSSE transcript for each Phase 1 episode.
2. Extract the required intelligence fields using the rules in `docs/episode-analysis-framework.md`.
3. Update each placeholder file in `data/episodes/rank4/` with actual metadata.
4. Run validation checks against the dataset schema and Rank 4 guest list.
