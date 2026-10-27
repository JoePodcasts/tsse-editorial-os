# TSSE archive on Vercel

## Current result — 27 October 2026

The existing product is packaged and locally validated for Vercel. **No Vercel Preview or Production deployment has been created or verified.** The connected Vercel account cannot access the user-selected team, `joegakere-8265` (`team_rq5ezpuosc6oqLCUk87wamZq`); the project API returns 403, and the team authorization endpoint returns 404 for both the resolved team ID and slug. The Vercel connection must use an identity with access to this team before project creation can continue. There is no project ID, project link, production URL or DNS change yet. The GitHub repository is **private**. Its visibility must remain unchanged.

The scheduled workflow is not active until the reviewed archive baseline and workflows reach `main`. Do not share the localhost address as a public product URL. Cloud routing, protection settings, actual cold starts, production-domain assignment and runtime freshness credentials still require the account steps below.

## Architecture decision

Preserve the buildless HTML/CSS/JavaScript frontend, Python `ArchiveApp` and SQLite FTS5 retrieval. A single supported `BaseHTTPRequestHandler` entrypoint, `api/archive-function.py`, handles API requests. No React, Next.js, database or search migration. Python 3.12 is selected explicitly.

Build time validates the accepted canonical archive and exact CSV/Markdown exports, rebuilds the existing SQLite index in an isolated directory, and constructs explicit `public/` and `vercel_runtime/` directories. Runtime only reads these files. Ingestion, source updates, index construction, Git writes and ZIP compression never run in a web request. All six required search queries are compared with the canonical index during the build, including passage identities, text and ranking.

HTML, CSS, JavaScript, logo/fonts, CSV, individual Markdown and the reproducible ZIP are static/CDN files. Python handles coverage, browse/sort/filter, lexical search, source readers, passage resolution, export inventory and synchronization status. The Episode File view fetches the same static Markdown download, checks its SHA-256, and renders it as text. The local development adapter can still supply inline Markdown, so its existing behavior remains supported.

