# TSSE discovery notebook · phase 1

Start with the [catalogue for review](proposed/review.md), [coverage report](proposed/coverage.md), [review guide](review-guide.md) and [Phase 2 specification](phase-2.md). This directory contains a private editorial proposal. Every theme and association awaits human judgment.

## Archive audit

The November 10 sync at revision `3b7ad8277ddf548cef22b787cd69c28e191ea866` added one episode and kept 196 unchanged. The 197 present records in `archive/catalogue.jsonl` are the publication inventory. Each Simplecast episode ID joins its official metadata, transcript and published show notes in `archive/manifest.json`. All 197 have all three. The manifest points to immutable HTML under `archive/sources` and its UTF-8 projection in `archive/derived/text`. The 56 legacy transcript/intelligence records overlap this collection.

Reconstructing the production segmenter yielded 18,770 transcript passages. The archive report also counts 2,231 show-note passages and 21,986 searchable documents including metadata. Of 118 transcripts containing bracketed times, 117 contain a positive time within the audio duration. Episode 1 contains only zero. In 13 episodes some markers exceed the listed duration. See the affected IDs in the [manifest](proposed/manifest.json). Metadata duration is a check, not an audio alignment. All 197 contain syntactically parseable source labels. The archive flags 35 with ambiguous colon prefixes, six unusual formats and four with multiple turns in one HTML paragraph. Categories overlap. A paragraph boundary or a long turn can leave a passage unlabelled.

`archive_sync.py` maintains the catalogue, accepted sources, projections and stable provider identities. `archive_library.py` validates source identity and materializes exports. `archive_search.py` splits on turn/paragraph boundaries, then on sentences or whitespace around 1,800 characters. Offsets count Unicode code points with exclusive ends. A lexical-v2 ID hashes episode, source kind and locator (including source and projection hashes). SQLite FTS5 ranks lexical matches; no embedding index is required. `archive_web.ArchiveApp` resolves the provider ID and selected passage in the transcript reader. `archive_public.py` removes local paths from public responses. The Connected Insights recommender scores overlap among legacy editorial records and also accounts for newsletter history. It does not establish a quotation or cover the full official corpus.

The Tuesday 06:30 America/Los_Angeles workflow restores the last successful state, stages and validates synchronization, runs regression suites, persists changed content and uploads operational status. A content update can invoke the deployment workflow, which validates a staged build before promotion. Phase 1 runs independently of both. The repository’s archive, frontend HTTP and deployment suites cover ingestion, retrieval, source links and packaging.

## Discovery and repeatability

1. Read the full catalogue in publication order. Compare repeated questions in episode titles with summary bigrams counted once per episode (`corpus.py`). “Venture capital” appears in 96 summaries and “Silicon Valley” in 38. Neither frequency alone tells an editor what different guests actually argue. Contradictory portfolio titles prompted a search for the rationale behind breadth and concentration. Recurring hiring, pitch, customer and financing questions furnished other leads.
2. Screen every official transcript passage. `discover.py` records the exact regex vocabulary distilled from that first pass. A sentence-like exact span of 50–650 characters must match both of the first two signal groups. The rank sums distinct matching strings per group, including the optional third group. This is retrieval priority only. Short or interrupted turns, paraphrases and multi-sentence arguments can be missed. Titles and show notes orient discovery; transcript passages establish associations.
3. Inspect high-ranked excerpts across episodes. The initial comparison sorted by descending rank, passage ID and excerpt, kept one result per episode per theme, and inspected up to twenty per theme; the full search output remains reproducible. The initial sample excluded explicitly labelled host passages. A second read targeted labelled voices, divergent cases and titles missed by sentence screening, including episodes 53, 112, 139, 174 and 197. Known guest names in the inventory come from matching the published summaries for retained episodes. A null guest list elsewhere means unindexed. A named episode guest is never a fallback speaker label.
4. Retain a theme when at least eight distinct conversations yield passages worth comparing, with a recurring question, a plausible editorial use and an identifiable boundary. Keep 8–15 excerpts per theme. Direct mechanisms, examples and explicit opposing arguments are strong; a boundary condition or secondary illustration lacking the central argument is contextual. Supporting, qualifying and contrasting describe the excerpt’s position, independently of its strength. Each association links to a specific reason in the selections table. No numeric confidence or claims of saturation.
5. Version 1.0 freezes the interpretive choices in the catalogue, relationships and selections. Nine themes survived this pass. AI-assisted reading and annotation followed the Phase 1 brief in this chat; exact model revision and sampling settings were unavailable. Generating new interpretations will vary. Replaying the recorded decisions is deterministic and uses only the Python standard library and repository code, with zero incremental external API fees. The archive fingerprint and curation files in Git identify the inputs.

Run from the repository root (project Python 3.12):

```sh
python3 research/themes/corpus.py
python3 research/themes/discover.py > /tmp/tsse-theme-candidates.jsonl
python3 research/themes/build.py --check
python3 -m unittest discover -s research/themes -p 'test_*.py'
```

To regenerate the proposed outputs after editing curation inputs, run `python3 research/themes/build.py`. That command writes only inside `research/themes/proposed`. Use a feature branch for each new review version. The generator rejects approved records and fails on missing passage IDs. Changes to source text or segmentation create new passage IDs. Reopen the updated source, select the span again and submit a replacement explicitly. Never transplant an old offset or automatically carry approval over to new evidence.

## Data contract · version 1

- `catalogue.json` owns stable theme slugs, editorial interpretations, possible assignments, review identity, evidence date and discovery version.
- `selections.json` maps theme and passage IDs to an exclusive code-point range relative to the passage, a classification, strength and rationale. `relationships.json` pairs two themes with one selected passage from each and the interpreted connection.
- `episode-guests.json` supplies summary-grounded episode guest names. `proposed/inventory.json` is the consumer projection keyed by canonical episode ID, including title, number, date, URL, guests, screen-hit count and outcome for every published record. Regenerate metadata from the catalogue.
- `proposed/associations.json` joins each theme–episode pair to its role, strength and passage IDs. Resolve the reason through the matching selection. `proposed/evidence.json` stores the exact excerpt once per passage, a local source label or “unknown”, source-verification status, and the existing internal reader route. Join its episode ID to inventory for number, title and original URL. A time is recorded only when it starts the excerpt. End times are null. No fabricated source, identity or end boundary is needed.
- `proposed/manifest.json` records current input and output counts, timestamp exceptions, schema version, segmenter and archive fingerprint. The Markdown reports are generated views. None of these research files is a production input.

## Extension after a weekly sync

After a successful content sync, a future independent job could compare manifest hashes, screen changed or new episodes, then open a proposal with candidate excerpts and a diff against the last reviewed version. Require an editor to resolve changed IDs and approve additions. Preserve signed decisions keyed to theme, discovery version and exact evidence fingerprint. A future publication build should consume only a separately approved immutable release. Keep rejected and superseded revisions in Git. No scheduling or deployment changes are required for this research pass.
