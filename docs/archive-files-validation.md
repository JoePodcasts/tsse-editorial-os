# Archive files and retrieval refinement validation

Historical phase report. Current weekly synchronization and freshness behavior are documented in [the operations guide](archive-weekly-sync.md) and [current validation](archive-weekly-sync-validation.md).

Validated 26 October 2026 against the existing published archive. Portable-deliverable validation ran before frontend edits. No archive source/export rewriting, audio checking, speaker QA, scheduling, semantic search or newsletter UI was introduced.

## Portable deliverables

| Check | Result |
|---|---|
| Published catalogue / CSV | 195 episodes / 195 rows, one row per canonical episode |
| Markdown files | 195, deterministic remote UUID filenames |
| UTF-8 | CSV and all 195 Markdown files decode strictly |
| Metadata / published notes / transcript | Present in all 195 files |
| Transcript fidelity | Zero word changes; zero timestamp changes |
| Timestamped source transcripts | 116; remaining 79 do not gain timestamps |
| CSV size | 267,242 bytes |
| Markdown total size | 13,940,050 bytes |
| Full-library ZIP | 195 files; 3,918,604 bytes (3.74 MiB) |

The fidelity check compares each preserved HTML block to its original source and compares transcript projection non-whitespace token sequences and timestamp sequences. The complete Markdown document must also match the current reproducible exporter. Formatting-only differences are acceptable under the task definition; no wording/timestamp exceptions were found. This checks the published source, not audio accuracy.

CSV fields (33, unchanged):

`episode_id`, `remote_id`, `rss_guid`, `episode_number`, `season_number`, `title`, `published_at`, `date`, `duration_seconds`, `duration_display`, `url`, `audio_url`, `episode_type`, `media_mime_type`, `speakers_json`, `speaker_status`, `guest_names_json`, `summary`, `artwork_url`, `public_presence`, `source_updated_at`, `show_notes_status`, `transcript_status`, `structured_transcript_status`, `transcript_available`, `show_notes_available`, `timestamps_available`, `speaker_labels_available`, `intelligence_available`, `newsletter_content_available`, `social_content_available`, `markdown_path`, `metadata_revision`

These expose episode identity/number, official title, publication date, duration, URLs, format/type, source speaker labels and content availability. The existing nullable or unverified fields are not recast as verified guest identities.

The ZIP is created in memory on request with Python `zipfile`, sorted entry names, fixed 1980 timestamps, Unix 0644 permissions and deflate level 6. Two independent builds were byte-identical in this runtime; compressed bytes may depend on the zlib implementation across runtime versions. It contains only `episodes/<uuid>.md`. Each original document's preserved source HTML and source-reference section is intentionally retained. No separate manifest, source files, index or reports are bundled.

ZIP SHA-256: `adec24a037137e50cffcfbd0b8b828e0f81522c98b0e41040ae507be86e9ae83`.
CSV SHA-256: `13749bbd134cb2b238722ebb18ac58dcc4207cc03e7c11fe517e3d59b7298b23`.
Full per-file hashes and counts: [portable validation JSON](../archive/reports/portable-files-validation.json).

## Frontend behavior

- Home keeps Content Archive, search, coverage, the restrained Archive Files entry, then browse/results.
- Archive Files explains the actual CSV fields/count/UTF-8 and Markdown contents, with CSV and ZIP downloads.
- Markdown browsing lists all 195 real episodes in pages of 24, with newest/oldest/episode-number sorting, view and individual-download actions.
- Episode File shows the actual generated Markdown with its original UUID filename, size, integrity disclosure and metadata/notes/transcript/reference section navigation. Source HTML is literal text. No frontend-specific export is generated.
- Overview retains summary, transcript, notes and scoped search, adding a substantive Episode file panel. Readers also have file access.
- Grouping shows each episode once, with metadata/notes/transcript groups and expandable passages. Episode order is the best-match order; source sections follow first occurrence; within each section original passage rank is retained. The backend lexical ranking is unchanged. Counts describe loaded results, with 30 initially and up to 100.
- Search origin travels in the URL. Query, source filter, episode scope, loaded limit and expanded groups survive passage → overview → file → Back to search results, including reloads. Pixel scroll position is not explicitly restored; loading more results resets expanded groups.
- Transcript context keeps the query, return link and episode overview link visible near the exact highlighted passage.
- Notes paragraph links use a quiet arrow at rest, appear on hover/focus and remain keyboard-operable.

