# Phase 2 archive ingestion and retrieval validation

Historical phase report. Current weekly synchronization and freshness behavior are documented in [the operations guide](archive-weekly-sync.md) and [current validation](archive-weekly-sync-validation.md).

Validated 26 October 2026 against the complete public TSSE catalogue. The implementation includes incremental source ingestion, offline parsing, a portable Markdown/CSV library, natural source passages, and a SQLite lexical-search CLI. No frontend, weekly schedule, semantic retrieval or publishing was implemented.

## Coverage

| Measure | Actual coverage |
|---|---:|
| Official published episodes | 195 / 195 (100.0%) |
| Normalized catalogue records | 195 / 195 (100.0%) |
| Searchable metadata records | 195 / 195 (100.0%) |
| Official published show notes | 195 / 195 (100.0%) |
| Official transcripts | 195 / 195 (100.0%) |
| Transcripts with timestamps | 116 / 195 (59.5%) |
| Speaker-labelled transcripts | 195 / 195 (100.0%) |
| Transcripts with at least one parseable explicit label | 195 / 195 (100.0%) |
| Markdown episode documents | 195 / 195 (100.0%) |
| Intelligence-linked episodes | 57 / 195 (29.2%) |

The index contains **18,595 transcript passages** and **2,210 show-note passages** from 195 episode note documents. It has 21,780 indexed field/passage rows in total. Field/passage counts are not episode counts.

All 195 current detail sources expose both notes and transcripts: **0 absent transcripts, 0 absent show notes**. There are **79 untimed transcripts**. Metadata membership remains independent of source availability; missing/failed-source behavior is covered by controlled tests rather than falsely claiming live examples where none occurred.

Local/provisional episode 196 remains outside official catalogue/search membership. Existing Rank 4/active intelligence attaches separately; the 57 intelligence links do not restrict browse/search coverage. No newsletter history mapping or recommendation scoring was changed.

## Ingestion and resumability

The full expansion fetched 190 previously missing detail responses and reused the five preserved pilot responses. Requests were sequential with minimum 0.5-second spacing between HTTP attempts. The measured 190 HTTP attempts equal 190 queued episodes; no detail retries or retrieval failures occurred. The preceding metadata refresh used a site lookup and two list pages.

The reported full-ingestion duration was **508.706 seconds** (about 8 minutes 29 seconds). This timing ends after materialization/validation; final reporting and directory publication add small overhead.

The final unchanged ingestion run queued no episodes, reused all 195 accepted details and made **0 HTTP requests**. Its reported ingestion work took **1.179 seconds**, and the complete measured function call including report generation/publication took **2.474 seconds**. All **2,015 non-report files** retained the same file set, bytes and modification times.

Durable-checkpoint tests simulate interruption before publication and during a refresh; resumed runs replay matching source responses and preserve unprocessed checkpoints. Failed attempts have a retry cooldown. Successful empty fields are not hammered on immediate reruns; a bounded refresh policy can revisit them later.

## Source integrity and transcript structure

- Actual source retrieval failures: **0**. Source/export validation failures: **0**.
- All 195 source identities, HTML fields, text projections, source hashes and generated exports passed offline validation.
- The conservative parser upgrade was performed by `archive_library.py reparse` with **0 HTTP requests**. All **1,031 preserved source files** retained identical bytes and modification times. Only derived structures/exports were updated; old segment sidecars remain retained.
- Three sources contain multiple turns in a single HTML paragraph: **episodes 2, 151 and 195**.
- Two sources use shortened labels: **106 (`Gopi`, `Ryan`) and 113 (`Gopi`, `Alex`)**. They remain shortened; no guessed full names were inserted.
- Together these produce **five structural-format cases**. Sentence/whitespace fallbacks retain exact source spans where boundaries are unusual.
- The older newsletter validator rejects **episodes 1 and 151**: the short single-host introduction and an unusual single-paragraph transcript. These are diagnostics, not evidence of missing source material.
- **34 transcripts** contain colon prefixes that are not confidently name-like. Many are ordinary prose. They are reported as ambiguous candidates and excluded from speaker attribution, not counted as source validation failures.
- Source spellings such as `Adam draper` remain unchanged. Colon delimiter spacing is excluded from parsed name tokens while original source/text whitespace remains intact.
- Speaker-label presence/parseability is not identity accuracy. **No speaker identity has been verified against audio** in this task; some continuation passages legitimately have no explicit label or timestamp.
- Show-note headings never receive speaker attributions. Show notes remain distinct from transcript matches in both CLI and JSON output.

## Five actual CLI demonstrations

All commands below were executed against the full index. Filters are explicit; the older transcript example also restricts the episode to demonstrate a known passage. JSON results, exact source/context, offsets, hashes and ranking components are retained in [search-demonstration.json](../archive/reports/search-demonstration.json).

