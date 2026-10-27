# Full-archive source ingestion and lexical search

Phase 2 extends the [Phase 1 source library](archive-sync.md). Official published membership still comes exclusively from the complete Simplecast catalogue. Local/provisional episode material does not add catalogue members.

## Commands

Run from the repository root with Python 3.9+ and SQLite compiled with FTS5 (the standard Python runtime used here provides it). No new package installation, API credential, browser runtime or model is required.

```sh
python3 -B archive_sync.py sync
python3 -B archive_library.py ingest
python3 -B archive_library.py export
python3 -B archive_library.py reparse  # only after upgrading parsing rules
python3 -B archive_search.py rebuild
python3 -B archive_library.py report
python3 -B archive_search.py search "proof of value" --source episode_title
python3 -B archive_search.py search "choosing a partner in life" --source transcript --episode 191 --phrase
python3 -B archive_search.py search "Commerce Ventures" --source show_notes --json
python3 -B archive_search.py context PASSAGE_ID --json
python3 -B archive_sync.py validate
python3 -B -m unittest discover -s tests/archive -v
```

`--output /path/to/archive` applies to every command. A clean clone first synchronizes the catalogue, ingests official details, and builds the index. Historical local attachment coverage additionally requires those repository inputs; official metadata/source retrieval does not depend on them.

The binary SQLite file is excluded from Git by `archive/.gitignore`; rebuild it locally from the preserved source corpus. The source and text/JSONL deliverables remain present independently of that binary.

Use `ingest --limit 20` to commit a bounded batch; another invocation resumes eligible work. `--delay 0.5` is the default minimum spacing between sequential HTTP attempts. The command makes no parallel requests. Missing/failed sources do not exclude catalogue members or Markdown files.

`ingest --refresh-limit 20 --min-age-days 7` also rechecks a bounded oldest-checked cohort. Changed list metadata always makes an episode eligible; this cohort catches source edits that might not change list timestamps. `--limit` bounds total work if needed. The standalone ingestion command leaves successful empty source fields unavailable-at-source until selected for refresh. The production orchestrator explicitly retries missing sources on each check. Failed standalone attempts use a five-minute retry cooldown.

An unchanged immediate `ingest` invocation makes no HTTP requests. `sync` still checks the full public metadata list. The complete staged production command and locally implemented schedule are documented in [weekly synchronization](archive-weekly-sync.md); activation is pending review.

## Incremental state and recovery

`ingestion_state.json` records accepted/failed attempts and the metadata revision checked. A preserved, hash-valid detail whose normalized metadata matches the current catalogue is reused. Changes to official list metadata queue a fresh detail request. Refreshes preserve prior source versions under the Phase 1 content-addressing strategy.

The sibling `.<archive-name>-ingest-checkpoints/` directory holds allowlisted response checkpoints before derived parsing/export. Every checkpoint contains the expected catalogue metadata hash, payload hash, source acquisition time and approved original fields. If a process exits before publication, the next invocation replays matching valid checkpoints instead of downloading those responses again. Invalid response checkpoints are quarantined as `.failed.json` so a later retry can fetch corrected remote content. Checkpoints are removed only after accepted content is published; they are operational recovery state, not portable catalogue sources.

A writer lock and staged archive copy preserve a coherent accepted library. Normal Ctrl-C finalizes accepted work when possible; an abrupt process exit leaves the prior accepted snapshot plus durable checkpoints. If a killed process leaves a lock, confirm no process owns it before removing the stale lock. Export/validation failure prevents publication. The directory publication contract remains the documented Phase 1 two-rename swap, with a brief reader retry window.

The ingester reports actual HTTP attempts (including bounded retry attempts), accepted responses, replayed checkpoints, failures and elapsed time. It does not retrieve audio or perform speech recognition. The public API offered no verified conditional caching contract during investigation, so metadata/source hashes and bounded refreshes are used rather than unproven ETag assumptions.

## Evidence and derived text

Original `long_description` and `transcription` HTML remain under `sources/`; normalized plain text is separate under `derived/text/`. The Phase 1 transformation remains unchanged: decode HTML entities, append source text nodes unchanged, and insert LF at structural breaks. No spoken wording, quotations or names are repaired. JSON allowlisting excludes incidental operational tokens/actions.

Every catalogue episode now gets a reproducible UTF-8 Markdown export, even when deeper source content is absent, pending or failed. CSV availability is regenerated from the manifest. Editorial themes/industries/lessons remain separate and are not indexed in this phase. Source labels remain audio-unverified.

## Natural passages and locators

Phase 2 passages derive from the hashed text projection, retaining exact source slices:

1. Split at paragraph boundaries and explicit speaker labels at line starts.
2. Recognize timestamp-prefixed speaker labels inside an otherwise unbroken paragraph.
3. Keep continuations within the natural block until the next boundary. Do not infer speaker identity for unlabeled blocks or carry names into them silently.
4. For blocks longer than 1,800 characters, use a sentence-ending boundary within that range. If none exists, use whitespace; a final hard character boundary handles a pathological unbroken token. These are deterministic display/retrieval fallbacks, not embedding chunks.