References: [Python API handlers](https://vercel.com/docs/functions/runtimes/python/api-directory), [Python bundle controls](https://vercel.com/docs/functions/runtimes/python), [function limits](https://vercel.com/docs/functions/limitations).

## Exact deployment contents

| Content | Destination and reason |
| --- | --- |
| Published catalogue and reduced manifest | Python: membership, metadata and source availability |
| Current official metadata, summaries, notes and transcripts | Python: original-source hash verification |
| Their current normalized text | Python: source reading and verified passage offsets |
| Rebuilt `archive.sqlite3` | Python: original FTS5 ranking and passage lookup |
| Validated export inventory | Python: counts, filenames and hashes without revalidating the whole library on requests |
| Last successful matching sync record | Python: fallback during credential/network/artifact outages |
| Seven existing/new Python modules and the entrypoint | Python application code; standard library only |
| `web/index.html`, app.js, style.css, logo and two Source Sans fonts | Static UI, unchanged visual language |
| Existing catalogue.csv, 195 existing Markdown files, deterministic ZIP | Static downloads with exact original bytes |

Excluded from the function: repository `data/`, `outputs/`, private/editorial inputs, provisional episodes absent from the published catalogue, historical source revisions, full episode-detail responses, legacy source files, segment JSONL, large passage/search-document JSONL, tests, docs/screenshots, local reports, `.git`, `.env`, operational ingestion state and ZIP/Markdown/CSV duplication. Static output is an explicit asset allowlist; there is no generic repository/file-serving route.

The reduced manifest removes editorial references and history. The API removes repository path fields from provenance, retaining official URLs, hashes, offsets and source identity. Markdown downloads preserve the existing portable archive-relative source references required by their format. These are not host paths or filesystem routes. Public text is scanned for credential-shaped values, local host paths and localhost URLs. The scanner distinguishes legitimate official links such as `https://leap.cl/en/home/` from absolute filesystem paths.

`functions.excludeFiles` was exercised with Vercel's actual glob implementation, then the official Python builder. Only the entrypoint/generated runtime and Vercel's own support package enter the function. The private repository's other content is not published.

## Configuration and new files

- `vercel.json`: Other/no framework; build `python3 -B archive_deploy.py build`; output `public`; one Python function, 30-second limit; API/SPA rewrites; download/security/cache headers; automatic Git deployments disabled in favor of the explicit validated pipeline.
- `.python-version`: Python 3.12. No application dependency manifest is needed; the Python runtime supplies its own handler support.
- `api/archive-function.py`: imports the generated Python adapter and exposes `handler`.
- `archive_deploy.py`: validates, builds the index, trims inputs, copies exact exports, compares retrieval, tests all source readers, checks budget, then replaces build-owned directories atomically at directory level. Prior outputs survive validation failure.
- `archive_public.py`: read-only public adapter, prevalidated inventory, clean HTTP errors, write-method rejection.
- `archive_status.py`: matching success-record validation and server-only GitHub Actions artifact retrieval, with a 60-second process cache and last-known-good fallback.
- `.vercelignore`: allowlisted CLI source upload; production function/static boundaries are enforced separately. `.gitignore` excludes generated outputs and provider-local credentials/configuration.
- `.github/workflows/archive-deploy.yml`: reusable, manual and main-push production workflow; build, stage, HTTP-check and promote exactly that build.
- `tests/deployment/`: artifact/rollback/error/read-only tests, a reusable real-HTTP smoke checker, runtime credential check and local packaging harness.

The actual Vercel routing compiler accepted the configuration. The API rewrite preserves search query parameters and supplies the route to the one function. Download filename capture substitution compiles correctly. Actual cloud behavior remains a Preview validation item.

## Success-only freshness without content commits

The earlier choice remains intact: **no timestamp-only commits and no deployment on a successful no-change sync**.

After candidate validation, regression checks and successful Git persistence, the sync workflow uploads:

1. `archive-sync-state`: operational restore evidence (existing behavior).
2. `archive-status-<archive fingerprint>`: only `sync-status.json`, for the frontend, retained for 90 days.

The timestamp is the actual successful sync time already recorded by the synchronizer. It is never derived from upload, build, commit or server time. New/changed flags, episode count and fingerprint are validated before use. The API selects the newest unexpired matching artifact from `main`, reads only a bounded ZIP containing exactly `sync-status.json`, and validates its schema/count/fingerprint/time. The record cannot move backward. Failed syncs never reach the upload steps. If a later deployment fails, an already completed and validated synchronization remains a real success.

Because the repository is private, Vercel requires **`ARCHIVE_STATUS_TOKEN`**, a server-side fine-grained GitHub credential restricted to this repository with **Actions: read** (plus mandatory metadata read), and no content-write permission. [GitHub artifact API permissions](https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28). Configure it for Preview and Production in Vercel, never in frontend code or Git. GitHub organization approval may be required. Runtime API responses expose only the validated success fields, never the credential, artifact logs or ingestion state. Authorization is stripped when following the signed artifact-storage redirect.

Requests refresh the matching status at most once per 60 seconds per warm process. A normal page reload can then display a later no-change check without a new deployment. This is weekly checking, not realtime sync or a push update to already-open pages. Missing/expired artifacts, missing/revoked credentials, failures and malformed/mismatched records preserve the bundled/last verified success. The frontend continues to say **Last successful sync**, with the timezone-safe `America/Los_Angeles` formatter and `PT` label; it does not make an unsupported “Up to date” claim.

Builds from fresh Git checkouts retrieve the matching artifact using the job's scoped GitHub token. A local preview can use the already persisted local success file. Production deployment additionally verifies the *actual Vercel runtime credential* pulled into ignored `.vercel/.env.production.local`; a working build token alone cannot prove runtime freshness. The check does not print the credential or add it to artifacts.

An unauthenticated GitHub release-asset design was tested and rejected after confirming repository privacy. The temporary release/tag created for that check was removed. The final implementation uses Actions artifacts only; no repository visibility change, extra public repository or new database/storage service is required.

## Weekly sync → deployment

The schedule remains **Tuesday 06:30 America/Los_Angeles**, following the expected 04:00 publication. GitHub handles the Pacific schedule's daylight-saving transition.

For a newly published episode: official catalogue → isolated sync candidate → sources/CSV/Markdown/index/ZIP validated → regressions → conditional content commit and fast-forward push to main → both success artifacts uploaded → reusable deployment workflow called with that exact commit → clean build → production-target deployment staged with `--skip-domain` → real HTTP smoke checks → confirm main has not advanced → `vercel promote` the tested deployment.

A bot push with `GITHUB_TOKEN` does not start an ordinary downstream GitHub `push` workflow. Vercel's separate Git integration also has commit-author/organization rules and can race status publication. The implementation therefore does not depend on either behavior: the sync workflow directly calls the reusable deployment workflow. Human code/content pushes to main trigger that same deployment workflow normally. `git.deploymentEnabled: false` prevents a second unvalidated Git-triggered deployment. The repository can remain linked to the Vercel project for identity/navigation, but deployment is deliberately controlled by Actions.

This modest deviation from the initial Git-webhook sketch provides explicit sequencing and prevents domains pointing at an unverified build. Deploy hooks were not selected because they still require Git integration and introduce another trigger/configuration interaction. [GitHub token events](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow), [Vercel Git controls](https://vercel.com/docs/project-configuration/git-configuration), [staged deployments](https://vercel.com/docs/cli/deploy).

A no-change run uploads success artifacts, creates no content commit, and skips the deployment job. A failed sync publishes neither a new content state nor success record. A later publish/deploy failure is visible in Actions; the existing public deployment remains available. If content was committed but publication/deployment failed, rerun the failed jobs or manually dispatch **Deploy TSSE Archive** after restoring a valid status artifact. A fresh no-change run alone intentionally does not deploy.

## Vercel/GitHub setup and first release

1. Use a Vercel connector identity with access to `joegakere-8265` (the current identity cannot obtain a team-access link), or sign in locally with `npx vercel@65.4.0 login`. Do not paste credentials into chat.
2. Create/select a Vercel project such as `tsse-content-archive` in that team. Set Framework **Other**, root **repository root**, Python **3.12**, Build Command `python3 -B archive_deploy.py build`, Output Directory `public`. There is no install/build frontend framework. Connect `JoePodcasts/tsse-editorial-os` only if the team's GitHub app has permission to that private repository. Confirm the team's plan permits this private organization repository; do not change repository visibility to bypass a plan restriction.
3. Set Vercel `ARCHIVE_STATUS_TOKEN` for Preview and Production as described above. Use the public production access setting required for public review; retain protection on Preview if desired, supplying an automation bypass secret to the deployment smoke check. Public access/protection and the project itself have not been changed by this task.
4. Link the reviewed checkout using `npx vercel@65.4.0 link --scope joegakere-8265 --project tsse-content-archive`. Record the returned `orgId`/`projectId`; they are not credentials. Do not invent them.
5. Validate a Preview before production. With Python 3.12, Node 20.12+ and `uv==0.9.25` installed, run:

   ```sh
   npx vercel@65.4.0 pull --yes --environment=preview
   npx vercel@65.4.0 build
   npx vercel@65.4.0 deploy --prebuilt
   python3 -B tests/deployment/smoke.py https://ACTUAL-PREVIEW-URL.vercel.app
   ```

   The URL above is a placeholder, not an existing deployment. Use the actual CLI URL. The local ignored success file supplies the first build's baseline. Protected Preview requires `VERCEL_AUTOMATION_BYPASS_SECRET` in the test environment or authorized browser access. Do not disable protection just to bypass a test failure. Repeat the documented browser checks/screenshots against the actual Preview, including direct passage reload and mobile/tablet file views.
6. In GitHub, create the `production` environment restricted to `main`. Configure repository/environment variables `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`; secret `VERCEL_TOKEN` scoped to the selected Vercel team/project; optional `VERCEL_AUTOMATION_BYPASS_SECRET` for staged deployment protection. Store secrets directly in the account UI. The user has authorized unattended weekly synchronization/deployment; a required human reviewer would pause that automation, so configure environment review policy deliberately. Actions need contents-write only in the sync job; deployment has contents-read/actions-read. No PAT is used to push archive content.
7. After Preview validation, merge the reviewed baseline to `main`. First manually run **TSSE Archive Sync** on main to create the first authenticated matching success artifacts. Then run **Deploy TSSE Archive** on main (a no-change sync intentionally skips deployment). A push-triggered build before that initial artifact exists must fail safely. The pipeline checks the real runtime credential, stages, validates and promotes. Record and verify the resulting production domain before sharing it.
8. Verify the next scheduled run in Actions, artifact timestamp and public `/api/sync-status`; confirm a no-change run has no commit or deployment. For a later new episode, confirm counts, sources, search, file, CSV and ZIP update together. The 196-episode simulation already passes locally; it is not real published content and is not included in the bundle.

No custom domain is necessary for initial review; the verified Vercel production domain is sufficient. DNS work is not performed or required yet.

## Headers, routing and errors

Static HTML/assets/exports use `public, max-age=0, must-revalidate`, avoiding stale content under stable filenames without claiming immutable URLs. Vercel serves them from its static/CDN layer. API/search/status responses use `no-store`; status itself has the bounded internal cache described above. Security headers include nosniff, no-referrer and a same-origin CSP that disallows source HTML execution, framing and object content.

CSV is UTF-8 `text/csv`, Markdown UTF-8 `text/markdown`, ZIP `application/zip`; download dispositions retain the intended filenames. The ZIP is a static 3,918,604-byte file, not a function response. Direct SPA routes include archive/files, episode overview, transcript, show notes and Episode File. Unknown episodes/passages and malformed queries retain the existing clean UI recovery states. Missing static files return 404. Unexpected backend exceptions are logged server-side and return a generic 503 with no traceback or host paths. POST/PUT/PATCH/DELETE return 405.

## Validation and measurements

The real local package contains 195 published catalogue members, transcripts, show-note records and Markdown files. The last-successful record is **2026-10-27T05:26:17.109254+00:00**, displayed as **Oct 26, 2026 · 10:26 PM PT**. It reports zero new/changed episodes. No synthetic episode was installed in the accepted archive.

| Check | Verified locally | Actual Vercel |
| --- | --- | --- |
| Existing archive tests | 113 passed, including simulated new episode, no-change and rollback cases | Pending first workflow |
| Existing HTTP tests | 14 passed | Not a cloud substitute |
| Deployment-specific tests | 15 passed | Pending first workflow |
| Pacific time formatting | Five standard/daylight/transition cases plus missing/failed states passed | Same code; browser verification pending |
| HTTP smoke | 82 checks passed: all six queries, source passage, counts, files, exact CSV/ZIP/MD hashes, clean errors | Pending Preview |
| Browser archive tests | 28 passed: browse all members, grouped search/filter, source-fidelity hashes, direct deep-link reload, responsive readers | Pending Preview |
| Homepage/Archive Files layouts | 1366, 768 and 375 px, no horizontal overflow; sync label visible | Pending Preview |
| Episode File/browser ZIP | Exact Markdown hash; complete 3,918,604-byte ZIP download and expected SHA-256 | Pending Preview |
| Read-only/error behavior | Requests leave all runtime hashes unchanged; generic 503 hides internal path; write methods rejected | Pending Preview |
| Vercel package/compiler | Official Python builder and routing compiler passed locally | Cloud build pending |
| Status-only publication | Private artifact format/cache/failure/credential-isolation tested with fixtures | First scheduled artifact and Vercel credential check pending |

All six searches returned identical canonical ranking/passage/text results: customer discovery (16), proof of value (10), Gokul Rajaram (16), Commerce Ventures (16), relentlessly resourceful (6), choosing a partner in life (4). These are measured live lexical results, not query-specific precomputed answers.

Approximate measured sizes (exact inventories are generated in ignored `.vercel/archive-build-report.json`):

| Artifact | Size |
| --- | ---: |
| Full Python bundle including provider runtime | 71.9 MiB |
| Application runtime + archive data | 70.2 MiB |
| Archive data within runtime | 70.15 MiB |
| SQLite index | 58,122,240 bytes / 55.43 MiB |
| All static files | 18,790,766 bytes / 17.92 MiB |
| Static ZIP | 3,918,604 bytes / 3.74 MiB |

This is comfortably below Vercel's documented standard Python 500 MB uncompressed limit and the build's stricter 250 MB application budget. No large-function beta. The original local archive is about 178.6 MiB, so the build does not simply ship it wholesale. The runtime file-selection check found no unexpected application files.

Local representative timings: validated artifact build about 14 s; index build about 5 s; official Python packaging about 11 s. Python 3.12 process initialization plus first search measured 22.37 ms, subsequent search 3.84 ms. Final local HTTP first search 15.93 ms, four-request median 4.51 ms; homepage 13.97 ms; baseline freshness API 0.60 ms; selected transcript JSON 117.14 ms; Markdown 2.25 ms; ZIP 2.74 ms. These are localhost/warm-filesystem samples, **not Vercel cold-start or network/CDN measurements**. The initial rejected unauthenticated status mechanism took 3.7 s; it is not the final private-artifact implementation. Actual private-artifact request latency and cloud performance remain to be measured after credentials/access are configured. The fallback remains usable during outages.

Evidence is in `docs/screenshots/archive-vercel/`: build/package summaries, HTTP/browser/layout reports, desktop/tablet/mobile homepage and Archive Files PNGs, and Episode File PNG. Local harness command: `python3 -B tests/deployment/preview_server.py`; it serves generated outputs on `http://127.0.0.1:8766`. It is explicitly not a Vercel emulator.

## Rollback and operational recovery

Retain the last good deployment until a staged successor passes smoke checks. On production regression, use Vercel's rollback to the last verified deployment. Its own bundled fingerprint/count/status remains internally consistent; it cannot adopt a success record for a newer catalogue. Vercel rollback may disable automatic domain assignment; the next verified `vercel promote` restores the intended release flow.

For a corrupt build input, repair/re-sync and validate the canonical archive; do not edit deployed SQLite or transcript text. For token expiry/artifact outage, replace the server-only read credential or rerun a successful sync to recreate its artifact. Existing users keep the last known good timestamp. Never create a fictitious timestamp to make the site look fresh. Keep GitHub workflow failure notifications enabled, and inspect Vercel runtime logs after the first live smoke run. No real Vercel error scan, monitoring or performance claim is possible before a project exists.

**Readiness:** locally ready for account setup and a real Preview validation. Not yet ready to share as a live public product, test with external users, or record as a deployed portfolio application. No Remotion work has been started.
