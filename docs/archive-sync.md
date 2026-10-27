# Canonical archive synchronization and source library

For the complete production check, use `python3 -B archive_operations.py sync`. See [weekly operations](archive-weekly-sync.md) for staging, source ingestion, exports, search, successful-sync metadata, GitHub scheduling and persistence. The workflow is implemented locally and awaits review/activation.

The following lower-level Phase 2 commands extend the original pilot to incremental full-archive ingestion and local lexical retrieval. See [archive search and ingestion](archive-search.md) for their individual behavior:

```sh
python3 -B archive_sync.py sync
python3 -B archive_library.py ingest
python3 -B archive_library.py export
python3 -B archive_search.py rebuild
python3 -B archive_library.py report
python3 -B archive_search.py search "proof of value" --source episode_title
```

The following sections preserve the Phase 1 baseline and its bounded `sync --pilot` behavior; that historical five-episode limit does not apply to `archive_library.py ingest` or the production orchestration command. Statements below about later phases reflect the Phase 1 implementation date.

## Phase 1 baseline


Implemented 26 October 2026 under the limited approval following [the archive audit](archive-interface-audit.md) and [the sync design](full-archive-sync-design.md). This implementation creates an additive archive library. No frontend, search index, bulk detail ingestion or scheduled workflow is included.

## Run manually

From the repository root, with Python 3.9 or later:

```sh
python3 -B archive_sync.py sync
python3 -B archive_sync.py sync --pilot
python3 -B archive_sync.py validate
python3 -B archive_sync.py export
python3 -B -m unittest discover -s tests/archive -v
```

- `sync` fetches the complete official public catalogue and reconciles existing repository sources. It makes no episode-detail requests. Previously accepted pilot content remains attached.
- `sync --pilot` additionally fetches details **only for episodes 1, 2, 75, 191 and 195**. That fixed bounded pilot is intentional for this implementation; no whole-archive detail option is provided.
- `validate` is offline. It verifies identities, manifest consistency, source hashes, metadata mappings, source HTML equality, derived text/segment fidelity and reproducible CSV/Markdown.
- `export` regenerates CSV and existing pilot Markdown from preserved local sources, then validates them. It does not fetch anything or regenerate editorial content.
- `--output /absolute/path/to/archive` selects another dedicated additive directory. Original repository source directories are rejected as sync destinations. A nonempty existing destination must already contain an archive manifest.

The commands use only Python's standard library and the existing `episode_discovery.request_json` helper. There are no new dependencies or credentials. Public API network access is required for sync. The fetcher uses the existing site lookup, public published-list endpoint and next-page links, with additional validation and retries. No management/action links are invoked.

## Storage and portable deliverables

All generated/preserved library material lives under `archive/`:

| Path | Purpose |
|---|---|
| `catalogue.jsonl` | One normalized record per discovered remote identity; stable ordering by canonical ID |
| `manifest.json` | Accepted source versions, provenance, optional-content states and editorial links |
| `links.json` | Exact URL-plus-number intelligence matches and unresolved conflicts; no name guessing |
| `sources/<remote-id>/metadata/<hash>.json` | Allowlisted official list metadata, without operational tokens/action links |
| `sources/<remote-id>/summary/<hash>.txt` | Exact short `description` as UTF-8 |
| `sources/<remote-id>/detail/<hash>.json` | Allowlisted pilot detail fields, including unmodified notes/transcription strings |
| `sources/<remote-id>/show_notes/<hash>.html` | Exact decoded `long_description` string encoded as UTF-8 |
| `sources/<remote-id>/transcript/<hash>.html` | Exact decoded `transcription` string encoded as UTF-8 |
| `sources/<remote-id>/transcript_legacy/<hash>.txt` | Byte-preserved existing transcript copy, with original repository path/hash |
| `derived/text/<remote-id>/<source-hash>.txt` | Versioned structural HTML-to-text projection |
| `derived/segments/<remote-id>/<source-hash>.json` | Exact text spans, raw labels and optional timing markers |
| `exports/catalogue.csv` | Generated UTF-8 catalogue and availability columns |
| `exports/episodes/<remote-id>.md` | Five generated pilot episode documents |
| `reports/latest.json` | Machine-readable coverage and run outcome |
| `reports/latest.md` | Human-readable coverage and pilot table |

