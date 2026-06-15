# Automatic Episode Intelligence Generation v1

## Purpose

Automatic Episode Intelligence Generation v1 creates a structured episode intelligence record whenever TSSE Editorial OS processes a newly discovered episode.

The implementation lives in:

- `episode_intelligence_generator.py`
- `newsletter_production_pipeline_v1.py`

Newly discovered episode records are stored in the active episode intelligence corpus:

```text
data/episodes/active/
```

This makes `data/episodes/active/` the primary storage location for current and newly discovered episode intelligence. The Rank 4 directory remains a curated subset used by Connected Insights as its recommendation candidate pool.

## Inputs

Required inputs:

- transcript URL
- episode number
- guest name

Optional input:

- title
- explicit transcript path
- output directory

Standalone command:

```bash
python3 episode_intelligence_generator.py \
  --transcript-url https://podcast.sure.ventures/episodes/tsse-190-develop-point-of-view-david-zhou/transcript \
  --episode-number 190 \
  --guest-name "David Zhou" \
  --title "Develop a Point of View and Let Your Advantage Compound"
```

Output:

```text
data/episodes/active/episode_190.json
```

## Generated Schema

Active records follow the established episode intelligence schema:

- `episode_number`
- `title`
- `guest_name`
- `episode_url`
- `primary_theme`
- `secondary_themes`
- `founder_lessons`
- `industries`
- `community_organizations`
- `notable_quotes`

## Pipeline Integration

The production workflow now runs:

Discovery -> Transcript Retrieval -> Episode Intelligence Generation -> Briefing -> Newsletter Draft

When `newsletter_production_pipeline_v1.py --latest` discovers a new episode:

1. `episode_discovery.py` identifies the next episode missing newsletter coverage.
2. The pipeline retrieves the rendered transcript using the existing Playwright path.
3. `episode_intelligence_generator.py` creates and saves an active intelligence record in `data/episodes/active/`.
4. The pipeline uses the saved active record as the current episode context.
5. Connected Insights v3 and Startup Recommender v1 run against that current context.
6. The pipeline writes `briefing.json`, `briefing.md`, and `newsletter_draft.md`.

The generated record path is also stored in `briefing.json` under:

```json
"episode_intelligence_record": {
  "source": "episode_intelligence_generator.py",
  "path": "...",
  "status": "active"
}
```

## Extraction Method

Version 1 is deterministic and local. It does not call external APIs, language models, or metadata inference systems.

The generator:

- parses speaker turns from the rendered transcript
- skips TSSE intro and outro boilerplate
- extracts guest-centered sentences
- scores recurring theme and industry keywords
- derives founder lessons from advice-oriented transcript passages
- extracts notable quote candidates from guest passages
- identifies community organization mentions

This is intentionally conservative. It creates a usable draft intelligence record, but it is not a substitute for the curated human-reviewed Rank 4 process.

## Validation

Validation was run on Episode 190, David Zhou.

### Generated Record

Command:

```bash
python3 episode_intelligence_generator.py \
  --transcript-url https://podcast.sure.ventures/episodes/tsse-190-develop-point-of-view-david-zhou/transcript \
  --episode-number 190 \
  --guest-name "David Zhou" \
  --title "Develop a Point of View and Let Your Advantage Compound"
```

Generated:

```text
data/episodes/active/episode_190.json
```

Record summary:

- episode number: 190
- title: Develop a Point of View and Let Your Advantage Compound
- guest: David Zhou
- primary theme: LP education and disciplined emerging manager evaluation
- community organization: Friends of Children with Special Needs

### Pipeline Validation

Command:

```bash
python3 newsletter_production_pipeline_v1.py \
  --latest \
  --output-dir outputs/newsletter_production/latest_intelligence_generation_validation
```

Generated:

- `outputs/newsletter_production/latest_intelligence_generation_validation/briefing.json`
- `outputs/newsletter_production/latest_intelligence_generation_validation/briefing.md`
- `outputs/newsletter_production/latest_intelligence_generation_validation/newsletter_draft.md`
- `outputs/newsletter_production/latest_intelligence_generation_validation/discovery_report.json`

### Comparison Result

The active intelligence record was compared with the briefing output.

Matching fields:

- `episode_number`
- `title`
- `guest_name`
- `primary_theme`
- `secondary_themes`
- `founder_lessons`
- `notable_quotes`
- `community_organizations`

The briefing also includes the active record path:

```text
data/episodes/active/episode_190.json
```

## Known Limitations

- Active intelligence generated from new episodes is draft quality and requires editorial review.
- Theme and industry extraction are keyword-based.
- Founder lessons are derived from high-scoring advice passages and may need tightening.
- Notable quotes are transcript excerpts, but quote selection is not yet as editorially refined as human-curated Rank 4 records.
- Community organization extraction can still require manual verification.
- Active records are not automatically added to the Connected Insights candidate pool; Rank 4 remains the curated candidate subset.

## Recommended Next Improvements

- Add field-level confidence notes.
- Add quote validation metadata with transcript file and approximate location.
- Add a human review worksheet for active intelligence records.
- Add a promotion workflow from `data/episodes/active/` to curated subsets such as Rank 4 when appropriate.
- Improve theme extraction with a controlled TSSE theme vocabulary.
- Add a validation script that checks generated records for required fields and non-empty values.