| Query | Scope | Demonstrated result | Source type | Timestamp / source label |
|---|---|---|---|---|
| `proof of value` | `--source episode_title` | 195 — Show Proof of Value Before You Build for Scale | Official episode title | Not applicable |
| `Gokul Rajaram` | `--source metadata` | 2 — Lessons from >100 angel investments | Derived list of explicit source speaker labels | Audio-unverified |
| `Commerce Ventures` | `--source show_notes` | 75 — Avoid ‘Me-too’ Startup Ideas | Published show notes; company heading and surrounding description | Not applicable |
| `relentlessly resourceful` | `--source transcript --episode 2` | 2 — a question about testing founder resourcefulness | Transcript | `[00:12:34]`, Gopi Rangan |
| `choosing a partner in life` | `--source transcript --episode 191` | 191 — investment/partner-choice comparison | Transcript | `[00:23:15]`, Justin Smith-Lorenzetti |

Example commands:

```sh
python3 -B archive_search.py search "proof of value" --source episode_title --limit 1
python3 -B archive_search.py search "Gokul Rajaram" --source metadata --limit 1
python3 -B archive_search.py search "Commerce Ventures" --source show_notes --limit 1
python3 -B archive_search.py search "relentlessly resourceful" --source transcript --episode 2 --limit 1
python3 -B archive_search.py search "choosing a partner in life" --source transcript --episode 191 --limit 1
```

The human CLI displays source context and a precise locator rather than only an isolated keyword fragment. `context PASSAGE_ID --json` returns the same indexed passage plus surrounding text. A result's raw label is attributed only to its source passage and remains audio-unverified.

Eight real-content query fixtures passed against the complete corpus. They cover guest/speaker names, title phrases, companies, founder/investor concepts, exact transcript phrases, notes, oldest content and recent content. Assertions concern expected episode/source types, not a claimed universal relevance benchmark.

## Performance and storage

Fresh offline index reconstruction took **4.582 seconds** and reproduced the prior full index **byte-for-byte** under the same SQLite version.

Across 25 measured in-process searches over five representative queries, warm latency was **1.572 ms median** (1.053–2.462 ms). Fresh-process CLI calls had **58.378 ms median** including interpreter startup. These are local observations, not a production latency guarantee.

| Artifact | Bytes at measurement | MiB |
|---|---:|---:|
| Preserved sources | 16,504,082 | 15.74 |
| Derived text | 6,619,671 | 6.31 |
| Structured segments, including retained previous parsing | 20,359,447 | 19.42 |
| Passage JSONL | 32,367,698 | 30.87 |
| All search-document JSONL | 33,149,442 | 31.61 |
| SQLite index | 58,122,240 | 55.43 |
| Markdown library | 13,940,050 | 13.29 |
| CSV | 267,242 | 0.25 |
| Entire local archive | 183,301,709 | 174.81 |

The binary index is excluded from Git and rebuilds from local sources. The passage/search-document JSONL files are large derived text artifacts with some duplication; a deployment can regenerate them rather than carrying every representation through Git history. Preserved sources and normalized metadata are the durable evidence. Old segment versions were retained for traceability, which contributes to the measured size. No audio/media files were downloaded.

Before weekly scheduling, choose durable generated-data persistence, permitted branch/storage writes, artifact retention, failure notifications and a runtime budget for backfills/refresh cohorts. Typical unchanged ingestion is inexpensive; a first full backfill is the measured multi-minute operation. No scheduled workflow was created or enabled.

## Tests and acceptance

**53 automated tests passed; 0 failed.** Tests run offline from retained real API fixtures and controlled modifications. They cover the Phase 1 identity/pagination contracts plus archive-wide reconciliation, exact HTML/text preservation, natural passage IDs/locators, timestamps, source labels, missing notes/transcripts, changed sources, interrupted checkpoint replay, unprocessed refresh checkpoints, deterministic ranking and index reconstruction, source context, stale-index rejection, Markdown/CSV regeneration, exclusion of provisional identities, and prose/notes-heading attribution regressions.

Run:

```sh
python3 -B -m unittest discover -s tests/archive -v
python3 -B archive_sync.py validate
```

No unrelated recommendation or publishing tests were rerun because their implementations were unchanged. Existing editorial sources were left untouched.

## Readiness recommendation

**Phase 3 searchable frontend: ready to proceed after approval.** The complete catalogue and all currently available official notes/transcripts are searchable; exact context/source locators and explicit source types are available. The frontend must retain missing-source states and label uncertainty and sanitize any displayed HTML without altering preserved files.

**Weekly scheduled synchronization: command pipeline ready; operational deployment not yet ready.** Approve/configure persistence, write permissions, notifications and scheduling first, then exercise a scheduled run and failure recovery. The intended frequency remains once per week. Scheduling has not been implemented or claimed as automated.

Source speaker accuracy, exhaustive attribution for unlabeled continuation text, and editorial/guest identity reconciliation remain separate review work. They do not block an honest source-search frontend.

Machine evidence: [coverage](../archive/reports/latest.json), [metrics](../archive/reports/phase2-metrics.json), [index](../archive/reports/search-index.json), [search quality](../archive/reports/search-quality.json). Commands and storage contracts: [archive-search.md](archive-search.md).
