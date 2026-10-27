# Archive frontend

## Architecture decision (before implementation)

Use a buildless HTML/CSS/JavaScript frontend and a small, read-only Python standard-library HTTP adapter. The repository's archive pipeline already uses Python and SQLite FTS5; adding a JavaScript application framework or a second server runtime would add maintenance without improving retrieval.

`archive_web.py` will call `archive_search.query()` for search and `archive_search.context()` for passage resolution. The catalogue and manifest remain the source of episode metadata and coverage. Episode reading uses the existing SQLite passage payloads and hash-verified derived text, fetched only for the selected episode. There is no additional episode database or browser copy of the corpus.

Canonical episode URLs use the remote UUID. Transcript and show-note URLs carry the existing passage ID. The server verifies that the passage belongs to that episode and source; the browser uses its exact Unicode offsets to render and highlight it, including after a direct reload. Missing or outdated passages produce an explicit message.

Original source HTML is never sent to an HTML renderer. The frontend creates text nodes from the existing safe text projection. Source hashes, locators and passage IDs remain available in a provenance disclosure. Speaker labels are presented as source labels with an explicit audio-verification limitation.

The interface uses the repository's TSSE logo and Source Sans Pro fonts, a restrained navy/cyan palette, and responsive layouts. It needs no package install or build. It binds to localhost by default and serves allowlisted application assets, read-only JSON endpoints, and the existing portable exports.

This architecture section records the original frontend decision. Weekly synchronization is now implemented separately through [the production operations command](archive-weekly-sync.md). Editorial intelligence, publishing, semantic search and audio verification remain outside the frontend scope.

## Running locally

From the repository root:

```sh
python3 -B archive_web.py
```

Open <http://127.0.0.1:8765>. Use `--port` to change the port or `--archive` to select an archive directory. If the local ignored SQLite index is missing or stale, run `python3 -B archive_search.py rebuild` first. Python must include SQLite FTS5, as required by Phase 2.

After a production `python3 -B archive_operations.py sync`, all required archive artifacts are already prepared. For a fresh checkout after activation, `python3 -B archive_web.py --github-status JoePodcasts/tsse-editorial-os` validates/rebuilds missing derived files and restores matching successful-sync metadata from Actions before serving. This explicit preparation option requires authenticated `gh`; it neither pulls Git nor continuously polls. See the operations guide for checkout and artifact-retention details.

## Read-only API

- `GET /api/archive`: live catalogue and source coverage.
- `GET /api/sync-status`: persisted, fingerprint-matching last successful source check, or `null` when no matching evidence exists.
- `GET /api/episodes?sort=newest|oldest|number&offset=0&limit=24`: catalogue pages.
- `GET /api/search?q=…&source=all|metadata|transcript|show_notes&episode=…&limit=…`: existing lexical search, with result URLs and catalogue publication dates.
- `GET /api/episodes/<uuid>`: official metadata and source availability.
- `GET /api/files`: validated portable-file counts, fields, byte sizes, download URLs and the same successful synchronization status.
- `GET /api/episodes/<uuid>/file`: the actual generated Markdown text, filename and SHA-256.
- `GET /downloads/catalogue.csv`, `/downloads/episodes/<uuid>.md`, `/downloads/markdown-library.zip`: verified attachments.
- `GET /api/episodes/<uuid>/content?source=transcript|show_notes&passage=…`: verified text, existing passage spans and source provenance. Optional passage resolution validates the deep link.

Stable views: `/`, `/?q=…&source=…`, `/episodes/<uuid>`, `/episodes/<uuid>/transcript?passage=<id>`, and `/episodes/<uuid>/show-notes?passage=<id>`. Archive file views are `/archive-files`, `/archive-files/episodes?sort=newest|oldest|number`, and `/episodes/<uuid>/file`. Numeric episode aliases redirect to the canonical UUID URL, preserving query parameters.

## Reading and retrieval contracts

The adapter opens the existing SQLite index in read-only mode. It preserves lexical ranking, query tokenization, field boosts and passage IDs. Search displays at most 30 matches initially, expands to 100, and truthfully indicates truncation; source filters and episode scope refine the same retrieval call. The frontend groups the returned matches by episode, then metadata/show notes/transcript. Episode order follows each episode’s best-ranked match; source groups follow their first occurrence; passages within each source group retain ranked order. One best match per source group is initially visible; a keyboard-accessible control reveals the remaining loaded passages. Counts explicitly distinguish episode groups from source matches and label truncation. This presentation does not re-rank retrieval or claim global flat ordering across the grouped hierarchy. Every word must occur in the same indexed passage; exact phrases receive the existing ranking bonus. This is lexical search, not semantic relevance.