Identity is `simplecast:<UUID>`. Number is a nullable human-facing field; missing number or slug does not exclude an otherwise valid public member. Numbers are checked for uniqueness within a season; duplicate UUIDs are rejected. This is appropriate for the current TSSE numbering; a future legitimate numbering change should be reviewed rather than silently deduplicated.

The normalized catalogue is derived from official metadata. Markdown and CSV are reproducible exports, not editable master data. Original rankings, enrichment records, transcripts, newsletters, discovery reports, publishing inputs and outputs remain unchanged.

The archive directory can be copied as a self-contained source/export bundle. Intelligence references point back to original repository paths and hashes; the intelligence files themselves are deliberately not copied into the official source layer. Those attachments require the original repository to inspect their contents.

## Availability semantics

Each episode has metadata, summary, show-notes, transcript, structured-transcript, intelligence, newsletter and social entries. Transcript state also describes timestamp presence and speaker parsing. Metadata-only episodes have `not_checked` deeper sources; they do not claim that transcripts are unavailable remotely.

States include:

- `available`: source content was actually retained or an exact local intelligence reference was evidenced.
- `not_checked`: no remote detail retrieval or reviewed relationship inspection has occurred.
- `unavailable_at_source`: a successful pilot detail response contained a null/empty content field.
- `failed`: a pilot retrieval/validation failed without a previously accepted source to retain.
- `not_found_locally`: no exact local intelligence match was found.

An accepted prior source survives a later request failure; the run report records the failed attempt. A successful empty source preserves the former source version historically but marks the current remote source unavailable. Previous changed content versions retain hashes, paths and acquisition dates under `previous_versions`.

Official and legacy transcript entries remain distinct. CSV's `transcript_available` and coverage's `locally_preserved_transcripts` use their distinct episode union, preferring official pilot content for current timing/label statistics. `official_transcripts` counts only fresh retained API sources; `legacy_transcripts` counts existing repository copies, including overlap. Legacy acquisition dates are explicitly unknown even though the archive records when it copied the file.

Existing intelligence attaches only when both the number and full episode URL match. Conflicts are recorded as unresolved. Newsletter/social relationships remain `not_checked`; this task does not repair historical mappings or infer published assets from generated output directories.

## Provenance and source fidelity

Each accepted source records the canonical/remote ID, kind/layer, endpoint or source URL, source field where applicable, relative path, SHA-256, acquisition timestamp, retrieval result and validation method/version. A same-hash rerun retains its acquisition timestamp. Dynamic API counters and action links are excluded from normalized source content, so they cannot cause meaningless catalogue revisions.

The preserved notes/transcript `.html` files equal the API's decoded JSON field strings byte-for-byte after UTF-8 encoding. The implementation intentionally retains an allowlisted detail snapshot rather than distributing the complete HTTP response with incidental operational fields. It does not claim identical HTTP JSON whitespace/key ordering.

Text projection uses `HTMLParser` with entity decoding. It appends text nodes unchanged, inserts LF for `<br>`, and two LF characters at selected block endings. It does not trim text, collapse internal whitespace, change words or fix grammar. The exact HTML remains available separately. Active script/style/iframe content and application shells are rejected as unexpected transcript markup.

Markdown includes separate metadata, short summary, exact notes HTML, exact transcript HTML, derived transcript text and provenance sections. Variable-length literal fences prevent source backticks from terminating a block. Format conversion is explicitly labeled; the derived text is not called byte-identical HTML.

Speaker detection is conservative and syntactic. The parser reads line-start labels, including optional `[HH:MM:SS]` prefixes. It never assigns identities from the API contributor list, carries a speaker across unlabeled lines, or silently repairs names. `parseability=syntactic` means every nonempty projected line begins with a recognized label; `partial` means only some do. Neither proves audio accuracy. Raw speaker labels are exported as evidence, while guest-name arrays remain empty until reviewed attribution is available.

Segments use zero-based Unicode code-point offsets, exclusive ends, into a text projection identified by hash. Each stores the exact excerpt, optional raw speaker label, and timing-marker positions/seconds. No end times or audio alignment are invented. Future JavaScript consumers must convert UTF-16 indices before comparing these offsets. Changing extraction rules requires a versioned migration; do not overwrite a released projection contract silently.

## Completeness, failure and idempotency

The catalogue is accepted only after all pagination completes with consistent totals/current-page markers. Repeated pages, duplicate identities, foreign hosts/podcast paths, malformed fields, unexpected publication states and missing final pages fail the run. HTTPS is required. Missing optional metadata is reported rather than fabricated. A list/detail revision mismatch rejects that pilot detail rather than combining inconsistent source metadata.

