# Phase 3 validation — searchable archive frontend

Historical phase report. Current weekly synchronization and freshness behavior are documented in [the operations guide](archive-weekly-sync.md) and [current validation](archive-weekly-sync-validation.md).

Validated locally on 26 October 2026 against the retained complete archive. The six prerequisite audit/design/sync/search documents were reviewed before selecting the architecture. The decision was written in `archive-frontend.md` before creating application files.

## Delivered interface

The buildless frontend uses HTML, CSS and JavaScript with a Python standard-library HTTP adapter. It reuses the official local TSSE logo and Source Sans Pro fonts. No third-party dependencies were added. Search calls the existing `archive_search.query()`; context resolution calls `archive_search.context()`. Catalogue, manifest, source HTML, safe derived text and existing SQLite passage payloads remain authoritative. No episode database, replacement index or browser corpus was created.

The following are implemented and exercised in the actual browser:

- Archive landing/search with live coverage: **195 episodes, 195 transcripts, 195 published show notes**.
- Catalogue browsing with newest/oldest/number sorts and incremental loading through all **195** unique records.
- Unified lexical results with distinct metadata/notes/transcript labels, real publication dates, source text, available timestamps and source speaker labels, lexical match explanations and provenance disclosures.
- Episode detail for every catalogue member, with official title, number, date, duration, format and official episode link.
- Overview, Transcript and Published show notes views; only available content has a reading tab.
- Search within the currently opened episode using the existing episode restriction.
- Deterministic transcript and notes links, highlighted by passage identity and exact source offsets, including direct reload. A sticky reading header retains episode orientation. Invalid/stale passage IDs have explicit recovery links.
- Full source text preservation: reconstructed transcript and note DOM text matched the projection SHA-256 in browser checks. No grammar, names or transcript wording was edited. Unicode code-point slicing prevents UTF-16 drift.
- Responsive desktop, tablet and phone layouts, semantic forms, keyboard submission, current-page navigation labels, live announcements, visible keyboard focus and a skip link.

Original HTML is preserved but never rendered. Notes and transcripts use text nodes from the existing derived text, with only trusted DOM markup for typography. HTML-like query input remains literal text. Original source/text hashes are verified server-side before reading. The local server has no mutation endpoints, no arbitrary file serving and no cross-origin API access.

Speaker labels are source-preserved and **have not been verified against audio**. Untimed transcripts say so; unlabeled continuation passages receive no guessed speaker. Editorial intelligence remains deferred to keep this phase focused on official source retrieval.

## Five required real frontend searches

These results were submitted and opened through the actual frontend, then independently checked through the adapter against `archive_search.context()`. Filters are explicit; rankings were not changed to favor the fixtures.

| Query | Frontend source filter | Actual evidence |
|---|---|---|
| `proof of value` | All sources | Episode **195**, official episode title, first result. |
| `Gokul Rajaram` | All sources | Episode **2**, source speaker-label metadata, first result. Detail discloses audio-verification limitation. |
| `Commerce Ventures` | Show notes | Episode **75**, published show-note heading **About Commerce Ventures**, first result. Opens that exact note passage. Other source matches remain independently visible. |
| `relentlessly resourceful` | Transcripts | Episode **2**, **00:12:34**, source label **Gopi Rangan**. It is the second result: episode 58 legitimately ranks first. Opens the precise question and adjacent source context. |
| `choosing a partner in life` | All sources | Episode **191**, **00:23:15**, source label **Justin Smith-Lorenzetti**, first result. Opens and highlights the exact passage. |

`archive/reports/frontend-browser.json` retains browser assertions and the actual result/passage evidence. The existing eight Phase 2 content fixtures remain covered by the original test suite. Search is an AND of query tokens within one passage, with the existing exact-phrase boost. A query can also return literal all-token matches without the complete phrase; this behavior is disclosed in the interface and was not replaced with semantic search.

## Additional portfolio demonstration queries

Use the **Transcripts** filter for these sequences. All examples below were retrieved from the actual index; exact passages and working URLs are retained in `archive/reports/frontend-demo-queries.json`.

