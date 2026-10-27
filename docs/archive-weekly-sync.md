# Weekly archive synchronization

Implemented and locally validated 27 October 2026. This is the current operational guide; the Phase 1–3 reports retain their historical results. See [validation evidence](archive-weekly-sync-validation.md).

The implementation is ready for review. It is **not yet an active GitHub schedule**: the workflow, archive implementation and baseline archive have not been merged into the default branch. The deployment preparation is on a review branch; no scheduled production workflow, branch-protection change or live deployment has been activated. Activation requires publishing the reviewed baseline and workflow to the default branch, then completing a successful manual Actions run. The later Vercel adaptation is documented in `docs/archive-vercel-deployment.md`; no live deployment has yet been verified.

## Schedule

The publication assumption is every other Tuesday around 4:00 AM Pacific. Check every Tuesday around 6:30 AM Pacific, giving approximately 2½ hours for source publication without encoding biweekly arithmetic.

`.github/workflows/archive-sync.yml` uses:

```yaml
on:
  schedule:
    - cron: '30 6 * * 2'
      timezone: America/Los_Angeles
  workflow_dispatch:
```

GitHub now supports an IANA timezone on scheduled events. This runs at 13:30 UTC during PDT and 14:30 UTC during PST, while preserving Tuesday 6:30 AM local time. No dual-cron guard is needed. The schedule uses the default branch; manual runs on other branches are skipped. Runs share a concurrency group, do not cancel an active run, and have a 30-minute timeout. [GitHub schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Scheduling is approximate: GitHub may delay or drop queued scheduled jobs. In a public repository, 60 days without repository activity can disable scheduling. Weekly no-change runs deliberately create no commits, so check the Actions page if publication or repository activity pauses for that long. These service limits are why the UI reports an actual successful check instead of promising continuous freshness.

## One production command

From the repository root:

```sh
python3 -B archive_operations.py sync
```

Requires Python 3.9+ with SQLite FTS5 and public Simplecast network access; CI uses Python 3.12. The production pipeline uses Python's standard library and the existing request helper. The workflow additionally uses the hosted runner's Git, GitHub CLI and Node for a small presentation regression test; the frontend itself needs no Node build.

The sequence is:

1. Lock the accepted archive and copy it into a disposable candidate.
2. Discover the official Simplecast podcast and all published catalogue pages through `archive_sync.sync`.
3. Compare stable remote identities, metadata and accepted manifests.
4. Run `archive_library.ingest` for new/changed records, pending sources and a bounded historical refresh cohort. Preserve official metadata, source HTML, published notes, transcripts and source versions.
5. Materialize Markdown and CSV through the existing exporter; preserve source text and timestamp markers in derived text/segments.
6. Validate the archive and portable exports, rebuild the lexical corpus/index when missing or changed, and verify SQLite integrity and published-episode coverage.
7. Reuse or regenerate the reproducible Markdown ZIP, checking every member against its export hash; exercise the actual frontend adapter for coverage and episode-file access.
8. Update content coverage only when content changes. Record the actual successful completion time and per-run summary.
9. Promote the complete candidate with rollback on an ordinary publication error.
10. In Actions, run regression tests, stage only the content allowlist, conditionally commit/push, then upload successful operational state. A local `sync` does not commit or push.

All scheduled and manual checks use this same implementation. The older Phase 1 `archive_sync.py sync` command alone is **not** a complete production check and does not advance successful-sync metadata.

## Incremental policy

Catalogue discovery runs every check. New records and metadata revisions are eligible immediately. Explicitly missing official sources are retried on the next production check. In addition, at most 20 oldest-checked records at least seven days old are refreshed to catch source-only corrections that do not update catalogue metadata. For a stable archive of 195 records, a silent correction can take about ten weekly checks to encounter; the bound grows with archive size. A successful unchanged refresh updates only operational check state.

To check every historical source immediately:

```sh
python3 -B archive_operations.py sync --refresh-limit 100000 --min-age-days 0
```

Requests are paced by the existing polite client. A clean runner rebuilds missing ignored derived files from accepted sources; a warm checkout reuses a matching index and ZIP. No-change source checks do not rewrite CSV, Markdown, accepted source timestamps or coverage reports.

## Persistence and footprint

Content is persisted on the default branch, using the commit message `archive: sync published TSSE episodes`. `persist` refuses unrelated staged work or the wrong branch and uses an ordinary fast-forward push. It never force-pushes, rebases or silently resolves a conflict.

The explicit archive content allowlist is:

| Committed path under `archive/` | Purpose |
| --- | --- |
| `catalogue.jsonl`, `manifest.json`, `links.json` | Canonical identities, accepted revisions, provenance and links |
| `sources/` | Accepted original payloads and historical source versions |
| `derived/text/`, `derived/segments/` | Source-preserving projections and locators referenced by manifests |
| `exports/catalogue.csv`, `exports/episodes/` | Portable catalogue and one Markdown file per published episode |
| `reports/latest.json`, `reports/latest.md` | Coverage of the accepted content generation |

Code, tests, workflow, documentation, frontend assets and `archive/.gitignore` belong in the reviewed baseline commit, not in automated data commits. Existing local editorial inputs remain separate; review their persistence independently before activation. In particular, currently untracked Episode 192 inputs are not silently swept into a scheduled commit. A checkout missing a local editorial JSON input reports that local intelligence as unavailable on the next reconciliation; preserved official sources remain usable. Legacy transcripts already copied into `archive/sources/` remain preserved.

Measured selected archive content: **2,012 files, 59,600,442 bytes (56.84 MiB)**. The whole working archive is 187,307,517 bytes (178.63 MiB), including rebuildable corpus/index/ZIP. There are currently **zero tracked archive files**; these numbers describe the proposed baseline. Selected content averages approximately 0.292 MiB per current episode, or roughly 7.6 MiB for 26 additional similarly sized episodes, before historical corrections and Git compression. Actual growth depends on transcript size and retained revisions.

Ignored/rebuilt locally: `search/*.sqlite3`, consolidated `derived/passages.jsonl` and `derived/search-documents.jsonl`, generated ZIP, and index/ZIP validation reports. No audio, request checkpoints, temporary candidate directories, test fixtures or failure logs enter automatic content commits.

**No-change successful checks create no Git commit.** Per the selected operating model, Actions persists `sync-status.json`, `ingestion_state.json` and `reports/sync-run.json` in the small `archive-sync-state` artifact, with 90-day retention. This preserves both freshness and the rotating refresh cohort without timestamp-only commits. Artifact upload happens only after validation, regression tests and Git persistence succeed.

## Successful-sync metadata and frontend

`archive/sync-status.json` contains a schema version, `status: success`, UTC `last_successful_sync_at`, published episode count, new/changed/unchanged counts, a changes-detected flag and a catalogue/manifest fingerprint. The timestamp is created after a real completed source check and validation. It is never inferred from Git, file modification, builds or server startup.

`GET /api/sync-status` and the `sync` field of `GET /api/files` expose a successful record only when its fingerprint matches the served archive. Failed attempts leave the accepted file untouched. No-change success advances it. Artifact restoration considers only successful runs on the configured branch, checks the fingerprint and timestamp, and never replaces a matching newer local success with an older artifact.

The homepage and Archive Files show `Last successful sync … PT` in the existing muted style. `Intl.DateTimeFormat` explicitly uses `America/Los_Angeles`; `PT` avoids a seasonally incorrect hard-coded PST suffix. The display makes no “Up to date” claim. More than nine days after the last success, it adds a restrained `Weekly check overdue` notice (weekly cadence plus two days' grace). Individual episode views do not repeat the status. Missing or mismatched metadata says `Last successful sync not yet recorded.` Technical failure details remain in operational logs.

All catalogue, coverage, CSV, Markdown, browsing, search, Episode File and ZIP counts come from the accepted archive. A partial new episode is browsable and has a Markdown file immediately; its available metadata/notes are searchable, and transcript text becomes searchable after successful retrieval.

## Preparing a frontend checkout

A browser reading the same local archive sees a completed sync on reload without a frontend build. A GitHub runner does not update a separate laptop or web host automatically. The Vercel adaptation now adds a directly called, validated deployment workflow after changed content is persisted. It also publishes a small fingerprint-scoped success artifact for runtime freshness; see `docs/archive-vercel-deployment.md`. Account configuration and first activation are still pending.

After the reviewed implementation is on GitHub, in a clean checkout on the default branch:

```sh
git pull --ff-only
python3 -B archive_web.py --github-status JoePodcasts/tsse-editorial-os
```

The explicit `--github-status` option validates/prepares missing index and ZIP files, restores matching successful operational state using authenticated `gh`, then starts the read-only web server. It does not fabricate a new timestamp, fetch official source content, pull Git, or poll continuously. Restart with the same option to restore a later no-change successful check even when Git has no new commit. A future host must run this preparation after pulling content or restoring status; deploying only on new commits will miss no-change freshness updates.

To restore operational state without starting the server:

```sh
python3 -B archive_operations.py restore-status --github-repository JoePodcasts/tsse-editorial-os
```

Restoration checks up to the latest 30 successful workflow runs. Missing/expired artifacts retain an existing local success; a new checkout with no matching evidence displays unknown freshness. A failed GitHub API request fails visibly in the operator terminal. Artifact retention is not indefinite archival storage; the canonical content stays in Git. The frontend remains a localhost research application until a hosting/access policy and production server are chosen.

## GitHub permissions and activation

Repository inspection found `JoePodcasts/tsse-editorial-os` public, default branch `main`, Actions enabled, default token permissions read-only, and `main` not protected. No repository settings were changed. The workflow overrides only its synchronization job to `contents: write` for content commits and `actions: read` for prior run/artifact lookup. Other permissions remain unset. It uses GitHub's short-lived token; no PAT or third-party service secret is required. Artifact upload uses the runner's artifact service.

Checkout, setup-python and upload-artifact are GitHub-owned actions pinned to verified full commit SHAs, with release labels in comments. Repository/organization policy must permit those actions and the requested token scope. Branch protection/rulesets requiring PRs or signed commits can reject direct bot pushes; the workflow then fails and keeps the previous published archive. Resolve that operating policy explicitly rather than bypassing protection or broadening token access automatically.

Commits made with `GITHUB_TOKEN` do not trigger ordinary downstream `push` workflows. If hosting is added, integrate preparation/deployment explicitly; do not assume an archive bot commit starts it. [GitHub token-trigger behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

To activate after review: commit the reviewed implementation and selected baseline to `main`, confirm the workflow is enabled in Actions, run it manually once, and verify the success summary, content persistence and downloadable `archive-sync-state` artifact. Then verify a prepared frontend checkout restores that artifact. This final hosted-run exercise remains outstanding.

## Failure behavior and recovery

| Situation | Result |
| --- | --- |
| Explicit null/empty official transcript or notes field | Valid partial availability, clearly marked in manifest/Markdown/summary; retry next check |
| Catalogue/detail transport failure, malformed response, missing required field or wrong source type | Abort candidate; accepted archive and last-success timestamp stay unchanged |
| Export, fidelity, index, ZIP or frontend validation failure | Abort candidate; no publication or Git commit |
| Ordinary directory promotion error | Restore prior directory and fail |
| Regression test, commit or push failure in Actions | Fail job; no successful-state artifact; prior remote content remains unless a push already succeeded |
| Artifact upload fails after a successful content push | Validated content may already be in Git; job fails, no new confirmed status. Rerun to complete persistence; do not roll back valid content blindly |

An explicit null field is distinct from a missing field or failed request. Source corrections retain prior accepted payload versions. Unexpected catalogue disappearance is quarantined by existing checks/coverage validation and requires operator review, rather than silently deleting sources.

The writer lock prevents concurrent local updates. Promotion retains the existing two-rename contract: a reader can briefly need a retry between renames, but sees no mixed file generation. Exceptions roll back; abrupt machine termination during that narrow gap is a manual recovery case. If the archive directory is missing, preserve the `.archive-production-*/previous` directory, validate it with `python3 -B archive_operations.py validate --output /absolute/path/to/previous`, and restore it as `archive/` before retrying. A leftover `.archive.lock` contains the writer PID; remove it only after confirming that process is no longer running. Never delete a candidate/backup or clear a lock while synchronization is active.

GitHub's failed run status, step logs and job summary are sufficient for this project. Inspect **Actions → TSSE Archive Sync**; account/repository notification preferences determine alerts. No Slack/email integration was added. The CLI prints captured Git/GitHub diagnostics on failure, including rejected pushes.

For a manual GitHub run after activation, select **Actions → TSSE Archive Sync → Run workflow → main**, or:

```sh
gh workflow run archive-sync.yml --repo JoePodcasts/tsse-editorial-os --ref main
gh run list --repo JoePodcasts/tsse-editorial-os --workflow archive-sync.yml --limit 5
```

After correcting the cause, choose **Re-run all jobs** on the failed run, or substitute its numeric ID below:

```sh
gh run view RUN_ID --repo JoePodcasts/tsse-editorial-os --log-failed
gh run rerun RUN_ID --repo JoePodcasts/tsse-editorial-os
```

Alternatively, run locally:

```sh
python3 -B archive_operations.py sync
python3 -B archive_operations.py validate
python3 -B archive_web.py
```

Local recovery updates the local archive only. Review and persist that change through the normal repository process, or rerun Actions from a clean latest checkout. In particular, after a local failed push with a commit already created, do not assume running `persist` again will push it: it creates/pushes only when content is staged. Prefer the clean Actions rerun; a conflicting remote update must be reviewed, never forced.
