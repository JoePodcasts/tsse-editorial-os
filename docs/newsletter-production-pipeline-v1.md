# Newsletter Production Pipeline v1

## Purpose

`newsletter_production_pipeline_v1.py` creates an operational TSSE newsletter production package from a transcript URL.

It connects the completed Editorial OS subsystems into one workflow:

Transcript URL -> Transcript Retrieval -> Episode Intelligence Extraction -> Connected Insights Recommendation -> Startup Recommendation -> Newsletter Briefing -> Newsletter Draft

The pipeline is designed for editorial preparation. It creates grounded briefing artifacts and a draft scaffold that Joe can edit before publication.

## Inputs

Required:

```bash
python3 newsletter_production_pipeline_v1.py <transcript_url>
```

Optional:

```bash
python3 newsletter_production_pipeline_v1.py <transcript_url> --output-dir outputs/newsletter_production/my_issue
python3 newsletter_production_pipeline_v1.py <transcript_url> --force-retrieve
python3 newsletter_production_pipeline_v1.py <transcript_url> --episode-number 188 --guest-name "Guest Name"
python3 newsletter_production_pipeline_v1.py --latest
```

The transcript URL should follow the existing TSSE podcast pattern:

```text
https://podcast.sure.ventures/episodes/<episode-slug>/transcript
```

If the URL is an episode URL rather than a transcript URL, the pipeline normalizes it by appending `/transcript`.

When `--latest` is used, the pipeline calls `episode_discovery.py`, identifies the newest episode missing newsletter coverage, and uses that episode's transcript URL automatically.

## Outputs

The pipeline writes three files:

- `briefing.json`
- `briefing.md`
- `newsletter_draft.md`

By default, output is written under:

```text
outputs/newsletter_production/<episode-slug>/
```

The output directory can be changed with `--output-dir`.

## Workflow

### Step 1: Transcript Retrieval

The pipeline reuses the existing Playwright-based retrieval path from `phase3_transcript_retrieval.mjs`.

It does not implement a second browser extraction system.

Behavior:

- If a rendered transcript already exists under `data/transcripts/`, the pipeline uses that cached `.txt` artifact by default.
- If no cached transcript exists, or if `--force-retrieve` is passed, the pipeline invokes:

```bash
node phase3_transcript_retrieval.mjs --episode-number <episode> --episode-url <episode_url>
```

Transcript validation checks:

- byte length greater than 10 KB
- at least two speaker names
- no SPA shell markers
- no legacy 3.2 KB HTML shell content

### Step 2: Episode Intelligence Extraction

The pipeline generates an episode intelligence object with:

- guest
- title
- primary theme
- secondary themes
- founder lessons
- industries
- notable quotes
- community organizations

For transcript URLs that match existing Rank 4 records, the pipeline uses the existing transcript-derived intelligence record from `data/episodes/rank4/`. This preserves the strongest available evidence and avoids modifying the canonical record.

For new URLs that do not match an existing Rank 4 record, the pipeline uses conservative local heuristic extraction from the retrieved transcript. This draft extraction is marked:

```text
extraction_method: local_heuristic_transcript_extraction
extraction_confidence: draft_requires_editorial_review
```

This fallback is intentionally limited. It avoids metadata inference and does not invent facts, but it should be treated as a first-pass editorial aid rather than final intelligence.

### Step 3: Connected Insights Recommendation

The pipeline calls `recommend_connected_insights_v3()` from `connected_insights_recommender_v3.py`.

It selects the top three recommendations and stores:

- rank
- guest name
- episode number
- score
- score breakdown
- matched themes
- matched founder lessons
- matched industries
- matched community organizations
- recency note
- frequency note
- rationale

The pipeline does not modify Connected Insights scoring logic.

### Step 4: Startup Recommendation

The pipeline calls `recommend_startups_v1()` from `startup_recommender_v1.py`.

It selects the top three recommendations and stores:

- rank
- startup name
- score
- score breakdown
- matched themes
- matched industries
- matched founder background
- notable milestones
- recency status
- frequency status
- rationale

The pipeline does not modify Startup Recommender scoring logic or startup records.

### Step 5: Briefing Artifacts

`briefing.json` is the structured source of truth for the generated package.

It includes:

- episode summary
- founder lessons
- notable quotes
- Connected Insights recommendations
- Startup Corner recommendations
- community organizations
- transcript retrieval metadata
- recommendation metadata

`briefing.md` renders the same core content in an editor-friendly format.

### Step 6: Newsletter Draft

`newsletter_draft.md` follows the TSSE newsletter structure:

- Intro
- Podcast Entries
- Connected Insights
- Startup Corner
- Community Involvement
- Editorial Notes

The draft is immediately useful as a starting scaffold, but it deliberately includes placeholders for:

- episode URL
- Connected Insights episode URL
- company URL
- missing Community Involvement detail

The draft uses recommender-generated rationale where useful, but it should be edited for final voice, specificity, and publication quality.

## Dependencies

Local data dependencies:

- `data/episodes/rank4/`
- `data/startups/`
- `data/newsletter_history.csv`
- `data/transcripts/`

Code dependencies:

- `episode_discovery.py`, when using `--latest`
- `phase3_transcript_retrieval.mjs`
- `connected_insights_recommender_v3.py`
- `startup_recommender_v1.py`

Runtime dependencies:

- Python 3
- Node.js
- Playwright, when fresh transcript retrieval is required

No external APIs are used.

## Limitations

- Fresh transcript retrieval requires network access and a working Playwright installation.
- Cached transcript validation does not prove that the remote page is still retrievable today.
- New non-Rank-4 episode intelligence extraction is heuristic and should be manually reviewed.
- The pipeline does not write or update canonical episode intelligence records.
- The pipeline does not write or update startup intelligence records.
- The pipeline does not modify recommender logic.
- Newsletter draft prose is a planning scaffold, not finished copy.
- Current facts, URLs, and organization details still require human verification before publication.

## Example

```bash
python3 newsletter_production_pipeline_v1.py \
  https://podcast.sure.ventures/episodes/tsse179-start-early-stay-consistent-steve-kim/transcript \
  --output-dir outputs/newsletter_production/validation_episode_179
```

Generated files:

- `outputs/newsletter_production/validation_episode_179/briefing.json`
- `outputs/newsletter_production/validation_episode_179/briefing.md`
- `outputs/newsletter_production/validation_episode_179/newsletter_draft.md`
