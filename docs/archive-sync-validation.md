# Archive foundation implementation validation

Historical phase report. Current weekly synchronization and freshness behavior are documented in [the operations guide](archive-weekly-sync.md) and [current validation](archive-weekly-sync-validation.md).

Validated 26 October 2026. Scope: complete public catalogue metadata, five official episode details, existing local transcript reuse and exact intelligence links. No full-detail backfill, search, frontend or scheduling.

## Live catalogue

The public Simplecast response returned **195 records**, on two pages of 100 and 95. The normalized catalogue contains **195 unique namespaced remote IDs**, with unique current season/episode-number pairs and numbers 1–195. Count and membership are calculated from the live response, not constants.

- First by source publication time: episode 1, `2020-07-17T18:37:38-07:00`.
- Latest by source publication time: episode 195, `2026-09-22T04:00:00-07:00`.
- Duplicate/conflicting identities: zero.
- Missing checked metadata: artwork for episode 1 only.
- Metadata and short summaries retained: 195 each.
- Official full show notes/transcripts retained: five each.
- Legacy transcripts preserved: 56; overlap with official pilot at episodes 75/191.
- Distinct episodes with locally preserved transcripts: **59/195 (30.3%)**.
- Timestamped preserved transcripts: **36/195 (18.5%)**.
- Syntactically detected speaker labels: 50 episodes; this is not an accuracy metric.
- Exact URL-plus-number intelligence links: **57/195 (29.2%)**.
- Pilot Markdown documents: five, with all notes/transcript sources accepted.
- Retrieval failures / validation failures: **0 / 0**.

The current [machine report](../archive/reports/latest.json) and [human report](../archive/reports/latest.md) are generated from accepted content.

## Pilot evidence

| Episode | Source condition | Full notes | Transcript | Timing markers | Raw speaker labels | Export/source validation |
|---:|---|---|---|---|---|---|
| 1 | Short introduction, one host | Preserved | Preserved | Present | Gopi Rangan; partial | Passed |
| 2 | Old episode with missing main local transcript | Preserved | Preserved | Present | Gopi Rangan, Gokul Rajaram; partial | Passed |
| 75 | Existing untimed transcript | Preserved | Preserved | Absent | Gopi Rangan, Dan Rosen; partial | Passed |
| 191 | Active/local overlap; varied HTML formatting | Preserved | Preserved | Present | Justin Smith-Lorenzetti, Gopi Rangan; partial | Passed |
| 195 | Recent, line-separated turns inside a single paragraph | Preserved | Preserved | Present | Rohini Chakravarthy, Gopi Rangan; partial | Passed |

All raw-label accuracy states remain `unverified`. Transcript language, punctuation and supplied names were not repaired. The source HTML is exact; the plain-text projection is a documented structural conversion.

## Automated checks

Run:

```sh
python3 -B -m unittest discover -s tests/archive -v
python3 -B archive_sync.py validate
python3 -B archive_sync.py export
```

**31 offline automated tests passed; zero failed.** The suite uses synthetic in-memory API fixtures and temporary directories, not the live service. It covers:

- Canonical UUID and editorial-number uniqueness; metadata-only catalogue members.
- Complete pagination, changing totals, truncation, unsafe next-page hosts and duplicate IDs.
- Malformed optional/required metadata types and inconsistent detail/podcast identities.
- Exact notes/transcript source preservation and SHA-256 checks.
- Unicode, quotes, commas, embedded newlines and deterministic CSV output.
- Markdown regeneration, safe literal fences and exported source content.
- Unicode passage spans, timestamp preservation, line-separated speaker parsing, short/untimed/single-speaker transcripts.
- Missing optional content, shell rejection and per-episode retrieval/validation failures.
- Source version preservation, exact legacy/intelligence matching and conflicting crosswalks.
- Idempotent reconciliation, removal/reappearance handling, directory publication and fatal-failure rollback.
- Tampered source/export detection.

The offline archive validator additionally traverses every accepted catalogue record and source reference, checks source/derived hashes, recreates normalized metadata, verifies exact HTML fields against preserved detail snapshots, recomputes text/segments, and regenerates CSV/Markdown for byte comparison. All **195 records** passed.

## Live idempotency

Three live runs were made during development, always fetching the complete list and only the same five episode details:

1. Initial run: 195 new records, 0 failures.
2. After the pilot exposed multiple speaker turns in one HTML paragraph, the derived segment parser was improved. The next run reported 3 derived-source-state changes and 192 unchanged records; no new episode or remote-content claim was made.
3. Final unchanged-source repeat at `2026-10-26T09:21:02.489738+00:00`: **0 new, 0 changed, 195 unchanged**, 0 failures.

Before the final repeat, a snapshot of file hashes and modification times was recorded outside the repository under `/tmp`. Comparing it afterward found **485/485 non-report files unchanged in both bytes and modification times**. Only the two latest-run reports changed, as expected for check time and per-run statistics. No duplicate episodes or new source versions were created by the repeat.

## Scope preservation and remaining work

The repository's previously tracked editorial sources/scripts were not modified. The pre-existing untracked episode 192 and newsletter production files remain untouched. The new implementation consists of `archive_sync.py`, `tests/archive/test_archive_sync.py`, this documentation and the additive `archive/` outputs. No dependencies were installed.

The implementation is ready for the separately approved next phase of incremental full-archive detail ingestion and lexical-search preparation. Work still required there includes an ingestion queue/budget and refresh cohort beyond the hard-bounded pilot, broader parser evaluation against every source shape, and lexical-index construction. Speaker accuracy requires separate human/audio review if promised as a client deliverable. Deployment persistence, permissions, monitoring and weekly scheduling still need configuration and approval; none is enabled here.
