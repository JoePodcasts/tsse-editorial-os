# Newsletter Briefing v1 Evaluation Plan

## Purpose

Newsletter Briefing Generator v1 should be evaluated as an editorial planning assistant. The goal is to determine whether the generated package helps Joe/Gopi plan a newsletter issue faster and with better context.

## Evaluation Goals

The evaluation should answer:

- Does the episode summary capture the issue's likely editorial center?
- Are founder lessons useful and clear?
- Are notable quotes usable as newsletter raw material?
- Are Connected Insights recommendations plausible?
- Are Startup Corner recommendations plausible?
- Are community organizations surfaced correctly?
- Is the package easier to use than manually opening multiple files and tools?

## Evaluation Set

Use 8-12 episodes:

- 3 FinTech or insurance-heavy episodes.
- 2 AI or frontier-technology episodes.
- 2 founder-development or early-stage company-building episodes.
- 1 emerging-manager or LP-oriented episode.
- 1 episode with named community organizations.
- Optional: 1 edge case with sparse community organization or quote data.

Suggested initial episodes:

- Episode 75: Dan Rosen.
- Episode 117: David Gritz.
- Episode 167: Geoff Ralston.
- Episode 179: Steve Kim.
- Episode 12: Ravi Belani.

## Review Workflow

1. Generate a briefing:

```bash
python3 newsletter_briefing_generator_v1.py 117 --format markdown --output /tmp/briefing_117.md
```

2. Give the briefing to reviewers without asking them to inspect source JSON first.

3. Reviewers rate each section:

| Rating | Meaning |
|---:|---|
| 5 | Ready to use with minimal editing |
| 4 | Useful with light editorial review |
| 3 | Plausible but needs checking |
| 2 | Weak or incomplete |
| 1 | Not useful |

4. Reviewers add notes on missing context, wrong emphasis, or recommendation issues.

## Review Fields

Per briefing:

- Episode summary rating:
- Founder lessons rating:
- Notable quotes rating:
- Connected Insights usefulness rating:
- Startup Corner usefulness rating:
- Community organization usefulness rating:
- Overall usefulness rating:
- Most useful section:
- Least useful section:
- Missing information:
- Would use for newsletter planning? Yes/No:
- Notes:

## Success Metrics

Primary metrics:

- Average overall usefulness rating.
- Percentage of briefings reviewers would use for newsletter planning.
- Percentage of briefings where at least one Connected Insights candidate is publishable.
- Percentage of briefings where at least one Startup Corner candidate is publishable.

Secondary metrics:

- Time saved versus manual review.
- Frequency of missing or misleading quote context.
- Frequency of overbroad AI, FinTech, or Venture Capital matches.
- Frequency of community organization gaps.

## Known Risks

- Briefing quality depends on episode intelligence quality.
- Startup Corner recommendations are early v1 and need human review.
- Connected Insights recommendations remain lexical and can miss semantic connections.
- Newsletter history normalization gaps can affect recency and frequency notes.
- Older Phase 1 quote exactness gaps may affect quote confidence.

## Feedback Loop

Capture evaluation results in a structured file:

```csv
episode_number,summary_rating,lessons_rating,quotes_rating,connected_rating,startup_rating,community_rating,overall_rating,would_use,notes
```

Use the feedback to improve:

- briefing section ordering
- quote selection
- recommendation thresholds
- Markdown formatting
- future editorial note fields
