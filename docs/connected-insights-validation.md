# Connected Insights Prototype Validation

This validation report evaluates the first Connected Insights recommendation prototype against 10 historical newsletter issues.

## Test setup

- Tested issues: 66 through 75
- Input for each issue:
  - `primary_theme`: taken from `data/newsletter_history.csv` if available
  - `secondary_themes`: empty
  - `industries`: empty
- Recommendations were generated with `recommend_connected_insights(current_episode, top_n=10)`.

> Note: Most tested issues did not include structured episode metadata in `data/newsletter_history.csv`, so input was largely empty. This evaluation therefore measures prototype behavior in a minimal-data scenario.

## Results by issue

| Issue | Actual Connected Insights Guest | Top Recommendation | Top 3 Recommendations | In Top 3? |
|------:|-------------------------------|--------------------|-----------------------|:---------:|
| 66 | VCs who are deeply connected to the founders they serve will win | Global Impact from Home | Global Impact from Home, Build 12 months of barrier to entry, Venture capital is ultimately a relationship business | No |
| 67 | Build Companies Without Stretch Marks | Global Impact from Home | Global Impact from Home, Build 12 months of barrier to entry, Venture capital is ultimately a relationship business | No |
| 68 | What Makes Founders Stand Out | Global Impact from Home | Global Impact from Home, Build 12 months of barrier to entry, Venture capital is ultimately a relationship business | No |
| 69 | Endurance Is the New Alpha | Global Impact from Home | Global Impact from Home, Build 12 months of barrier to entry, Venture capital is ultimately a relationship business | No |
| 70 | The Geometry Framework | Global Impact from Home | Global Impact from Home, Build 12 months of barrier to entry, Venture capital is ultimately a relationship business | No |
| 71 | Look where others are not looking | Global Impact from Home | Global Impact from Home, Build 12 months of barrier to entry, Venture capital is ultimately a relationship business | No |
| 72 | Start with Your Childhood, Not Your Resume | Global Impact from Home | Global Impact from Home, Build 12 months of barrier to entry, Venture capital is ultimately a relationship business | No |
| 73 | Conviction in the absence of traditional metrics | Global Impact from Home | Global Impact from Home, Build 12 months of barrier to entry, Venture capital is ultimately a relationship business | No |
| 74 | Competition Is Irrelevant When You're Building Infrastructure | Global Impact from Home | Global Impact from Home, Build 12 months of barrier to entry, Venture capital is ultimately a relationship business | No |
| 75 | Leadership Is More Human Than Corporate | Global Impact from Home | Global Impact from Home, Build 12 months of barrier to entry, Venture capital is ultimately a relationship business | No |

## Observations

- The prototype returned the same top 3 recommendations for every tested issue.
- All 10 actual Connected Insights guests were missing from the top 3.
- This outcome was driven by minimal input metadata; the prototype defaulted to a baseline ranking dominated by historical frequency and recency.
- The prototype did not successfully surface the historical guest selected in the original newsletter issue under this test setup.

## Hit rate summary

- Total issues tested: 10
- Actual guest in top 3: 0
- Hit rate: 0%

## Key takeaways

1. The prototype is currently too weak when episode metadata is absent.
2. Historical recency/frequency alone is not enough to recover editorial choices for these issues.
3. Better episode characteristics (primary theme, secondary themes, industries) are needed for meaningful recommendations.
4. The validation exposed that the system should prioritize stronger theme matching and candidate metadata alignment before relying on raw recency/frequency.

## Recommended next improvements

- Populate episode intelligence records for the tested issues.
- Use actual primary and secondary themes in recommendations.
- Normalize and canonicalize historical Connected Insights guest labels.
- Enhance scoring with theme overlap or categorical matching.
- Add a small manual evaluation step for the first prototype outputs.