Episode content requests read only the selected episode's indexed payloads and derived text. Before serving content the adapter verifies original-source and text hashes, passage identity, offsets and excerpt equality. It refuses mismatched or stale content. The browser converts text to Unicode code points before slicing Python's offsets; JavaScript UTF-16 indices would otherwise drift around emoji. It preserves gaps and passage text, including original grammar and label spellings.

Transcript and notes content is constructed using text nodes. No source-controlled string is passed to `innerHTML`, a template interpreter or an HTML insertion API. Source URLs shown as external links accept only HTTP(S). A restrictive content security policy, no CORS, localhost binding and a static-file allowlist limit the local surface. This is a local research app; authentication, TLS, a production web server and access policy must be selected before shared hosting.

Coverage is derived from the catalogue and manifest on each request. Missing content remains a visible availability state; its reading tab is omitted. The interface does not invent timestamps or continue a speaker attribution into unlabeled passages. Labels and timestamp markers are from the source; neither proves audio identity or exact audio alignment.

Default web startup does not rebuild the index. The explicit `--github-status` preparation option validates/rebuilds missing derived files before serving; there is no write endpoint. Run the production pipeline separately to check official sources. A stale/missing index yields a clear error. During an archive directory promotion, a brief failed read can require retrying the view, as documented by the existing sync contract.

The homepage places a muted `Last successful sync … PT` line below coverage and Archive Files; Archive Files shows the same record. Formatting explicitly uses `America/Los_Angeles` and a semantic `<time datetime>` with the original UTC instant. A failed check does not advance it; a successful no-change check does. It is not a Git/build/file timestamp. No record yields an honest unknown state; a success older than nine days adds `Weekly check overdue`. The UI does not claim real-time freshness or repeat the line on individual episode pages.

## Portable files and search context

`archive_files.py` validates the existing CSV and Markdown exports against the published catalogue, manifest, source HTML and current exporter. It verifies UTF-8, canonical UUID mapping, all metadata, and transcript wording/timestamp sequences. The frontend reads the actual Markdown bytes into text nodes, with section anchors; it does not reconstruct a second document. CSV and Markdown downloads serve those same bytes with attachment headers.

The frontend library ZIP is built on demand using Python's standard library, sorted UUID filenames, fixed timestamps and permissions, and fixed compression settings. It contains the current published Markdown files under `episodes/`; the count is dynamic. Their embedded source HTML and source-reference sections are intentionally retained; separate internal source files, manifest, index and reports are excluded. A revision-aware in-memory cache avoids repeat validation/compression and invalidates when catalogue, manifest or export stat signatures change. Individual file reads recheck their hashes. The web adapter writes no files. The production synchronizer also validates an ignored, reusable local ZIP cache using this same implementation.

Result links carry a same-origin, validated `return` URL with query, source filter, episode scope, loaded limit and expanded groups. Readers show the query and a Back to search results link in the sticky context bar. Overview, source tabs and the Markdown view preserve that origin, including on direct reload. Expanded groups are URL state; browser pixel scroll position is not explicitly restored. Loading more matches currently starts collapsed groups in the expanded result set.

## Verification

```sh
python3 -B -m unittest discover -s tests/archive -v
python3 -B -m unittest discover -s tests/frontend -v
python3 -B tests/frontend/measure_http.py
```

The second command binds an ephemeral loopback port. The benchmark requires the main server running. The original 53 fixture tests still run offline. The added full-archive adapter tests explicitly skip when the local ignored index has not been materialized.

`tests/frontend/browser-checks.mjs` is a reproducible browser suite using the documented Codex `cua_repl` tab/viewport handles. After selecting the browser/tab and reading its controls, it can be run inside `cua_repl`:

```js
const suite = await import('file:///Users/jwanyua/tsse-editorial-os/tests/frontend/browser-checks.mjs');
const viewport = await browser.capabilities.get('viewport');
const report = await suite.runArchiveChecks(tab, viewport);
// Save/report the returned checks, then restore the normal viewport.
await viewport.reset();
```

This browser suite is not a standalone Node driver. Production needs only Python and a browser; no npm install/build step or third-party package was added. See [Phase 3 validation](archive-frontend-validation.md) for actual measurements, source fixtures, screenshots and readiness.

The portable-file refinement adds `tests/frontend/files-browser-checks.mjs`; call `runFilesChecks(tab, viewport, repositoryRoot)` in the same browser environment. See [archive files validation](archive-files-validation.md) for current counts, 97 Python tests, 77 browser checks, download integrity, query comparison and screenshots. The Phase 3 report remains the historical baseline.

Current operational validation and updated counts are in [weekly synchronization validation](archive-weekly-sync-validation.md). `tests/frontend/sync-status-unit.mjs` checks Pacific winter/summer/DST formatting. `tests/frontend/sync-browser-checks.mjs` verifies the persisted timestamp and responsive homepage/Archive Files treatment through `runSyncChecks(tab, viewport, repositoryRoot)`.