| Query | Examples | Why it works visually |
|---|---|---|
| `customer discovery` | **174** (2025), **00:20:17**, Gopi Rangan; **16** (2020), **00:17:37**, Manan Mehta; also 65 and 60 | Strongest additional demo: understandable founder advice connects material five years apart, with timestamps and source labels on the leading results. |
| `founder market fit` | **125**, **44**, **82**, **42**; 42 includes **00:17:00** | Repeated investment concept across episodes; useful for showing multiple source contexts rather than a single title hit. |
| `contrarian` | **144** (2024), **110** (2023), **161** (2025), **118** (2023) | Clear questions about taking a contrarian view connect older and newer investor conversations. These leading passages are untimed; the UI accurately retains that limitation. |
| `capital efficient` | **68**, **35**, **143**, **44** | Shows related founder/investor language across years, including hyphenated source wording. Prefer the short episode 68 passage about capital-efficient businesses; not every all-token hit has the same degree of relevance. |

For the simplest recording: home coverage → `customer discovery` → Transcripts → episode 174 result → highlighted source; then browse episode 75 → official metadata → notes → full transcript. The required episode 191 query provides a particularly compact timestamp/speaker/context sequence. No fake result, scripted animation or video production was added.

## Measurements

Measurements are local observations on this workstation, not hosted-service guarantees. HTTP samples used warm filesystem data, 20 requests per endpoint, and included JSON transfer. Browser observations used the actual app and five samples per page; they include normal browser loading, with no fake delays.

| Operation | Median | P95 / detail |
|---|---:|---|
| App HTML response | **0.29 ms** | 0.54 ms P95; 1,273 bytes at measurement |
| Initial catalogue API (24 episodes) | **5.78 ms** | 6.29 ms P95; 34,960 bytes |
| Five required search APIs | **7.51–9.14 ms** per-query medians | 8.70–10.51 ms P95, depending on query |
| Broad `founder` search API | **24.57 ms** | 25.91 ms P95 |
| Episode 191 metadata API | **5.43 ms** | 5.68 ms P95 |
| Episode 191 full transcript API | **17.08 ms** | 18.51 ms P95; one 101.48 ms outlier; 162,065 bytes |
| Browser home, JS start to DOM ready | **21.7 ms** | 20.7–34.0 ms range |
| Browser home, navigation to ready | **151 ms** | 148–157 ms, including automation overhead |
| Browser episode overview, navigation to ready | **78 ms** | 67–164 ms, including automation overhead |
| Browser transcript, navigation to ready | **164 ms** | 159–273 ms, including automation overhead |
| Browser search submission to ready | **126 ms** | 117–127 ms across the five required queries, including automation overhead |

The JS-start DOM metric excludes initial asset download and final paint; it is not claimed as total page load. The navigation-to-ready measurements are conservative browser-automation wall times. The app serves about **626 KiB** of initial HTML/JS/CSS/logo/fonts, plus about **34 KiB** of initial catalogue/coverage JSON. Fonts and the logo account for most of this; they are local assets, with no third-party requests. Only one episode's full source is loaded when reading. The browser never downloads the 18,595-passage corpus, the JSONL exports or the SQLite database.

The current index scans episode payloads from its existing documents table for reading; measured latency is small at this size. No Phase 2 index redesign was necessary. HTTP uses a local development server and conservative cache headers; production hosting can add asset caching/compression and a production server after access requirements are agreed.

Raw measurement files: `archive/reports/frontend-performance.json` and `archive/reports/frontend-browser-performance.json`. Reproduce with the benchmark in `tests/frontend/measure_http.py`; browser DOM timings are exposed as an unstyled `data-view-milliseconds` attribute on `main` for tests.

## Tests and issues resolved

Final result: **80 Python tests and 28 actual browser checks passed; no remaining failures**.

