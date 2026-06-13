# Automatic Episode Discovery v1

## Purpose

Automatic Episode Discovery v1 lets TSSE Editorial OS identify the next podcast episode requiring newsletter production without manually supplying a transcript URL.

The implementation lives in:

- `episode_discovery.py`
- `newsletter_production_pipeline_v1.py --latest`

## Workflow

### Standalone Discovery

Run:

```bash
python3 episode_discovery.py
```

This creates:

```text
discovery_report.json
```

The report includes:

- newest published episode
- latest episode already represented in `data/newsletter_history.csv`
- episodes missing newsletter coverage after the latest represented episode
- recommended next episode for newsletter generation

### Full Production Pipeline

Run:

```bash
python3 newsletter_production_pipeline_v1.py --latest
```

This performs:

1. Discover newest published TSSE episode.
2. Compare discovered episodes against newsletter history.
3. Select the newest episode missing newsletter coverage.
4. Retrieve the transcript through the existing Playwright retrieval path.
5. Generate episode intelligence for the current briefing context.
6. Run Connected Insights v3.
7. Run Startup Recommender v1.
8. Write newsletter production artifacts.

Outputs:

- `briefing.json`
- `briefing.md`
- `newsletter_draft.md`
- `discovery_report.json`

By default, production outputs are written under:

```text
outputs/newsletter_production/<episode-slug>/
```

The output directory can be overridden:

```bash
python3 newsletter_production_pipeline_v1.py --latest --output-dir outputs/newsletter_production/latest
```

## Discovery Source

The TSSE podcast website is a JavaScript-rendered Simplecast site. The static HTML at `https://podcast.sure.ventures/episodes` is only a SPA shell.

Discovery v1 uses the same official Simplecast API endpoints used by the rendered podcast website:

- `https://api.simplecast.com/sites/search`
- `https://api.simplecast.com/podcasts/<podcast_id>/episodes`

This avoids creating a separate browser scraper for episode discovery.

## Newsletter History Comparison

Discovery compares published podcast episodes against:

```text
data/newsletter_history.csv
```

The comparison uses the `featured_episode` column.

The current logic treats the highest numeric `featured_episode` value as the latest episode already represented in newsletter history. Episodes with higher episode numbers are considered missing newsletter coverage.

## Recommended Next Episode Rule

Version 1 recommends the newest episode missing newsletter coverage.

Example from validation:

- newest published episode: Episode 190
- latest episode represented in newsletter history: Episode 188
- missing coverage: Episodes 190 and 189
- recommended next episode: Episode 190

This rule matches the `--latest` command name. If the editorial process prefers chronological catch-up, Version 2 should add an option to choose the oldest missing episode instead.

## Assumptions

- The Simplecast API remains available without authentication for public podcast site data.
- Episode numbers in Simplecast are authoritative.
- `data/newsletter_history.csv` uses numeric `featured_episode` values when an issue has already covered an episode.
- Newsletter coverage should be inferred from `featured_episode`, not from Connected Insights or Startup Corner fields.
- The newest missing episode is the right production target for `--latest`.
- Transcript pages continue to follow the podcast site pattern:

```text
https://podcast.sure.ventures/episodes/<slug>/transcript
```

## Limitations

- Discovery requires network access.
- Fresh transcript retrieval requires Playwright and Chromium.
- In the Codex sandbox, live discovery and Playwright retrieval may require elevated execution approval.
- Newsletter history has incomplete `featured_episode` data for older issues, so discovery only treats episodes after the latest represented episode as current missing coverage.
- New non-Rank-4 episodes do not have curated transcript-derived intelligence records.
- For non-Rank-4 episodes, `newsletter_production_pipeline_v1.py` uses conservative local heuristic extraction. This can produce rough founder lessons and themes that require editorial review.
- Guest and title metadata are taken from discovery for `--latest`, but deeper intelligence still depends on transcript heuristics unless a curated record exists.

## Validation Process

Validation performed on June 13, 2026:

1. Ran syntax validation:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/tsse_pycache python3 -m py_compile episode_discovery.py newsletter_production_pipeline_v1.py
```

2. Ran standalone discovery:

```bash
python3 episode_discovery.py --output discovery_report.json
```

Discovery found:

- newest episode: Episode 190, David Zhou, `Develop a Point of View and Let Your Advantage Compound`
- latest episode represented in newsletter history: Episode 188
- missing coverage count: 2
- missing episodes: 190 and 189
- recommended next episode: Episode 190

3. Ran the integrated production command:

```bash
python3 newsletter_production_pipeline_v1.py \
  --latest \
  --force-retrieve \
  --output-dir outputs/newsletter_production/latest_discovery_run_fixed
```

Generated:

- `outputs/newsletter_production/latest_discovery_run_fixed/briefing.json`
- `outputs/newsletter_production/latest_discovery_run_fixed/briefing.md`
- `outputs/newsletter_production/latest_discovery_run_fixed/newsletter_draft.md`
- `outputs/newsletter_production/latest_discovery_run_fixed/discovery_report.json`

4. Validated generated JSON:

```bash
python3 -m json.tool outputs/newsletter_production/latest_discovery_run_fixed/briefing.json
python3 -m json.tool outputs/newsletter_production/latest_discovery_run_fixed/discovery_report.json
```

5. Confirmed fresh transcript retrieval:

- retrieval source: `playwright_rendered_transcript`
- episode: 190
- guest: David Zhou
- transcript validation: valid
- HTML shell detected: false
- retrieval attempts: 1

## Validation Notes

The single-command path works end to end.

The generated Episode 190 newsletter draft is structurally complete and uses the correct discovered episode metadata, but the founder lessons reflect the known limitation of heuristic extraction for new non-Rank-4 episodes. Joe should review and rewrite the episode intelligence sections before publication.

## Future Improvements

- Add `--latest-strategy newest|oldest` to choose between newest missing and chronological catch-up.
- Persist discovery run history under `outputs/episode_discovery/`.
- Add confidence flags to heuristic episode intelligence fields.
- Add a manual review worksheet for new-episode intelligence before draft generation.
- Improve guest extraction from Simplecast descriptions for edge cases.
- Add an option to stop after discovery without generating production materials.