Each passage includes canonical episode ID, number/title, source type, source ID/path/hash/field, text projection path/hash, passage ID, start/end offsets, exact text, and optional source timestamp/speaker label. Offsets use Unicode code points and exclusive ends. IDs hash the method version, episode identity, source type and complete locator; source changes create new IDs while unchanged sources reproduce the same IDs.

`derived/passages.jsonl` contains transcript/show-note passages. `derived/search-documents.jsonl` additionally contains catalogue metadata fields. `context` resolves an indexed passage and exposes its full exact text plus up to 300 characters on either side. An excerpt never becomes a transcript quote merely because it matched: `source_type` remains explicit.

Conservative name-like label recognition rejects ordinary prose colon prefixes, tolerates indentation, and preserves source spellings such as `Adam draper` without correcting them. Colon delimiter spacing is not part of a parsed name; original whitespace remains in the text. Show-note headings never produce speaker attributions.

The parser upgrade is explicit: `segments-v2` stores new segment sidecars in a versioned subdirectory, and `lexical-v2` identifies current passage/index rules. `reparse` regenerates derived structures and exports from saved official fields without HTTP requests. Previous segment files and all source HTML remain intact.

Format diagnostics count timestamp markers, syntactic labels, shortened labels, source paragraph structure, and multiple turns within one HTML paragraph. Ambiguous colon prefixes are reported separately: many are ordinary sentences, not malformed speaker names. The parseable-transcript count means at least one explicit name-like label was recognized; it does not claim complete attribution of every word. They separately report the old newsletter validator's result, which can reject short or unusual-but-useful transcripts. Neither source-label detection nor parseability establishes identity accuracy against audio.

## Search index and ranking

The offline index is SQLite FTS5 at `search/archive.sqlite3`. Metadata includes official title, episode number, publication timestamp, summary and evidenced raw transcript speaker labels. Every published catalogue member with its metadata is indexed independently of source depth. Show notes and transcripts are independent passage types. No embeddings, semantic search, RAG or generated answers are involved.

Queries are literal Unicode word tokens. By default every token must occur within the same indexed field/passage; `--phrase` requires consecutive tokens. Punctuation/FTS operators supplied by the user are treated as token text, not query instructions. SQLite `unicode61` tokenization folds case and diacritics; there is no stemming or semantic synonym expansion.

Ranking is transparent:

- Field boost: title/episode number 20, speaker label 15, summary/date 8, show notes 5, transcript 2.
- Exact case-insensitive phrase substring bonus: 8.
- FTS5 BM25 relevance: added as negative BM25 (larger score is better).
- Equal scores use episode number then passage ID for deterministic ordering.

The CLI/JSON exposes every score component. `--source metadata`, `episode_title`, `episode_number`, `published_at`, `short_description`, `speaker_labels`, `show_notes` or `transcript` controls result type. `--episode` restricts to a human episode number. Results are passage-level and may include several passages from one episode; they are not artificially deduplicated or presented as distinct episode counts.

The index stores an input fingerprint of catalogue + manifest + method version. Queries reject a stale index after source/catalogue changes. Rebuild is entirely offline. Identical inputs preserve index bytes; rebuilding a removed database from the same corpus is deterministic under the same SQLite version. Cross-version binary identity is not promised. Coverage reports mark an older index stale until rebuilding.

## Validation and test fixtures

Real retained official pilot sources support the core retrieval fixtures. Additional captured episodes 106/113 exercise shortened `Gopi`/`Ryan`/`Alex` labels without replacing them with inferred full names. Query fixtures at `tests/archive/fixtures/search_queries.json` cover guests, titles, companies, concepts, transcript phrases, notes, older and recent material. They assert expected source types/episode presence rather than brittle exact ranks.

Controlled fixture modifications exercise missing sources and source changes; these do not alter production source data. Tests also cover interruption/checkpoint replay, idempotent ingestion, deterministic passage IDs/index rebuilds, provenance/context, safe query parsing and stale-index rejection. Run the suite offline using the command above.

Operational coverage and corpus format diagnostics are generated in `reports/latest.json` and `reports/latest.md`. Search-specific counts and fingerprints are in `reports/search-index.json`; ingestion timing/requests are in `reports/ingestion-latest.json`. See [the Phase 2 validation and demonstration](archive-phase2-validation.md) for measured counts, searches, runtime and storage.

## Weekly execution and frontend readiness

The weekly job now implements catalogue sync → bounded eligible ingestion/refresh → export/index/ZIP validation → coverage report → validated persistence, through `archive_operations.py sync`. See [weekly synchronization](archive-weekly-sync.md) for the selected content/status persistence policy, permissions, failure recovery and activation requirements. No remote weekly automation has been enabled yet.

The index and source locators are intended for a future searchable frontend. Its HTML display must sanitize source HTML without changing preserved files. Source-type labeling, missing-source states and audio-unverified labels must remain visible. This phase adds no frontend or publishing changes.
