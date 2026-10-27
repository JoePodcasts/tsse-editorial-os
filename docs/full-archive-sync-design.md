# Full TSSE catalogue synchronization and structured text-library design

Status: **proposed; awaiting review before implementation**. Investigation: 26 October 2026, Africa/Nairobi. Read alongside [the repository audit](archive-interface-audit.md). No frontend, sync command, scheduler, bulk transcript ingestion, search index, or source-data changes were implemented.

## 1. Executive summary

The official public Simplecast integration can enumerate the complete public published TSSE catalogue. Live inspection returned **195 distinct remote episode IDs**, numbered **1–195**, across **two pages (100 + 95)**. Every returned record has an official title, number, slug, publication timestamp, duration, description, audio enclosure URL, GUID, status, type, season and update timestamp. Artwork is present for 194/195.

The existing fetcher already retrieves all pages. Its normalization/reporting stages then narrow the result to newsletter work after the latest history reference. They are unsuitable as the archive membership definition.

A small detail-response investigation uncovered a simpler ingestion route than the historical browser workflow: `GET /episodes/{id}` returns **`long_description` HTML and `transcription` HTML**. Both are populated for all **five sampled episodes: 1, 2, 75, 191, 195**. Episode 195's live website visibly distinguishes the list's short `description` as “Episode Summary” and the detail's `long_description` as “Episode Notes.” Retain both, with different names. Do not claim all 195 have full notes/transcripts until separately approved ingestion checks every detail response.

Recommended architecture:

1. Official public catalogue membership keyed by **`simplecast:<remote UUID>`**.
2. Preserved source snapshots and a separate source/availability manifest.
3. Normalized catalogue records and deterministic text projections with source references.
4. Reproducible UTF-8 Markdown and CSV exports, never separately hand-maintained.
5. One weekly sync, preserving changed versions and reporting incomplete fetches; lexical search follows later.

Current reusable repository transcript coverage is **56/195 = 28.7%**; **33/195 = 16.9%** have bracketed timestamps. The existing strict validator accepts 47/195 (24.1%), but rejects nine substantial early transcripts because of formatting. These counts describe local content, not remote availability. Temporary API samples are investigation evidence, not newly ingested library records. Provisional episode 196 is not in the live published list and must not become a published catalogue member merely because a local file exists.

## 2. Existing discovery capability

### Actual request path

`episode_discovery.py`:

1. `POST https://api.simplecast.com/sites/search` with JSON `{"url":"https://podcast.sure.ventures"}`. This is a read-only lookup despite using POST.
2. Read `podcast.id`: `8a5f01b8-f271-4de0-b289-c224dc4fce0a`.
3. `GET https://api.simplecast.com/podcasts/{podcast_id}/episodes?status=published&private=false&sort=latest&limit=100&offset=0`.
4. Append `collection`; follow `pages.next.href` via `urljoin` until absent.
5. Normalize each episode, sort by episode number, compare against numeric `featured_episode` history values, then save only newest/recommended episode and the tail above the maximum represented history number.

The complete list exists in memory before step 5. `normalize_episode()` additionally drops records lacking a number or slug. That exclusion must not be copied into the catalogue: stable-ID episodes with incomplete metadata still belong.

Number resolution uses Simplecast `number` if integer-convertible, otherwise a `tsse[-_]?N` slug regex. It does not infer number from title or description. All 195 current list numbers are supplied as integers, so fallback is unnecessary for this snapshot. Guest inference is a separate regex over description/title and is not an official structured guest field.

Current retained fields: `episode_number`, `episode_title`, inferred `guest_name`, constructed `episode_url`, constructed `transcript_url`, `published_at`, `slug`, `simplecast_id`. Discarded list fields include duration, description, GUID, season, type, artwork, audio enclosure, status, hidden flag and update time. Detail content is not fetched by this discovery code.

No authentication header, credential configuration or secret is used by these public calls. The fetcher uses standard-library urllib and repository-relative paths; its CLI nevertheless writes a report, so investigation called read-only functions rather than `main()`. It has a 30-second request timeout but no retry/backoff, duplicate/page-cycle guard, or complete-snapshot transaction. Reuse the request/pagination logic conceptually, not its newsletter filtering or mutation path.

