# Newsletter Briefing Generator v1

## Purpose

`newsletter_briefing_generator_v1.py` creates a structured editorial briefing package for a TSSE episode.

It combines:

- transcript-derived episode intelligence from `data/episodes/rank4/`
- Connected Insights recommendations from `connected_insights_recommender_v3.py`
- Startup Corner recommendations from `startup_recommender_v1.py`
- newsletter history from `data/newsletter_history.csv`

The generator does not browse the web and does not call external APIs.

## Workflow

1. Load the requested episode record by episode number.
2. Extract the editorial core:
   - guest
   - title
   - episode URL
   - primary theme
   - secondary themes
   - industries
3. Include transcript-derived founder lessons.
4. Include up to three transcript-derived notable quotes.
5. Run Connected Insights v3 for the current episode.
6. Run Startup Recommender v1 for the current episode.
7. Include community organizations identified in the episode record.
8. Return a structured briefing package.

## Inputs

Required:

```bash
python3 newsletter_briefing_generator_v1.py 117
```

Optional:

```bash
python3 newsletter_briefing_generator_v1.py 117 --format markdown
python3 newsletter_briefing_generator_v1.py 117 --connected-top-n 5 --startup-top-n 5
python3 newsletter_briefing_generator_v1.py 117 --output /tmp/briefing.json
```

## Outputs

Default output is JSON. Markdown is available for human review.

The briefing contains:

- `episode_summary`
  - guest
  - title
  - episode URL
  - primary theme
  - secondary themes
  - industries
- `founder_lessons`
- `notable_quotes`
- `connected_insights_recommendations`
  - top candidates
  - score
  - matched themes
  - matched founder lessons
  - matched industries
  - recency/frequency notes
  - rationale
- `startup_corner_recommendations`
  - top candidates
  - score
  - matched themes
  - matched industries
  - recency/frequency status
  - rationale
- `community_organizations`
- `generation_notes`

## Example

```bash
python3 newsletter_briefing_generator_v1.py 117 --format markdown
```

This creates an editorial package for David Gritz's InsurTech episode, including episode themes, founder lessons, quotes, Connected Insights candidates, Startup Corner candidates, and community organizations.

## Limitations

- The generator only works for episodes with records in `data/episodes/rank4/`.
- It inherits Connected Insights v3 limitations, including noisy historical Connected Insights labels.
- It inherits Startup Recommender v1 limitations, including sparse startup milestones and mostly unverified Sure relationship fields. Verified shared-investment relationships are prioritized when present in startup records.
- It does not generate final newsletter prose.
- It does not verify quote exactness at runtime.
- It does not retrieve new transcripts, websites, or current news.
- Editorial review remains required before publication.

## Recommended Next Improvements

- Add an option to write briefing files under a dedicated `briefings/` directory.
- Add quote-validation status to briefing output.
- Add optional editorial notes fields.
- Add a combined Markdown worksheet format for Joe/Gopi review.
- Add current non-Rank-4 episode brief support once current-episode intelligence records exist.