## Portfolio path and real queries

Start at Content Archive → coverage → Archive Files → CSV facts/download → browse 195 Markdown files → episode 195 file → metadata, notes, transcript section. Then return to search and use **customer discovery** → show episode 174 and 16 groups → open episode 16 at **00:17:37** (or episode 174 at **00:20:17**) → exact highlighted transcript → episode overview → Episode file.

Customer discovery is the strongest visual example: a short, intelligible concept, 12 distinct episodes, timestamped matches in the first two groups, and coverage across 2020 and 2025. Episode 16's four matches demonstrate expansion without repeated top-level episode titles.

| Query | Episodes in initial results | Source matches | Assessment |
|---|---:|---:|---|
| customer discovery | 12 | 16 | Best recording choice; top two results have source timestamps |
| founder market fit | 16 | 30+ | Broad coverage and multiple source types; initial results truncated |
| contrarian | 17 | 30+ | Broad coverage; first matches are short show-note excerpts |
| capital efficient | 14 | 17 | Good alternative; source spelling includes hyphenated capital-efficient |

Counts are from actual initial browser retrieval, not claimed full-corpus totals for truncated queries. The additional deep-link screenshot shows episode 191's exact **00:23:15** passage for “choosing a partner in life”, with its source filter preserved.

## Validation

- **84 archive tests passed**, including all prior archive/search tests and 12 portable-file tests.
- **13 HTTP tests passed**, including exact CSV and Markdown attachments, actual Markdown JSON, allowlisting, and every ZIP member matching its original bytes.
- **28 existing browser checks passed** after adapting the test selector to grouped markup.
- **49 new browser checks passed**: actual CSV/MD/ZIP downloads and hashes; all 195 file rows; sort modes; exact Markdown DOM hash; section navigation; all four real concept queries; grouped source types; expansion; query/filter/return persistence; passage reload; notes keyboard links; no overflow at 375/768/1366 px across six major views; no console warnings/errors.
- Final failures: **0**. During implementation the existing coverage expectation was updated for the added Markdown count; one new browser assertion was corrected to use the artifact's real “Episode metadata” heading. Neither required modifying source documents.
- Real screenshots visually inspected. Downloaded files were verified from the browser's returned download paths. The application remains local; no hosting or publishing was performed.

Evidence: [browser results](screenshots/archive-files/browser-validation.json), [portable validation](../archive/reports/portable-files-validation.json). Re-run Python validation with:

```sh
python3 -B archive_files.py --report archive/reports/portable-files-validation.json
python3 -B -m unittest discover -s tests/archive -v
python3 -B -m unittest discover -s tests/frontend -v
```

Run the browser suites through documented Codex `cua_repl` handles with the local server running; see [frontend documentation](archive-frontend.md). No added production or browser-driver dependencies.

## Screenshots

All captures show the real local application with TSSE data.

1. [Archive home](screenshots/archive-files/home.png)
2. [Archive Files](screenshots/archive-files/archive-files.png)
3. [Markdown library browse](screenshots/archive-files/markdown-library.png)
4. [Actual Markdown document](screenshots/archive-files/markdown-file.png)
5. [Grouped cross-episode search](screenshots/archive-files/grouped-search.png)
6. [Transcript deep link](screenshots/archive-files/transcript-deep-link.png)
7. [Updated episode overview](screenshots/archive-files/episode-overview.png)

Additional evidence: [Markdown transcript section](screenshots/archive-files/markdown-transcript.png), [founder market fit](screenshots/archive-files/search-founder-market-fit.png), [contrarian](screenshots/archive-files/search-contrarian.png), [capital efficient](screenshots/archive-files/search-capital-efficient.png), [mobile files](screenshots/archive-files/mobile-files.png), [tablet library](screenshots/archive-files/tablet-library.png).

Ready for user review. Start the preview with `python3 -B archive_web.py` and open `http://127.0.0.1:8765`.