A writer lock prevents simultaneous syncs. All work is staged in a sibling directory, then validated before promotion. The directory swap uses two renames with rollback on a failed promotion; readers should retry during the brief rename gap. It prevents mixed generations but is not an uninterrupted database transaction. Fatal failures preserve the prior accepted archive and write a sibling `.<output-name>-last-failure.json` diagnostic. Do not treat that diagnostic as current accepted coverage.

Formerly public identities are retained as `not_seen_in_complete_snapshot` if absent from a complete later response. They are excluded from the current published denominator but remain in the catalogue. Absence does not mean deleted/private. Loss of more than two episodes or 10% of the prior active set, whichever is larger, is quarantined for review.

One pilot detail can fail while other catalogue additions remain accepted. Such a run exits with code 2 and reports affected IDs; fatal exceptions exit nonzero. Export validation failure prevents sync promotion. Retry handling is bounded for transient network/HTTP failures. A server-requested rate-limit pause over 30 seconds defers to a later run rather than retrying too early.

Content-addressed source paths and stable acquisition times prevent source churn. Identical runs preserve catalogue, manifest, crosswalk, CSV, Markdown and source/derived bytes. Only `reports/latest.*` changes for check time and per-run counts. Later production persistence should avoid committing timestamp-only reports.

## Pilot selection and verified results

The live source returned 195 episodes on two pages (100 + 95). All were represented. First publication: episode 1, `2020-07-17T18:37:38-07:00`; latest: episode 195, `2026-09-22T04:00:00-07:00`. No duplicate IDs or conflicting season/number identities were found. Episode 1 lacks artwork; all other catalogue fields checked by the coverage report are populated.

| Episode/title | Why selected | Notes/transcript | Timestamps | Speaker parsing | Markdown/fidelity |
|---|---|---|---|---|---|
| 1 — Welcome and quick intro | Short, older, single-host recording; invalidates a universal 10 KB/two-speaker requirement | Both preserved | Present | Gopi Rangan; partial | Exported; passed |
| 2 — Lessons from >100 angel investments | Older episode with a missing main local transcript | Both preserved | Present | Gopi Rangan/Gokul Rajaram; partial | Exported; passed |
| 75 — Avoid ‘Me-too’ Startup Ideas | Existing corpus overlap; untimed dialogue | Both preserved | Absent | Gopi Rangan/Dan Rosen; partial | Exported; passed |
| 191 — Have desire to build with unwavering commitment | Active/local corpus overlap; mixed markup and timestamped dialogue | Both preserved | Present | Justin Smith-Lorenzetti/Gopi Rangan; partial | Exported; passed |
| 195 — Show Proof of Value Before You Build for Scale | Latest listed episode; multiple turns within one HTML paragraph | Both preserved | Present | Rohini Chakravarthy/Gopi Rangan; partial | Exported; passed |

Speaker accuracy is unverified for all five; the table describes source-label parsing only. The corpus has 195 metadata/summary records, five official notes, five official transcripts, 56 legacy transcript copies and **59 distinct episodes with preserved transcript content**. The official and legacy sets overlap at 75 and 191. There are 36 timestamped preserved transcripts and 57 exact intelligence matches. Current machine/human reports are the operational source for these counts.

The initial live run discovered 195 new records. During implementation, a second live run regenerated three pilot parsing states after line-boundary handling was improved; these were derived-parser changes, not newly published or remotely edited episodes. The final live rerun and byte/mtime comparison are recorded in [implementation validation](archive-sync-validation.md).

## Before enabling weekly execution

This CLI is suitable for a later GitHub Actions job using standard Python and public network access. No browser, secret, local Codex runtime or machine-specific dependency path is needed. A normal sync does not fetch new episode details automatically in this bounded implementation: Phase 2 must add the separately approved ingestion queue and refresh policy.

Still to approve/configure: durable generated-data branch/storage, exact write permissions, default-branch workflow/manual dispatch, failure notifications, artifact retention and a once-weekly schedule. Persist accepted content revisions, not merely transient runner artifacts. Existing local legacy inputs must be present in the checkout; approved/untracked inputs need an explicit persistence decision before another machine can reproduce the same attachment coverage.

No scheduler has been created. The next approved phase can extend detail ingestion incrementally and prepare lexical indexing on these source spans; frontend, semantic search, automated enrichment and publishing remain separate work.