- **53 original archive/backend tests** retained and passing.
- **19 additional adapter tests**, including complete coverage, all 195 detail identities, all five required queries, unchanged lexical ranking, scope, real timestamp/speaker cases, missing content, exact notes/provenance, source-integrity failure, stale/wrong-source/wrong-episode passage IDs, malformed inputs and empty results.
- **8 HTTP integration tests**: assets/app, counts/browse, direct passage routes, numeric redirects, CSP/no-CORS, private-file isolation, host/method/input rejection and HEAD behavior.
- **28 browser checks**: actual form submission, source labels and filters, all 195 browse records, metadata/detail navigation, transcript/notes ID selection, direct reload, exact DOM source hashes, source speaker/untimed behavior, scoped search, HTML-like input, no results, stale-link recovery, phone/tablet/desktop overflow and console diagnostics.

The reproducible browser suite found a real fast-typing bug: asynchronous page completion could steal focus from a populated search field before Enter. Focus now moves before fetching data, and the complete suite passes with fast submissions. An initial test assumption that a literal `OR` query should have no results was corrected: the existing search intentionally treats it as a word, not a query operator. No retrieval behavior was changed.

Commands:

```sh
python3 -B -m unittest discover -s tests/archive -v
python3 -B -m unittest discover -s tests/frontend -v
```

Browser automation lives in `tests/frontend/browser-checks.mjs`; invocation is documented in `archive-frontend.md`. It runs with Codex's documented `cua_repl` handles, with no installed browser-test framework. The added full-archive checks explicitly skip if the local archive/index has not been materialized. On this validated checkout no tests were skipped.

## Run and important files

From the repository root:

```sh
python3 -B archive_web.py
```

Open <http://127.0.0.1:8765>. There is no install/build step. If the ignored local index is missing or stale, first run `python3 -B archive_search.py rebuild`. Stop the server with Ctrl+C. The verification server is stopped after capture; the command above starts a fresh session.

| Path | Purpose |
|---|---|
| `archive_web.py` | Read-only HTTP/API adapter over the existing archive/search |
| `web/index.html` | Accessible application shell and official local branding |
| `web/app.js` | Search, catalogue, episode reader, routing and exact passage selection |
| `web/style.css` | Responsive research interface and source typography |
| `tests/archive/test_archive_web.py` | Full-archive adapter integration tests |
| `tests/frontend/test_http.py` | Actual HTTP integration tests |
| `tests/frontend/browser-checks.mjs` | Reproducible end-to-end browser checks |
| `tests/frontend/measure_http.py` | Local HTTP benchmark |
| `docs/archive-frontend.md` | Architecture decision, contracts and run/test instructions |

Screenshots are actual app state in `docs/screenshots/archive/`: [home](screenshots/archive/home.png), [populated results](screenshots/archive/search-results.png), [transcript deep link](screenshots/archive/transcript-deep-link.png), [episode detail](screenshots/archive/episode-detail.png), [published show notes](screenshots/archive/show-notes.png), [mobile home](screenshots/archive/mobile-home.png), [mobile transcript](screenshots/archive/mobile-transcript.png).

## Readiness

**Ready for portfolio recording.** Core retrieval, browse/detail and exact source-context sequences work on real data. There are no blocking usability issues found in the tested views. For recording, select the intended source filter and use the documented short passages; broad queries can yield several matches from one episode. Grouping repeated episode matches, remembering expanded catalogue position when returning, and a phrase-only search control are small future usability improvements, not prerequisites for an honest recording.

**Ready to design the weekly operational phase; not yet ready for unattended weekly execution.** The existing command pipeline is ready and this frontend can consume its refreshed archive. The deployment still needs approved durable archive/index persistence, exact write permissions, failure notifications, retention and refresh/runtime budgets, followed by a complete scheduled-run/recovery exercise. Publish catalogue, accepted sources and rebuilt index coherently; readers fail clearly during a stale-index or promotion gap. A shared deployment also needs an agreed access policy and production HTTP server. These operational choices remain as identified in Phase 2.

No weekly workflow, scheduler, Remotion production, semantic/vector search, AI chat, publishing interface or editorial recommendation work was implemented. The original archive/search implementations and unrelated episode/output files were left untouched. The catalogue/manifest fingerprint still matches the Phase 2 index provenance.
