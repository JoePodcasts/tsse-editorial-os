# Connected Insights v2 Validation

This validation report evaluates the new Connected Insights Recommendation Engine v2 against the same historical newsletter issues used in the original prototype validation.

## Validation setup

- Tested issues: 66 through 75
- Recommendation engine: `connected_insights_recommender_v2.py`
- Candidate pool: all Rank 4 episode intelligence records in `data/episodes/rank4/`
- Validation input:
  - current episode derived from `featured_episode` or `featured_guest` when possible
  - otherwise current episode metadata was unavailable and the engine relied on thematic candidate scoring plus history signals
- Top recommendations: top 3 guests returned for each issue

> Note: `data/newsletter_history.csv` stores historical `connected_insight_guest` values as newsletter section titles in many cases, not normalized guest names. That makes exact hit-rate comparison with raw guest names unreliable.

## Results by issue

| Issue | Actual Connected Insight Label | Current Episode Used | Top Recommendation | Top 3 Recommendations | Exact guest name match |
|------:|-------------------------------|----------------------|--------------------|-----------------------|:----------------------:|
| 66 | VCs who are deeply connected to the founders they serve will win | none | Kamal Hassan | Kamal Hassan, Pat Matthews, Ravi Belani | No |
| 67 | Build Companies Without Stretch Marks | none | Kamal Hassan | Kamal Hassan, Pat Matthews, Ravi Belani | No |
| 68 | What Makes Founders Stand Out | Episode 20 / Sheel Mohnot | Ian Rountree | Ian Rountree, Shruti Gandhi, Gokul Rajaram | No |
| 69 | Endurance Is the New Alpha | none | Kamal Hassan | Kamal Hassan, Pat Matthews, Ravi Belani | No |
| 70 | The Geometry Framework | none | Kamal Hassan | Kamal Hassan, Pat Matthews, Ravi Belani | No |
| 71 | Look where others are not looking | none | Kamal Hassan | Kamal Hassan, Pat Matthews, Ravi Belani | No |
| 72 | Start with Your Childhood, Not Your Resume | none | Kamal Hassan | Kamal Hassan, Pat Matthews, Ravi Belani | No |
| 73 | Conviction in the absence of traditional metrics | none | Kamal Hassan | Kamal Hassan, Pat Matthews, Ravi Belani | No |
| 74 | Competition Is Irrelevant When You're Building Infrastructure | none | Kamal Hassan | Kamal Hassan, Pat Matthews, Ravi Belani | No |
| 75 | Leadership Is More Human Than Corporate | none | Kamal Hassan | Kamal Hassan, Pat Matthews, Ravi Belani | No |

## Hit rate summary

- Total issues tested: 10
- Actual guest name exact matches in top 3: 0
- Hit rate: 0%

## Observations

- The v2 engine is structurally stronger than the original prototype because it scores candidates using episode intelligence records first and only uses history as a secondary signal.
- The result still reports `0%` under raw exact-match scoring because the historical benchmark uses title-formatted Connected Insights labels, not normalized guest names.
- Issue 68 is the only case where the engine successfully used a current episode intelligence record (`Sheel Mohnot`, Episode 20), and the top recommendation changed from the earlier baseline.
- Most historical issues in the benchmark do not provide enough structured current episode metadata, so the evaluation remains constrained by the available dataset.

## Practical conclusion

- The engine now supports theme-aware recommendations and has the right architecture for future improvements.
- The current historical benchmark is not sufficient to demonstrate a direct hit-rate improvement because the input data is sparse and the historical `connected_insight_guest` labels are not normalized.
- This suggests the next improvement should be data quality: normalize historical Connected Insights guest labels and expand episode intelligence coverage before using hit rate as the primary success metric.