Official general API documentation describes bearer-token authentication for management APIs; the **specific public calls tested here succeeded without credentials**. That observed access should not be generalized to private/draft management endpoints. See [Simplecast API documentation](https://apidocs.simplecast.com/) and [official API guide](https://help.simplecast.com/hc/en-us/articles/21953603587613-Simplecast-API).

## 3. Official source/API findings

### Live evidence and boundaries

| Check | Observation |
|---|---|
| Public list | 195 records, 195 unique UUIDs, contiguous supplied numbers 1–195 |
| Pagination | `pages.total=2`, `limit=100`; first page 100, second 95; final `next=null` |
| Publication state | All `status=published`, `is_hidden=false`; all `scheduled_for=null` |
| Type/season | All `type=full`; season objects available for all |
| Latest item | Episode 195, “Show Proof of Value Before You Build for Scale,” published 22 September 2026 |
| Small detail sample | Episodes 1, 2, 75, 191, 195; all returned notes and transcripts |
| Page corroboration | Episode 195 shows summary, fuller notes, linked time cues, guest/company background, transcript navigation and contributors |
| Response headers | Recheck returned server Dates 26 October 2026 08:35:59 and 08:36:02 UTC; no ETag, Last-Modified, Retry-After or rate-limit headers observed in those list responses |
| Scope | Full metadata listing only; five details sampled; no audio download and no whole-archive transcript fetch |

Useful direct sources: [public episode listing](https://api.simplecast.com/podcasts/8a5f01b8-f271-4de0-b289-c224dc4fce0a/episodes?status=published&private=false&sort=latest&limit=100&offset=0), [episode 195 detail](https://api.simplecast.com/episodes/254fc97f-8c85-4d1a-bc84-0e230ec99cb5), and [published episode 195 page](https://podcast.sure.ventures/episodes/tsse195-show-proof-of-value-rohini-chakravarthy).

The historical root discovery report ending at 191 and local episode 192 package are not the live count. The prior audit's local lower bound of 190 also is not the official denominator. Episode 1 is an introductory recording but the source marks it `full`; retain that source value rather than relabeling it as a trailer. Do not infer publication from a season's next-number counter.

### Limits of status visibility

The list explicitly requests public published content. `status`, `is_hidden`, `scheduled_for`, and detail `is_published` are observed fields. `type` can be retained as the source's episode-type string, but no trailer or bonus examples occurred in this response. Preserve unfamiliar future types rather than rejecting them.

Draft/private/deleted episodes are not enumerated by this public request. Absence cannot distinguish deletion, unpublishing, privacy change, or an incomplete remote response. Never query private content by guessed IDs or label an absent item “deleted” without evidence. Keep last-known published metadata with an explicit “not seen in complete public snapshot” observation.

### Pagination and rate limits

No numeric rate quota was established. Do not invent one. Start with sequential requests and a configurable modest delay; on 429 honor `Retry-After`, otherwise use bounded exponential backoff with jitter for transient errors. Treat 401/403 as an access/configuration failure, not a reason to seek broader credentials automatically. Follow only HTTPS pagination links on the approved API host. Reject repeated page URLs, conflicting duplicate IDs, malformed collections, and unexpected podcast IDs. Check page-total/count consistency where meaningful; do not assume a field named `count` means total rather than page count without validating its semantics.

Offset pagination is not demonstrated to be snapshot-isolated. Deduplicate by remote ID and flag changing totals/ordering. On inconsistency, retry the entire small list once; do not use that run to infer removals. A valid complete result is required for membership reconciliation.

## 4. Available metadata fields

“List 195/195” means verified across the complete returned list. “Detail 5/5” means sample evidence only.

| Field | Available from source? | Existing discovery retains? | Reliability | Recommended catalogue field |
|---|---|---|---|---|
| Stable episode UUID | List 195/195 `id` | Yes, `simplecast_id` | Strong source identity | `episode_id`, `remote_id` |
| Podcast UUID | Site lookup; detail podcast object | Not on each normalized episode | Scope identity | `podcast_id`, `provider` |
| Episode number | List 195/195 integer `number` | Yes, with slug fallback | Human/editorial value; may change or repeat in future | Nullable `episode_number`, `number_origin` |
| Official title | List 195/195 `title` | Yes, renamed | Preserve exact string | `official_title` |
| Guest names | No dedicated verified list field | Regex inference | Unreliable extraction; do not present as source field | Separate attributed `participants`, not invented guest metadata |
| Contributors/authors | Detail 5/5 `authors.collection` | No | Includes people and companies, not necessarily speakers/guests | Preserve source contributors separately; never auto-copy to `speakers` |
| Publication time | List 195/195 `published_at` | Yes | Offset-bearing source time | `published_at`; optional derived UTC value |
| Duration | List 195/195 positive integer `duration` | No | Seconds corroborated by 195: 2262 = player 37:42 | `duration_seconds` |
| Episode web URL | Slug 195/195; detail `episode_url` | Constructed from slug | Detail URL often homepage (1,75,191,195); episode 2 is specific | Construct TSSE permalink from site base/slug; `episode_url_origin=site_slug`; keep raw URL |
| Audio URL | List 195/195 `enclosure_url`; detail audio URLs | No | Current delivery URL, may change/redirect | `audio_url` from enclosure; no audio-file ingestion |
| Short summary | List 195/195 `description` | Read for inference, discarded | Published summary, not full notes | `summary`, plus source field reference |
| Full show notes | Detail 5/5 `long_description` HTML | No | Episode 195 visibly corroborated as Episode Notes | Source manifest `show_notes`; catalogue reference rather than duplicate HTML |
| Transcript | Detail 5/5 `transcription` HTML | No | Official hosted source text, audio correctness unverified | Source manifest `transcript` |
| Episode type | List 195/195 `type=full` | No | Source type, not media MIME | `episode_type` |
| Media format | Detail 5/5 `audio_content_type=audio/mpeg` | No | Sample-only coverage | Nullable `media_mime_type`; do not infer video availability |
| Season | List 195/195 `season.number` and href | No | Preserve supplied value | Nullable `season_number`, source season reference |
| Artwork | List 194/195 `image_url` | No | One missing; URL not a downloaded asset | Nullable `artwork_url` |
| Public state | List `status`, `is_hidden`; detail `is_published` | No | Reflects fetched source, not future removals | `remote_status`, `is_hidden`; separate observation state |
| Updated time | List 195/195 `updated_at` | No | Useful hint; not proof every content change updates it | `source_updated_at` |
| Feed GUID | List 195/195 `guid` | No | Useful secondary identity; differs from episode UUID | `rss_guid` |
| Explicit flag/keywords | Detail sample fields | No | Preserve raw; semantics/coverage require later ingest | Optional normalized fields after validation |
| Transcript timing/labels | Inline in detail HTML | Existing browser writes visible text | Mixed; no structured speaker/segment field verified | Derived segments with uncertainty, tied to source hash |

Do not retain management/action links, tokens, dashboard links, or analytics in catalogue exports. Public source responses contain fields not necessary for a client library. An allowlisted evidence snapshot preserves relevant content fields unchanged without distributing incidental operational fields.

## 5. Episode identity strategy

Canonical machine key: **`simplecast:<id>`**, e.g. `simplecast:254fc97f-8c85-4d1a-bc84-0e230ec99cb5`. Store provider, remote ID and podcast ID separately too. Validate that every item belongs to this podcast.

`episode_number` is the human-facing editorial identifier; number, season, title, slug and URL may change without changing machine identity. Use the UUID as the stable storage filename. Retain prior slug/URL/number aliases when changes are observed, rather than renaming existing source directories. Keep RSS GUID as an alternate source identifier, not an unverified interchangeable UUID.

No guest name or filename determines membership. Repeated guests attach to multiple episode IDs. Multi-guest episodes get multiple participant entries only when evidence supports the separation. Initially each participant entry can contain `name`, `role` (host/guest/unknown), `source_id`, source location and `review_status`. A global people database is optional later. Raw transcript speaker strings are separate from canonical participant names; ambiguous “Gopi” remains the source label until a reviewed mapping is attached.

Existing enrichment joins: unique matching source URL/slug plus compatible episode number; conflicting or multiple matches go to an unresolved crosswalk. Number alone can be a candidate join but should not silently override a conflicting URL. Do not assign a remote UUID to provisional 196 or expose it as published until official discovery confirms it.

## 6. Proposed canonical catalogue

Use small JSON files/JSONL, not a new database service. The canonical **application view** is derived from source snapshots; editable editorial corrections live in an explicitly separate overlay, never in generated exports.

Proposed additive layout (none created):

```text
archive/
  catalogue.jsonl                 # normalized records, stable order by episode_id
  manifest.json                   # source entries, current-version pointers, availability
  links.json                      # reviewed legacy/enrichment/production crosswalk
  sources/<remote-id>/<kind>/<sha256>.json|html|txt
  derived/text/<remote-id>/<source-hash>.txt
  derived/segments/<remote-id>/<source-hash>.json
  exports/catalogue.csv
  exports/episodes/<remote-id>.md
  reports/latest.json
```

Proposed record below combines verified field names with illustrative control values. Angle-bracket values are schema placeholders, not saved evidence:

```json
{
  "schema_version": 1,
  "episode_id": "simplecast:254fc97f-8c85-4d1a-bc84-0e230ec99cb5",
  "provider": "simplecast",
  "remote_id": "254fc97f-8c85-4d1a-bc84-0e230ec99cb5",
  "podcast_id": "8a5f01b8-f271-4de0-b289-c224dc4fce0a",
  "episode_number": 195,
  "number_origin": "api:number",
  "official_title": "Show Proof of Value Before You Build for Scale",
  "published_at": "2026-09-22T04:00:00-07:00",
  "duration_seconds": 2262,
  "slug": "tsse195-show-proof-of-value-rohini-chakravarthy",
  "episode_url": "https://podcast.sure.ventures/episodes/tsse195-show-proof-of-value-rohini-chakravarthy",
  "episode_url_origin": "site_slug",
  "audio_url": "<exact enclosure_url>",
  "episode_type": "full",
  "media_mime_type": "audio/mpeg",
  "season_number": 1,
  "summary": "<exact description string>",
  "artwork_url": "<source image_url or null>",
  "rss_guid": "ec922e8b-1851-416c-9841-f87a291e608b",
  "remote_status": "published",
  "is_hidden": false,
  "public_presence": "present",
  "source_updated_at": "2026-09-22T01:11:37-07:00",
  "metadata_source_id": "<manifest source ID>",
  "participants": [],
  "record_revision": "<hash of normalized content and source references>"
}
```

Empty participants means not yet resolved, not no speakers. Unknown scalar values use null, not invented defaults or empty strings. `public_presence` is our observation, separate from remote status. The default published view selects present public episodes from the last complete snapshot; retained missing episodes remain accessible as historical records with their status clearly identified.

Avoid per-record `last_synced_at` churn: latest successful check belongs to the run report; content acquisition/change timestamps belong to the source manifest. A consumer can join these if it needs a last-checked display. A source-stable rerun should leave catalogue/exports byte-identical.

## 7. Proposed source manifest

Keep detailed availability outside catalogue records; derive convenient `has_*` export columns from it. A boolean alone cannot distinguish unknown, pending, failed and absent.

Each episode has entries for metadata, summary, show notes, transcript, structured transcript, intelligence, newsletter and social/production material. Source entries use a small shared envelope:

```json
{
  "source_id": "<episode-id>:transcript",
  "episode_id": "<episode-id>",
  "kind": "transcript",
  "layer": "official_source",
  "provider": "simplecast",
  "source_url": "https://api.simplecast.com/episodes/<remote-id>",
  "source_field": "/transcription",
  "web_url": "https://podcast.sure.ventures/episodes/<slug>/transcript",
  "availability": "available",
  "current_version": {
    "sha256": "<hash of exact UTF-8 field bytes>",
    "path": "sources/<remote-id>/transcript/<hash>.html",
    "media_type": "text/html; charset=utf-8",
    "retrieved_at": "<UTC timestamp>",
    "validation": "accepted_source",
    "validation_method": "<versioned validator>"
  },
  "derived_text": {
    "path": "derived/text/<remote-id>/<hash>.txt",
    "sha256": "<text hash>",
    "extractor_version": "<version>"
  },
  "timestamps": {"state": "present", "coverage": "partial"},
  "speaker_labels": {"state": "present", "accuracy": "unverified"}
}
```

Availability enum: `not_checked`, `pending`, `available`, `unavailable_at_source`, `failed`, `quarantined`. Track latest attempt result separately from current accepted content: a timeout must not demote an existing valid transcript to missing. `unavailable_at_source` requires a successful detail response with explicitly absent/empty content, not a connection failure. Derived segment status is separate from raw transcript availability. Link intelligence/newsletter/production entries only after crosswalk validation, preserving original paths/hashes and source type.

For metadata provenance, a record-level snapshot plus fixed field-mapping version is sufficient; participant claims and exceptional mappings need field-specific source locations. Do not build a general event-sourcing system.

## 8. Proposed Markdown episode format

**Choose B: reproducible export.** Source snapshots and normalized records are authoritative; Markdown is a read-only deliverable regenerated from them. This prevents two editable copies drifting and allows client delivery independent of any UI.

Filename: remote UUID `.md`; front matter carries the human number/title. Export one document for every published member, even metadata-only episodes. Use UTF-8, deterministic quoting/ordering and LF wrapper lines.

````markdown
---
schema_version: 1
episode_id: "simplecast:<uuid>"
episode_number: 195
title: "<official title>"
published_at: "<source timestamp>"
duration_seconds: 2262
url: "<episode permalink>"
episode_type: "full"
media_mime_type: "audio/mpeg"
speakers: []
speaker_status: "unverified"
show_notes_status: "available"
transcript_status: "available"
metadata_revision: "<hash>"
show_notes_revision: "<hash>"
transcript_revision: "<hash>"
exporter_version: "1"
---

# <Official title>

## Episode metadata

Source URLs and source acquisition dates; identities, duration and content states.

## Published summary

<Exact source summary in a literal block if needed to prevent Markdown reinterpretation>

## Published show notes — preserved source HTML

```html
<exact long_description string, without rewriting>
```

## Transcript — source-preserving text projection

```text
<deterministically decoded source text, with labels and timestamp strings retained>
```

## Source references and editorial attachments

Source files/hashes, extraction method, uncertainty and separately labeled links.
````

Rules:

- Full notes' exact HTML string is preserved in a literal fence in the single-file export; choose a fence longer than any embedded fence. A later optional readable Markdown conversion must be labeled a conversion. Do not equate format conversion with byte-for-byte verbatim HTML.
- Raw transcript HTML remains in source storage and is linked by hash. HTML-to-text projection decodes entities and represents block/line breaks through a versioned deterministic rule; it preserves words, punctuation, timestamp strings and labels, but is **not byte-identical to HTML**. Include the raw HTML as an additional literal section if a client requires self-contained exact source markup.
- If the input is already accepted UTF-8 plain text (legacy or client-supplied), embed its text exactly inside a sufficiently long literal fence; do not trim, fix spelling or normalize internal whitespace. Preserve original bytes separately, including original line endings; document any export newline representation.
- A strict “verbatim transcript” delivery claim must identify the source representation. Never call an edited/cleaned transcript verbatim. Offer source HTML alongside text projections for independently verifiable delivery.
- Missing sections state the actual availability, e.g. “Transcript not yet checked,” rather than implying “no transcript exists.” Empty notes must not silently become the summary.
- Speaker lists and accuracy claims are conditional on evidence. No automatic spell correction or inferred speaker reassignment in source text. Themes/lessons and production assets are linked under editorial attachments, never inserted into transcript paragraphs.
- Dynamic run timestamps are omitted from content-stable episode exports; latest sync status is a separate report. Each source's acquisition timestamp changes only with a new stored version.

## 9. Proposed CSV export

Generate from catalogue + manifest + reviewed participant crosswalk. Recommended columns:

```text
episode_id,remote_id,rss_guid,episode_number,season_number,title,
published_at,date,duration_seconds,duration_display,url,audio_url,
episode_type,media_mime_type,speakers_json,speaker_status,guest_names_json,
summary,artwork_url,public_presence,source_updated_at,
show_notes_status,transcript_status,structured_transcript_status,
transcript_available,show_notes_available,timestamps_available,
speaker_labels_available,intelligence_available,newsletter_content_available,
social_content_available,markdown_path,metadata_revision
```

`title` maps to official title; `date` is the source publication date with its offset semantics documented. Seconds are authoritative; display duration is derived `HH:MM:SS`. Avoid a vague `format` column: use source episode type separately from MIME format. `speakers_json` and `guest_names_json` are JSON arrays inside correctly quoted CSV cells; absence remains an empty array plus status. Sources do not currently guarantee guests/speakers for every row.

Use standard CSV quoting for commas, quotes and embedded newlines. Availability booleans are true only for accepted linked content, false otherwise; status columns retain the distinction between not checked and absent. For spreadsheet delivery, offer a separately labeled formula-safe export if necessary, without changing canonical strings. Do not place full transcript text in the catalogue CSV. Relative paths and stable IDs let a client join the CSV to Markdown and source packages.

## 10. Transcript-ingestion assessment

### What the investigation establishes

The detail endpoint makes direct API ingestion technically plausible for the entire public catalogue, but **archive-wide transcript coverage is not yet proven**. Sampling shows:

| Episode | Detail transcription HTML | Bracketed timestamps | Significance |
|---:|---:|---:|---|
| 1 | 2,546 characters | 1 | Intro is 195 seconds, single-host; the old >10 KB/two-speaker validation would wrongly reject it |
| 2 | 32,022 characters | 25 | Remote source exists despite missing local text |
| 75 | 28,016 characters | 0 | Untimed official transcript is still useful |
| 191 | 45,536 characters | 183 | Formatting includes bold speaker labels |
| 195 | 40,368 characters | 169 | Recent timestamped source with plain speaker labels |

Counts measure source HTML characters and literal timestamp occurrences, not unique timed turns or audio alignment. Official hosted transcript origin is established; whether TSSE generated each transcript with a machine, who edited it, and whether speaker labels are accurate against audio **cannot be established from these fields**. Simplecast supports author-supplied/edited transcripts, so hosting does not prove machine generation. See [Simplecast's transcript feature description](https://blog.simplecast.com/simplecast-hosts-podcast-transcripts?hs_amp=true).

No sampled episode lacks remote transcription. The remaining 190 detail responses were not fetched; record their remote transcript coverage as unknown. Legacy timeout and shell artifacts are retrieval failures, not proof of source absence. The earlier investigation document's broad “not available through public APIs” claim is superseded by these successful public detail responses.

### Existing retrieval components

- `transcript_ingestion.py`: urllib fetch of `/episodes/<slug>/transcript`; historically stores an SPA shell. Do not use shell size/extension as transcript evidence.
- `playwright_transcript_retrieval.mjs`: episode-73-specific selectors/required speakers.
- `phase2_transcript_retrieval.mjs`: fixed historical target list.
- `phase3_transcript_retrieval.mjs`: rank-4 selection by default, skipping episodes with existing intelligence unless overridden; single URL mode requires an episode number. These membership/skip rules are wrong for archive ingestion.
- Browser extraction takes all `<p>` elements' `innerText`, trims/filter blanks, slices around metadata/speaker/footer heuristics and joins paragraphs. It is not byte-verbatim HTML preservation and can miss introductory content or mishandle layouts.
- `newsletter_production_pipeline_v1.py` wraps browser retrieval with a Codex-cache Playwright path and strict speaker/length validation; it also generates intelligence and drafts. Do not invoke it as the archive synchronizer.

### Proposed retrieval policy

Primary: public detail API by remote ID; preserve `transcription` exactly. Secondary: portable browser adapter only when API content is absent or incompatible and the public transcript page visibly contains material. Preserve browser raw content/extraction evidence and label the method, rather than pretending it is the same representation as the API field.

New adapter must accept canonical remote IDs without requiring episode numbers, target every public member independently of rank/intelligence, use relative configured paths and pinned dependencies, and avoid local Codex runtime paths. API-only catalogue/details need no browser installation. Browser fallback later needs a reproducible Playwright/browser setup, explicit output staging, isolated configuration and no automatic software installation during sync.

Validation should detect HTML shells/error pages and malformed payloads, but accept short/single-speaker and untimed sources. Separate source acceptance from parsing quality and editorial verification. Preserve incomplete labels and out-of-order/duplicate timestamp diagnostics. Structured segments are derived sidecars with character spans into a hashed text projection plus source HTML block references. No forced transcript cleanup, speech recognition or invented timestamps.

## 11. Weekly synchronization design

Frequency: **once per week**, not daily polling. Initial backfill is a separately approved operation. Manual rerun is available for recovery.

1. Acquire a single-run lock; read the last accepted catalogue/manifest and configuration.
2. Fetch all public list pages into temporary staging. Validate IDs, podcast scope, pagination completion and field types. A failed/inconsistent list cannot replace current membership.
3. Reconcile by remote UUID. Add new members immediately in staged catalogue with pending detail/source states; update changed official metadata. Never let transcript availability or ranking filter membership.
4. Queue details for new episodes, changed metadata/update stamps, missing/failed sources, and a bounded refresh cohort. For steady state, recheck at least 20 otherwise-unchanged detail records weekly, oldest check first, to detect content edits not reflected in list timestamps (about ten weeks to sweep 195). This is proposed policy, not a measured API guarantee; it runs inside the one weekly job.
5. Retrieve sequentially with bounded retries. Save source fields by content hash only on change. Extract show notes/transcript representations, validate, and create derived text/segments when possible. If time budget is exhausted, retain pending work for the following run.
6. Resolve approved legacy/enrichment links without modifying original files. Rebuild changed Markdown/CSV artifacts and coverage report; a future search index rebuild reads the same accepted snapshot.
7. Validate cross-file references and export reproducibility. Promote the whole staged revision atomically; if export validation fails, keep the previous published revision. Preserve successful source candidates for safe retry if desired, without exposing mixed manifests.
8. Persist changed data and report outcomes. Failure reporting distinguishes catalogue failure from isolated content failures; the latter do not discard successful catalogue additions.

### Required behavior by case

| Case | Behavior |
|---|---|
| New episode | New UUID-keyed record even if no number/guest/notes/transcript; save metadata, queue details, expose explicit pending/failed states |
| Metadata edit | Refresh official fields and URL aliases, retain prior source version; no automatic overwrite of editorial intelligence |
| Notes/transcript edit | Store new hash/version and regenerate dependent projections/exports; old citations remain pinned to old hash; flag editorial quotes based on older versions |
| Not seen remotely | Only after a complete list, record absence observation; retain previous source/status separately. Exclude from current-public view while keeping historical record; do not label deleted/private without evidence |
| Reappears | Same UUID regains present state, no duplicate or new human identity |
| Transcript timeout | Keep episode; retain any accepted previous content, mark latest attempt failed; retry boundedly/next weekly run |
| Successful empty transcript | Record unavailable-at-source for current remote version; retain previous transcript historically and distinguish stale/local availability from current remote availability |
| One detail fails | Commit other valid catalogue/content updates; report that episode's error |
| List/page fails | Keep last accepted membership and denominators; mark report incomplete/stale; no inferred removals |
| Rerun without change | Stable IDs, hashes and exporter versions produce identical catalogue/content/exports; only operational check report may differ |

A complete fetch with an unexpectedly large loss of IDs should be quarantined for review before changing the default public view. Absence is evidence of non-observation, not deletion. Weekly checks do not promise immediate appearance at publication time.

## 12. Change/provenance strategy

Minimum useful provenance: provider + remote ID, retrieval URL/field, acquisition timestamp, content hash, relative local path, media type, retrieval method/status, validator version/result. Derived artifacts additionally record input hashes and extractor/exporter version. Legacy sources record original file path/hash and known URL; unknown acquisition dates remain unknown.

Preserve exact UTF-8 content-field bytes after JSON decoding; retain an allowlisted JSON evidence snapshot and a hash of the complete response bytes for diagnostic comparison. If raw full responses are ever retained, keep them outside portable public exports and apply a reviewed retention policy. Do not copy operational tokens into reports. Byte hashing alone cannot distinguish JSON-key ordering or dynamic counters from meaningful change: compute a separate canonical content hash over relevant fields, excluding counters such as `days_since_release`, request links and check timestamps. Changing acquisition metadata must not create a new content revision.

On real change, retain the prior accepted source blob; a current pointer identifies the active version. Small per-source versions plus Git history suffice; no event bus or event-sourcing framework. Use run reports for `last_attempt_at`/`last_successful_check_at`, not per-episode export churn. A monthly/weekly report can explain new, changed, unavailable, quarantined and stale sources.

Offsets: define them as zero-based Unicode code-point indices with exclusive end into the **specified UTF-8-decoded text projection**, never ambiguous JavaScript UTF-16 indices. Store projection hash and extractor version, and verify `text[start:end] == excerpt`. HTML source reference can include field JSON pointer and parsed block index tied to its hash; transformed text offsets must not be described as raw-HTML byte offsets. Audio timestamps and inferred speaker carry-forward are optional derived annotations with method/confidence, not source edits.

## 13. Coverage reporting

Denominator `N`: unique public published IDs from the last accepted complete official snapshot. Store its observation time. On list failure, continue displaying last-known counts with `catalogue_sync_complete=false`; never show a partial page as the full archive.

Numerators count distinct episode IDs, not files, transcript variants or keyword matches:

- Metadata normalized: accepted catalogue records / N.
- Summary available: nonempty accepted `description` / N.
- Full show notes retained: accepted nonempty `long_description` / N; separate from summary.
- Transcript retained: accepted current source/text mapped to published member / N; optionally show legacy-local vs freshly fetched and stale-version subtotals.
- Structured transcripts: accepted segment projections / N.
- Timestamped transcripts: recognized source timing markers / N, plus `/ transcripts retained`; timing presence is not complete alignment.
- Speaker-labeled transcripts: recognized labels / N; separately report verified participant mappings. Never call labels “accurate” just because a regex matched.
- Intelligence/newsletter/social: accepted reviewed links to each layer / N; suggestions/drafts are not published content.
- Run counts: newly discovered IDs, materially changed records/sources, no longer observed IDs, failed requests, successful empty sources, pending/quarantined items, reused legacy sources and export failures.

**Investigation baseline, not an implemented sync report:**

| Measure | Evidence |
|---|---:|
| Official public episodes | 195 |
| List metadata and short summaries returned | 195/195 (100%) |
| Existing local main transcripts joined by remote slug | 56/195 (28.7%) |
| Existing strict-validator accepted local transcripts | 47/195 (24.1%); nine format false negatives |
| Existing timestamped main transcripts | 33/195 (16.9%); 33/56 (58.9%) of local texts |
| Existing intelligence records | 57/195 (29.2%), pending formal UUID crosswalk |
| Full notes/transcripts in detail sample | 5/5 sampled; whole-archive remote coverage unknown |
| Canonical catalogue/export/index generated | None; this is a design task |

Do not add the five temporary samples to local coverage or count provisional 196 in N. Newsletter/social coverage requires reviewed identity/role mapping; the audit's raw nonempty CSV counts are not valid relationship-coverage numerators.

## 14. Search-readiness assessment

A full-catalogue lexical search can cover title, number, exact published summary and later full notes for every member with those fields. Guest/speaker search has explicitly partial evidence; `authors` is not a reliable shortcut. Metadata-only episodes must appear in results even without transcripts.

Text projections allow later lexical indexing by episode ID, source ID, source version, passage start/end, optional source timestamp and speaker label. A result can show the exact excerpt, jump to local context, and link to the official page. Episode 195's notes contain verified public `?t=...` links; retain those literal links. Do not assume all transcript timestamps have a valid player deep link or accurate audio alignment without checking.

For unparsed/untimed text return paragraph/context references without fabricating times. For ambiguous speaker labels display the raw label or “speaker unresolved.” Newsletter text needs section boundaries and reviewed links before claiming an episode association. Source HTML is inert storage; any future web renderer must sanitize HTML for display without rewriting preserved source files.

No search service, vector index, embeddings, semantic ranking or generated answers are needed to establish this library. The initial schema should merely preserve the evidence a later lexical index needs.

## 15. Relationship to existing editorial intelligence

Three separate layers:

| Layer | Contents | Membership/authority |
|---|---|---|
| Official/source | Public catalogue metadata, summary, notes, transcript; labels/times as supplied | Official public list determines published membership; source text preserved |
| Editorial intelligence | Rank4/active JSON, themes, industries, lessons, quote selections, CI/startup scores | Attach by reviewed crosswalk; source-derived interpretations, not replacements for official titles/notes |
| Production | Newsletter drafts, social/quote-card jobs, rendered assets | Attach by provenance and production state; generated does not mean published |

The source layer may have derived parsers but remains separate from editorial interpretation. A parsed speaker label is a technical annotation; a corrected participant identity is a reviewed claim. Existing rank4/active files stay unchanged. `links.json` can map a legacy path/hash to a remote ID with match evidence/status. Do not rerun newsletter generation during sync or implicitly refresh curated themes when a transcript changes. Mark attachments potentially stale and let editorial workflows decide.

## 16. Scheduling/deployment recommendation

**Primary recommendation: GitHub Actions weekly scheduled workflow plus manual dispatch, after local implementation is proven.** The repository already has a GitHub remote; no existing scheduler/deployment configuration was found. Proposed time: Monday 06:17 UTC / 09:17 Africa/Nairobi, avoiding the top of the hour. No workflow or recurring automation was configured.

Use a pinned Python runtime, pinned actions/dependencies and API retrieval first. Restrict network/configuration to approved public sources. No Simplecast secret is needed for observed access; do not add one speculatively. Give the automation only the repository permissions necessary for the approved persistence path.

Persistence recommendation: commit content-addressed sources, catalogue, manifests and text exports to a dedicated generated-data branch after validation; keep human editorial source files and application code on their existing branch. Read that data branch at run start. Commit only material changes, not a timestamp-only no-op. Use workflow artifacts/run summaries for per-run diagnostics; they are useful for inspection but are not durable canonical storage. A consumer checks out the data branch explicitly. If branch protection requires PRs, use a reviewed PR path rather than bypassing protection; select this policy at scheduling approval.

Use one concurrency group and atomic commit promotion; no force pushes or overlapping writers. Failed catalogue runs and partial content failures need visible run summaries/artifacts and configured failure notifications. A successful run with warnings must still list affected episode IDs. Monitor the last successful snapshot age; Actions scheduling is not an exact-time SLA.

GitHub documents default-branch execution, possible schedule delays/dropped queued jobs, and automatic disabling after 60 inactive days in public repositories. These are reasons for a manual rerun path and explicit stale-data visibility. See [schedule behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) and [workflow notifications](https://docs.github.com/en/actions/concepts/workflows-and-actions/notifications-for-workflow-runs).

| Option | Assessment |
|---|---|
| GitHub Actions | Fits existing repository, reproducible runner and visible logs; needs explicit data persistence/write policy and awareness of scheduling limits |
| Deployment-platform cron | Reasonable if a hosting platform and durable storage already exist; neither is established here, so it adds infrastructure now |
| Local cron/launchd | Simple technically, but depends on this machine being awake/configured and creates portability/visibility problems |

Do not promise zero cost: runner/artifact allowances depend on repository/account plan; API-only weekly work is small but cost and policy should be checked when scheduling is authorized. Keep audio, models and portrait outputs out of the data branch. Revisit object storage only if measured corpus/version growth warrants it.

## 17. Portfolio demonstration opportunities

Once implemented and validated, the system could honestly demonstrate:

- A complete official catalogue count independent of selected enriched episodes.
- A CSV deliverable with normalized dates/durations, stable identities and explicit missing fields.
- One standardized Markdown document per published episode, including metadata-only records.
- Side-by-side original source HTML and derived text with labels/timestamps preserved and conversion explained.
- Exact passage references anchored to source hashes, with changed-source detection.
- Coverage improving through approved ingestion, with measured counts rather than invented targets.
- A real weekly run discovering a newly published episode, retaining it when content retrieval fails and succeeding on a later retry.
- Layered editorial reuse without presenting a generated interpretation as a source quote.

These demonstrate podcast archive organization, repeatable export, metadata normalization, transcript organization and provenance-aware knowledge-library engineering. Search results can be demonstrated only after search is built; a weekly “automatic addition” demonstration requires an actual scheduled run and published source change. No claims of verified speaker accuracy, machine-generated transcript origin or time savings are supported yet.

## 18. Risks and unresolved questions

1. **Remote full-note/transcript completeness:** five successful samples are promising, not proof of 195/195. Approve catalogue/detail backfill separately.
2. **API stability/access policy:** public access is observed, general management API docs describe credentials. Keep failure handling and a browser adapter; do not assume undocumented public field contracts never change.
3. **Guest/speaker truth:** contributor lists include entities, and transcripts may contain shortened or incorrect labels. Confirm who reviews participant mappings if accurate speaker attribution is a client deliverable.
4. **Source fidelity:** agree on source HTML + deterministic text projection as the delivery contract. “Verbatim” must specify the representation; HTML conversion cannot be described as byte-identical text.
5. **Published membership:** recommend all public source types, including introductory/bonus/trailer items when listed. Current type is `full` for every item; do not editorially exclude episode 1.
6. **Provisional 196:** excluded from published membership today; existing local materials remain untouched and may remain separate provisional attachments.
7. **Change detection:** update timestamps are hints. Approve the bounded refresh cohort and last-checked visibility rather than assuming undetected remote edits are impossible.
8. **Disappearance policy:** retain previous data, record non-observation, quarantine suspicious mass disappearance; no automatic deletion or unjustified private/draft classification.
9. **Storage/scheduling approval:** confirm dedicated generated-data branch permissions and repository access before configuring automation. No uploads/commits/pushes performed here.
10. **Source snapshots vs repository size:** measure actual text volume during approved ingestion; avoid audio/media downloads and unnecessary identical versions.

## 19. Proposed implementation sequence

1. **Approve this design and delivery fidelity policy.** Especially official UUID identity, full published membership, generated Markdown/CSV, partial-content states and additive source storage.
2. **Implement catalogue-only synchronization first.** Read all public pages, validate full snapshot, retain allowlisted metadata, build canonical records/manifest and a coverage report in an additive location. Test malformed pagination, duplicates, missing numbers, status disappearance and no-op reruns. Keep all current scripts/data untouched.
3. **Implement a small detail-ingestion pilot and exports.** Use the five investigated shapes: short intro, early formatted transcript, untimed transcript and modern timestamped records. Preserve HTML/fields, deterministic text, source hashes and Markdown/CSV. Verify no-op exports, changed source versions, Unicode offsets, speaker uncertainty and partial failure.
4. **Seek separate approval for full detail/transcript backfill.** Enumerate the official catalogue; ingest incrementally and report actual notes/transcript availability. Reconcile legacy files without rewriting them.
5. **Add reviewed editorial/source crosswalks and acceptance checks.** All published IDs have documents; missing content is explicit; exact passages resolve; stale sources and provisional attachments remain distinguishable.
6. **Configure the weekly runner only after its persistence/permissions are approved.** Demonstrate manual success, failure reporting and idempotence before enabling the schedule.
7. **Then build lexical search and, in a subsequent approved task, the frontend.** Neither is implemented now. Do not add vectors, LLM enrichment, ASR, guest-identity guessing, newsletter regeneration or automatic publishing to this foundation task.

### Investigation record

Repository audit and relevant discovery/retrieval implementations were read. Public API calls used existing credential-free discovery helpers and standard-library HTTP; the initial sandbox DNS attempt failed, then authorized read-only network execution succeeded. Temporary response files were saved only under `/tmp` for analysis; no raw API payloads or secrets were added to the repository. Full metadata was enumerated, pagination rechecked, and five detail responses inspected. Browser inspection of the official episode 195 page corroborated summary vs notes and player duration. API action links were never invoked. No dependency installation, bulk retrieval, scheduler setup, source correction or implementation occurred.
