# Startup Recommender v1 Evaluation Plan

## Purpose

Startup Recommender v1 should be evaluated as an editorial support tool. The goal is not to prove that it exactly reproduces past Startup Corner choices, because the historical data is incomplete and the current startup intelligence layer did not exist when earlier newsletters were written.

## Evaluation Goals

The review should answer:

- Are the recommended startups relevant to the current episode?
- Does the rationale make the connection easy to understand?
- Does the engine avoid overusing recently featured startups?
- Does it surface fresh but relevant companies from the approved watchlist?
- Does the output help Joe/Gopi choose a Startup Corner candidate faster?

## Evaluation Set

Use 10-15 test cases:

- 5 Rank 4 episodes with clear industry fit, such as FinTech, InsurTech, AI, supply chain, or construction.
- 3 recent newsletter contexts where Startup Corner was already chosen.
- 3 synthetic editorial briefs for likely future issues.
- 2 edge cases with broad venture-capital themes and weak startup relevance.

Suggested initial Rank 4 test episodes:

- Episode 75: FinTech opportunity selection.
- Episode 117: InsurTech and insurance customer promise.
- Episode 167: AI safety.
- Episode 73: pre-seed/product-market fit.
- Episode 179: emerging manager asset allocation.

## Review Workflow

1. Run v1 for each evaluation item:

```bash
python3 startup_recommender_v1.py --current-episode 117 --top-n 5
```

2. Give reviewers the top 5 recommendations with:

- startup name
- score
- matched themes
- matched industries
- recency status
- frequency status
- plain-English rationale

3. Reviewers rate each candidate:

| Rating | Meaning |
|---:|---|
| 5 | Excellent Startup Corner candidate |
| 4 | Strong and usable |
| 3 | Plausible but not preferred |
| 2 | Weak connection |
| 1 | Not relevant |

4. Reviewers mark whether at least one of the top 3 is publishable.

5. Reviewers select the best candidate among the top 5 and add notes.

## Review Fields

For each recommendation:

- Strong candidate? Yes/No:
- Plausible candidate? Yes/No:
- Newsworthy enough? Yes/No:
- Would use in newsletter? Yes/No:
- Notes:

For each test episode:

- Best recommendation among top 5:
- Was at least one top-3 recommendation publishable? Yes/No:
- Did recency/frequency penalties feel appropriate? Yes/No:
- Missing obvious startup:
- Notes:

## Metrics

Primary metrics:

- Top-1 average editorial rating.
- Top-3 contains at least one publishable startup.
- Top-5 contains at least one publishable startup.
- Rationale usefulness rating.

Secondary metrics:

- Rate of over-recommending generic AI matches.
- Rate of over-recommending never-featured startups with weak relevance.
- Rate of suppressing recently featured but highly relevant startups too aggressively.
- Diversity of startups recommended across the evaluation set.

## Known Risks

- Historical Startup Corner usage is not a clean benchmark because older rows include aliases, headline-style values, and non-watchlist companies.
- The current startup records have uneven milestone and founder coverage.
- Sure relationship and guest relationship fields remain unverified, so v1 cannot score those signals.
- Generic industry labels can make broad matches look stronger than the editorial connection really is.

## Feedback Loop

After the first review pass, capture feedback in a CSV or JSON file:

```csv
evaluation_id,current_episode,recommended_startup,rank,score,rating,publishable,selected,notes
```

Use the feedback to tune:

- generic industry dampening
- AI/FinTech/InsurTech synonym handling
- recency penalty thresholds
- frequency penalties
- milestone weighting

Do not tune weights until reviewers have identified recurring failure modes.
