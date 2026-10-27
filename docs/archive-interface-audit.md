# TSSE archive interface audit

Audit date: 26 October 2026. Scope: the current local checkout, including untracked and ignored content actually present on this machine. This is discovery only; no interface, ingestion, schema change, dependency installation, or source-data correction was performed. The only intended repository addition is this report.

## 1. Executive summary

TSSE already has a useful editorial corpus and executable production tools, but not a unified archive application dataset. The strongest foundation is the guest-ranking export for episode identity, existing transcript text for search, and episode JSON for optional editorial enrichment. Newsletter prose and publishing provenance add valuable material outside that core.

- **178 valid episode rows** (episodes 2–179) in the rankings export, with names and URLs. Its 179th parsed row is a summary/footer, not an episode.
- **57 enriched episode records:** all 54 Rank 4 entries plus active episodes 190, 191, and 192. These are a selected subset, not the full archive.
- **56 main transcript text files**, covering 53 of those 54 Rank 4 episodes and all three active episodes. Episode 2 has only an HTML shell locally. An additional supplied transcript for provisional episode 196 exists in ignored publishing inputs.
- **190 distinct episode numbers directly evidenced across the principal data sources**, rising to **191 when provisional publishing episode 196 is included**. This is a locally evidenced lower bound, not a verified count of published TSSE episodes. The distinction and calculation appear below.
- **45 raw newsletter issues**, **46 CSV history rows**, **14 startup intelligence records**, and **10 generated newsletter packages**.
- A working local quote-card renderer and portrait review lifecycle already exist. They are neither a searchable archive nor evidence of automated social publication.

The principal risks are misleading completeness, stale/conflicting generated outputs, missing passage-level provenance in episode intelligence, and incorrect newsletter joins. Connected Insights v3 matches **zero** current history labels to candidate guests; its recency mechanism exists but receives no usable historical matches. Some `featured_episode` values actually identify the Connected Insights episode instead of the new episode.

**Recommendation:** after review, build a non-destructive derived catalogue, source manifest, and basic text index. Preserve source data and existing editorial tools. A useful first interface can follow once identities, source availability, and search-result citations are validated. Full-archive enrichment, semantic search, and automated editorial decisions are unnecessary prerequisites.

## 2. Current repository architecture

| Layer | Actual implementation | Interpretation |
|---|---|---|
| Editorial documentation | `README.md`, `docs/architecture.md`, `docs/workflows.md`, `docs/data-model.md`, `docs/sources.md`, `docs/roadmap.md` | Mix of intended entities/workflows and implemented capabilities; not an executable schema |
| Episode identity and content | `data/guest_rankings.csv`, `data/episodes/{rank4,active}`, `data/transcripts` | File-based editorial corpus, concentrated on Rank 4 recommendations |
| Newsletter memory | `data/newsletter_archive_sample.txt`, `data/newsletter_history.csv`, importer and history reader | Raw prose plus lossy extraction |
| Startup knowledge | `data/startups/*.json` | Curated/enriched watchlist with evidence and embedded appearance history |
| Retrieval and extraction | `transcript_ingestion.py`, three Playwright `.mjs` retrievers, `episode_discovery.py`, `episode_intelligence_generator.py` | HTTP/browser retrieval, API discovery, deterministic heuristic extraction |
| Recommendation and drafting | Connected Insights v1/v2/v3, `startup_recommender_v1.py`, `newsletter_briefing_generator_v1.py`, `newsletter_production_pipeline_v1.py` | Local Python functions/CLIs; token/rule scoring and template drafting |
| Publishing | `publishing/`, `schemas/publishing/quote-card.schema.json`, `tests/publishing/` | Separate image renderer, portrait processing, provenance and approval tools |
| Generated evidence | `outputs/`, validation/evaluation documents in `docs/`, root discovery report | Historical runs and review artifacts; not a canonical merged database |

No archive frontend, archive API, database, full-text index, embedding store, or application package manifest was found. HTML files under generated quote-card outputs are review previews, not an archive application. Python is used for editorial logic; Node/Playwright scripts retrieve rendered transcripts. The publishing runtime has its own dependencies and an existing `.venv-portraits` environment.

### Documentation/implementation discrepancies

1. `docs/data-model.md` describes publication dates, inline transcript text, profile URLs, and relational entities. The 57 episode JSON files are flat enrichment records and contain none of those date/profile/transcript fields.
2. `docs/architecture.md` calls for three intro alternatives and community mission/milestone research. The production renderer emits one templated intro and community placeholders; no automated organization research is demonstrated there.
3. `docs/workflows.md` and `docs/roadmap.md` describe some recommendations and drafting as future work, although executable versions and saved runs now exist. Conversely, startup news monitoring and complete editorial automation remain aspirations.
4. `docs/newsletter-history-validation.md` reports 45 rows and no missing Connected Insights labels. Current CSV has 46 rows, including issue 77 with a blank label.
5. `docs/episode-intelligence-phase3.md` correctly reports 54 populated Rank 4 JSON files; this does not prove 54 usable local transcripts. Episode 2's retained HTML is a shell.
6. README describes the archive importer as updating history. Its `main()` parses the raw input and `write_csv()` opens the destination in write mode: it replaces the CSV rather than merging. Rerunning could drop issue 77, absent from the supplied raw archive.
7. Historical validation documents describe earlier snapshots. For example, old shell-retrieval failures coexist with repaired `.txt` files, and earlier episode 190 outputs coexist with later corrected versions. Reports should be read as dated evidence, not current state.

## 3. Data inventory

Counts exclude caches and the dependency environment. Generated review variants are counted as files, never as distinct episodes or posts.

| Location | Format/count | Purpose, source and stage | Completeness; producers/consumers |
|---|---|---|---|
| `data/guest_rankings.csv` | **Tab-delimited** despite `.csv`; 179 parsed rows, 178 episode rows | Export of Gopi's Google Sheet documented in `docs/sources.md`; episode/name/URL/rank identity source | Episodes 2–179 only; 54 rank 4, 124 rank 1, one blank-ID footer with rank `54`. Consumed by transcript ingestion and historical selection; current v3 relies on the rank4 directory instead of live sheet validation |
| `data/episodes/rank4/` | 54 JSON | Normalized structure, curated/enriched editorial interpretation; source claimed as official transcripts | Complete for the 54 rank-4 export entries, partial for archive. Used by recommenders/briefing/pipeline; phase documentation and `phase2_processor.py` record historical preparation |
| `data/episodes/active/` | 3 JSON | Draft intelligence for 190–192 | `episode_intelligence_generator.py`/pipeline produce; pipeline consumes. No rank stored, appropriately separate from recommendation eligibility |
| `data/episodes/episode_template.json` | 1 JSON | Schema-like empty example | Not an episode and not a formal JSON Schema validator |
| `data/transcripts/*.txt` | 56 text files, 21,235–58,731 bytes | Retrieved/rendered source content | 53 Rank 4 + 3 active; retrieval scripts/pipeline write, extraction and publishing consume |
| `data/transcripts/*.html` | 16 files, each 3,281 bytes | Raw failed HTTP retrieval artifacts | All have the same SHA-256 and are SPA shells, not 16 extra transcripts. See `TRANSCRIPT_INVESTIGATION_SUMMARY.txt` and retrieval reports |
| `data/newsletter_archive_sample.txt` | 1 text file; 198,029 bytes; 45 issue headings | Raw supplied newsletter prose, issues 31–75; intros, podcast entries, CI, startup/community sections, occasional event references | Partial historical archive; not canonical website show notes. Consumed by `newsletter_archive_importer.py` |
| `data/newsletter_history.csv` | CSV; 46 unique issue rows | Parsed/partly normalized memory, issues 31–75 plus 77 | Incomplete and semantically inconsistent. Used by history reader, discovery, briefing, and recommenders |
| `data/startups/` | 14 JSON | Watchlist from source registry/Google Doc; official-site/manual enrichment and normalized newsletter appearances | All have identity, themes, industries and source lists; sparse founders/news/relationships. Consumed by startup recommender and newsletter generators; no standalone general startup refresh/normalization pipeline found |
| `discovery_report.json` | 1 JSON | Generated official Simplecast API discovery snapshot | Newest episode in this root snapshot is 191; stores selected coverage tail, not full API catalogue. `episode_discovery.py` produces; pipeline can embed/use discovery |
| `outputs/newsletter_production/` | 10 packages, 35 files: 10 JSON briefings, 20 Markdown files, 5 discovery reports | Generated drafts, recommendations, retrieval/validation metadata | Five distinct package episode identities: 75, 179, 190, 191, 192 (including a broken old 190 output). Multiple runs per episode; not published issues. Pipeline produces |
| `docs/` | Before this report: 60 Markdown + 1 JSON | Architecture, data summaries, phase/theme analyses, repairs, evaluations, validation and publishing evidence | Historical snapshots; `docs/connected_insights_validation_raw.json` is evaluation data, not archive content. Some generated by old scripts, others editorial documentation |
| `TRANSCRIPT_INVESTIGATION_SUMMARY.txt` | 1 text report | Retrieval investigation | Historical diagnostic; useful context, not transcript corpus |
| `data/publishing/local/` | **Ignored**, 37 files: 24 JSON, 9 images, 2 text, 1 DOCX, 1 ONNX | Local quote jobs, source receipts, portraits, provisional episode 196 record/transcript and model | Two guest example families (Patrick Eggen/Pavel Prata); includes 10 top-level quote-job variants, two portrait candidate bundles and current selections. `prepare_examples.py`, portrait and asset tools produce; renderer consumes |
| `outputs/quote_cards/` | **Ignored**, 131 files: 64 JSON, 46 PNG, 19 HTML, 2 text | Generated image/review/validation builds | Variants for local publishing review, not 131 content items or published posts. Produced by publishing tools |
| `outputs/portraits/` | **Ignored**, 90 files: 61 PNG, 18 JSON, 10 NumPy arrays, 1 text | Segmentation, alpha mattes, recovered foregrounds, manifests and review evidence | Local experiments/repeat runs and review bundles; no archive-wide guest portrait collection |
| `publishing/templates/quote-card/v1/` | Spec, approval, fonts/provenance/license, 3 images | Versioned approved template, logo and two visual references | Config/assets, not episode records; renderer consumes. `publishing/portraits/{config,model}.json`, dependency files and schema support this subsystem |
| `tests/publishing/` | 3 Python test modules | Quote-card, portrait and asset-lifecycle verification | Existing publishing coverage; no analogous automated archive catalogue/join suite found |

The pre-existing untracked inputs/outputs are `data/episodes/active/episode_192.json`, its transcript, and the episode 190 and 192 production package directories. They are counted above but are not guaranteed to exist in another clone. Ignored publishing assets likewise require an explicit portability decision later.

## 4. Episode archive coverage

### Count definitions

| Evidence level | Distinct episode count | Calculation and limits |
|---|---:|---|
| Ranking identity rows | 178 | Integer IDs 2–179; all have guest and URL; 176 distinct guest-name strings, so names are not episode IDs |
| IDs in structured rankings/history/main episode files/discovery and production JSON | 185 | Ranking IDs plus 186–192. Several are only thin metadata or history references |
| Also explicitly mentioned in raw newsletter prose | **190** | Adds 180, 181, 182, 184, 185. Union is 2–192 excluding 183. This does not establish that 183 is missing from the actual podcast |
| Also provisional publishing input | **191** | Adds 196/Pavel Prata, marked `provisional_from_supplied_reference_filename`, with no episode URL and unverified website correspondence |
| Main enriched records | 57 | 54 Rank 4 + active 190–192; 58 structured episode-shaped objects if the minimal provisional publishing record is included, but it is not enriched |
| Main usable transcript text | 56 | 53/54 Rank 4 + 3 active. Additional local Pavel text/DOCX represents one more provisional episode, not two |
| Main enriched records without matching text | 1 | Episode 2/Gokul Rajaram; HTML shell does not satisfy this requirement |
| Published dates retained in discovery snapshots | 4 episodes | 189–192; no publication dates in the 57 main episode JSON files |

This is a conservative source inventory, not a live crawl or a count of every numeric example in documentation. No remote sources were accessed. Numbers mentioned in narrative sources do not supply all catalogue fields. There is no full official episode catalogue saved locally, so archive completeness against the live podcast remains unverified.

### Content coverage and quality

- All 57 main JSON records parse and have the same 11 core fields; the 54 Rank 4 records additionally carry integer `guest_rank: 4`. Their names and URLs exactly match the corresponding ranking rows.
- Titles are often editorial summaries rather than official titles: episode 179 is `Data-Driven Emerging Manager Investing`, while its source slug says `start-early-stay-consistent`. Episode 191's active title is slug-derived while the discovery snapshot preserves `Have desire to build with unwavering commitment`.
- All 56 main text files contain substantial text. **33 contain bracketed `[HH:MM:SS]` markers**. A loose clock-pattern test finds 34, but the extra is “6:00 AM” in ordinary speech, not a transcript timestamp.
- The pipeline's current `validate_transcript()` accepts **47/56**. Nine early transcripts have concatenated speaker turns and fail the line-start speaker rule despite containing substantial dialogue. These are formatting/validator incompatibilities, not proof of missing conversations. They correspond to episodes 8, 9, 10, 11, 12, 14, 16, 17, and 20.
- No dedicated official show-note/description or chapter collection exists. Raw newsletter podcast entries and generated summaries exist but must retain those labels. Discovery reads descriptions to infer guests, then discards the description field from its normalized output.
- Social-related content exists as quote-card inputs and renders. No normalized archive of captions, channel-specific social posts, publication dates, or post URLs was found.
- Newsletter CSV references contain 18 populated `featured_episode` rows representing 16 IDs; **8 rows join to 6 main enriched episodes**, but a successful ID join does not prove the correct newsletter section.

## 5. Field consistency/readiness

Coverage denominators are the 57 main enriched records unless stated otherwise. “Ready” describes a field's existing usability within its coverage, not full-archive completeness.

| Field | Where stored | Coverage | Consistency/example | Interface readiness |
|---|---|---:|---|---|
| Episode number | Ranking TSV, episode JSON, discovery/history | 178 ranking rows; 57 enriched | Integer JSON vs CSV strings; exclude footer; e.g. 179 | Usable with normalization |
| Episode title | Episode JSON; discovery `episode_title`; newsletter prose | 57 enriched; additional recent snapshot metadata | Editorial vs official vs slug-derived; episode 191 differs | Usable with normalization and source labels |
| Guest name | Rankings, JSON, raw prose | 178 ranking rows / 176 names; 57 enriched names | Some multi-guest strings; spellings/diacritics; episode identity must not collapse by name | Usable with normalization |
| Guest rank | Ranking TSV; rank4 JSON | 178 ranking rows; 54 enriched | All rank4 JSON = 4; active records have no rank | Ready within snapshot; not a browsing eligibility rule |
| Role/company | Transcript/newsletter prose; quote-job `attribution` | 0/57 dedicated fields; two publishing example guests | Patrick: Co-founder and Partner, Counterpart Ventures | Partial; prose search possible, reliable archive filters unavailable |
| Episode URL | Ranking TSV, JSON, recent discovery | 178 ranking rows; 57 enriched | All rank4 URL joins exact; provisional 196 blank | Ready within coverage; no fresh remote availability check |
| Publication date / remote ID | Discovery `published_at`, `simplecast_id` | 4 recent episodes; 0/57 core records | Snapshot metadata for 189–192 | Partial |
| Transcript | Separate slug-named `.txt` | 56/57 enriched; extra provisional 196 locally | No explicit transcript path in main JSON; episode 2 shell only | Usable with manifest and format handling |
| Transcript timestamps/speakers | Inline text | 33/56 bracketed timestamps; speaker formats vary | Concatenated early turns, shortened `Gopi:`/`Ryan:` names | Partial; no structured segments or guaranteed audio seeks |
| Official description/show notes | Not retained as a collection | 0 dedicated normalized records | Newsletter summaries are a different source type | Missing; do not synthesize to fill gap |
| Chapters | No dedicated field/collection | 0 structured | Inline times do not equal chapters | Missing |
| Primary/secondary themes | Episode JSON | 57/57 | 57 distinct primary strings; 213 distinct secondary strings; prose phrases | Usable with normalization; editorial interpretations |
| Industries | Episode JSON | 57/57 | 124 distinct labels; e.g. FinTech vs Financial Technology | Usable with normalization; avoid pretending a controlled taxonomy exists |
| Founder lessons | Episode JSON arrays | 57/57 | Curated advice vs heuristic sentence fragments; episode 192 includes “And eventually, we don't even have to tell the computer what to do.” | Partial for trusted insight reuse; searchable as stored |
| Notable quotes | Episode JSON arrays | 57/57 | No speaker/offset metadata; whitespace/case-normalized substring check matched 156/168 quotes in the 56 available texts | Partial; match is evidence of text presence, not speaker/context verification |
| Community organizations | Episode JSON arrays | 46/57 nonempty | Names only; empty may mean not captured; no universal organization ID | Usable with normalization; partial provenance |
| Companies/people mentioned | Transcript/newsletter prose | No dedicated entity arrays | Startup watchlist is not an index of all mentioned companies | Partial for text search; missing structured relationships |
| Related episodes | Recommendation output JSON | 10 packages / 5 episode identities | Ranked candidates and rationales; repeated/stale runs | Partial; recommendations are not canonical relations |
| Newsletter appearances | CSV and raw archive | 18 numeric references; 45 CI labels | Wrong-section extraction and labels instead of guest IDs | Partial; verify joins before exposing as fact |
| Social assets and quote provenance | Local publishing job JSON | Two episode families, 70 and provisional 196 | Source path/hash, excerpt, offsets, speaker, classification, review status | Partial coverage; strong usable provenance pattern |

The substring quote check did not change text. Nonmatches can reflect punctuation, paraphrase, extraction differences or incorrect quotations; the audit does not label all 12 as fabricated. Episode 2's quotes were excluded because its source text is unavailable locally.

## 6. Search and sourceability assessment

| Search dimension | Existing data and coverage | Normalization needed | Source result can point to |
|---|---|---|---|
| Episode number/URL | 178 ranking rows, 57 enrichments, scattered later metadata | Integer IDs, footer exclusion, URL/slug mapping, conflict policy | Original TSV row, JSON file and official episode URL |
| Title | 57 enrichment titles plus recent metadata and newsletter headings | Distinguish official title, editorial title and section heading | Exact field and originating file; cannot claim all titles are official |
| Guest | 178 ranking rows; 57 enriched | Preserve raw names; multi-guest representation and aliases; don't merge episodes by name | Ranking/JSON record, later source passage if available |
| Company | Prose corpus + 14 startup profiles + two publishing attributions | Separate guest affiliation, mentioned company and startup eligibility | Matched transcript/newsletter passage or startup field/source URL; no reliable global company filter yet |
| Transcript text | 56 main texts + provisional local source | Explicit source mapping, stable offsets, speaker/timestamp parsing where possible | Exact local passage with surrounding context; link to transcript URL; timestamps only if present |
| Themes/industry | 57 enrichment records; startup tags | Case/whitespace/aliases and optional controlled grouping, retaining raw strings | JSON field; most lack direct supporting source spans |
| Founder lessons/quotes | 57 enrichment records | Distinguish curated vs heuristic, verified quote vs paraphrase | JSON record now; exact transcript passage only after a verified text alignment |
| Newsletter appearance | 45 raw issues / 46 CSV rows | Section-aware extraction, explicit issue/episode roles and review state | Raw issue and section excerpt; CSV alone is insufficient proof |
| Community organization | 46 episode arrays; 38 history rows | Aliases such as AchieveKids/Achieve Kids; no-match ≠ absence | Original record/prose, not an automatically researched mission |
| Rank/source availability | Ranking and local files | Derive availability flags independently of eligibility | Source record/manifest; immediately useful filters |
| Related content | CI outputs and newsletter sections | Pin recommendation run and distinguish suggestion from actual use | Score/matched-field rationale; not necessarily a transcript passage |

A basic lexical search can work without generating content. It should return direct text matches and their context, alongside optional metadata matches. A theme match should say it matched stored editorial metadata when no supporting passage exists; it must not imply a transcript citation.

There is no general passage index yet. An additive source manifest can pin relative file paths, source URLs, hashes and content type; derived text chunks can retain offsets into the original text. The quote-card schema and `publishing/quote_card.py` already demonstrate hashes, excerpt equality, offsets, speaker checks and quote classification. Reuse those principles, without forcing every archive document into the publishing schema.

Full-text search is not implemented by the recommenders. CI v3 uses lexical token overlap among stored enrichment fields, not transcript retrieval, embeddings, or semantic understanding. Its transparent matches are useful explanations of scoring, not proof of a claim's source passage.

## 7. Newsletter workflow assessment

### Implemented flow

1. **Supply historical prose → parse history:** `newsletter_archive_importer.py` uses regular expressions and limited guest cleanup; `newsletter_history.py` reads/prints summaries. Manual supply and script-assisted extraction. Current importer is replacement-based and section boundaries are insufficiently reliable.
2. **Select current episode:** explicit transcript URL, or `--latest` in the pipeline invokes `episode_discovery.py`. This discovers the podcast through the official Simplecast API, paginates episodes, normalizes selected metadata and compares to history. Retrieval-based, on-demand automation; no scheduler demonstrated.
3. **Retrieve/reuse transcript:** pipeline uses a cached `.txt` or browser retrieval, then checks size, speaker labels and shell markers. Legacy HTTP retrieval retained shell artifacts; phase2/phase3 browser scripts document repairs. Existing browser-module paths are machine-specific; do not assume a portable clean-clone command.
4. **Obtain intelligence:** reuse active first, then Rank 4 records; otherwise `episode_intelligence_generator.py` scores keyword groups, selects sentences and uses organization heuristics, then saves an active record. This is rule-based extraction, not demonstrated LLM generation. `phase2_processor.py` contains curated dictionaries and hard-coded historical paths; it is not a general intelligence extractor.
5. **Recommend Connected Insights:** production uses v3, with Rank 4 directory as candidate pool, excluding current episode/guest. Theme and lesson token overlap, exact normalized industry/organization overlap, issue-gap recency and frequency contribute to a score. V1/v2 remain historical prototypes, not separate search services.
6. **Recommend Startup Corner:** startup v1 scores themes, lessons, industries, founders, milestones, shared investments and embedded appearances. Verified shared investment is prioritized in sorting. Coterie's episode 191 relationship is the one populated guest-relationship case.
7. **Assemble briefing/draft:** top three recommendations from each engine, source retrieval diagnostics, stored intelligence and score explanations become `briefing.json`, `briefing.md`, and `newsletter_draft.md`. Draft text is templated; it contains URL placeholders and human-edit notes. Recommendation output is not a final editorial selection.
8. **Research/review/publish:** company/news freshness, community missions, event selection, final intro/voice, quote verification and publication remain external/manual. No demonstrated newsletter send/publish or automatic post-publication history update exists.

`newsletter_briefing_generator_v1.py` is an earlier briefing assembly entry point. The larger production pipeline adds retrieval, optional discovery, active intelligence persistence and draft files. The repository demonstrates callable execution and saved outputs, not unattended operations.

### History quality and recommendation consequences

CSV completeness: 46 issue numbers, 18 featured-episode values (16 unique), 19 featured-guest values (17 unique), 45 CI labels (44 unique), 43 startup labels (27 unique), 38 community labels (36 unique), **zero dates and zero central themes**. Issues 1–30 and 76 are absent from this history snapshot; absence is not proof they were never published. Issue 77 contains only Weav plus issue number.

- Issue 75 raw prose explicitly connects new episode **188/Ian Sandler** with CI **100/Guy Kawasaki**. CSV stores the CI heading “Leadership Is More Human Than Corporate,” losing the guest/episode relation even though the raw source contains it.
- Issue 69's new-episode passage names **182/Aman Verjee**, while CSV `featured_episode` is **83/Mark Suster**, from related content. Issue 68 similarly has new episode **181/Jonathan Crystal** but CSV says **20/Sheel Mohnot**. These are wrong-role joins, not just blank fields.
- Issue 70 `featured_guest` is a long narrative sentence. Issue 41 is only `Yi`. Nonempty counts therefore overstate usable guest metadata.
- Directly evaluating v3's read-only `build_history_stats()` on current files produces **0 matched appearances** across the 54 candidate guest records. All consequently receive its “fresh” +8 recency default and zero frequency score. Do not describe current CI spacing as reliable. Its frequency term rewards repeated usage up to +16 when matches exist; it is not a repetition penalty.
- Startup appearances are better structured: **30 embedded appearances across 11/14 companies**, with aliases/raw values preserved. The recommender reads these arrays for individual recency/frequency, using CSV only to determine latest issue. They can drift independently from the CSV. Issue differences are used, not elapsed days.
- All 14 startups have themes/industries; four have founder names/background, five have milestones, only Honeycomb has `last_news_date`, and only Coterie has guest relationships. `sure_relationship` objects exist throughout but object presence does not establish a verified relationship.
- Milestone scoring rewards available supported milestones (or lower-scored needs-review history items); it does not calculate time decay from `last_news_date`. This is not live news monitoring. Ava's documented category conflict is unresolved in the evidence: source registry says meeting intelligence while enrichment documents different official positioning.
- Discovery's “missing coverage” list only includes episodes with a number above the maximum represented history number. It does **not** audit historical holes below that number, and it relies on potentially misassigned history. Root discovery ends at 191; the saved episode 192 package has a newer snapshot. Neither proves what is newest today.

### Validation evidence and limits

`docs/connected-insights-v2-validation.md` explicitly reports 0/10 exact historical matches and warns about label/name mismatch; that metric cannot establish recommendation quality. `docs/connected-insights-v3-editorial-evaluation.md` contains human candidate judgments, useful but not an archive-wide performance evaluation. Startup evaluations describe weaker matches where the watchlist has no strong topic fit.

`docs/newsletter-production-pipeline-v1-validation.md` and saved 75/179 packages demonstrate cached-transcript production, transparent scores and editable drafts, not fresh end-to-end retrieval for every episode. An old `latest_discovery_run/briefing.json` has null episode number and guest “I'm your host”; later `latest_discovery_run_fixed` and active packages improve it. The audit did not rerun mutating production/retrieval commands or the publishing test suite. Its current checks were read-only data analysis and pure validation/history functions.

## 8. Dataset relationships and identifiers

| Relationship | Current key | Assessment |
|---|---|---|
| Episode ↔ ranking | Episode number; matching name/URL | All 54 Rank 4 records match export names and URLs. Prefer number plus retained source identity over guest name |
| Episode ↔ transcript | URL final slug + `_transcript.txt` | 56/57 main matches; early filenames contain no episode number. Requires manifest; don't infer solely from filename digits |
| Episode ↔ intelligence/themes | JSON `episode_number`, file `episode_N.json` | Strong within main corpus; no stable theme IDs; active and rank4 need explicit precedence if overlapping later |
| Episode ↔ guest | Human-readable `guest_name` | No guest entity table; repeat appearances and multiple guests prevent a name from serving as episode identity |
| Guest ↔ CI history | Lowercased whitespace-normalized name/token subset in CI heading | Zero current matches. Needs source-backed mapping, not looser guessing |
| Episode ↔ newsletter | CSV `featured_episode`; raw prose references | Some valid numeric joins, wrong section in others. Needs issue + section role + source passage |
| Startup ↔ history | `canonical_slug`, names/aliases, embedded issue references | Better normalized; CSV labels include headlines and non-watchlist companies; preserve unresolved rows |
| Guest ↔ startup | `guest_relationships[].guest_name` plus evidence/type | Only Coterie populated; fragile name matching, not a general investment graph |
| Episode ↔ generated packages | Embedded number/URL and output directory | Duplicate runs, null IDs and conflicting older metadata; directory called `latest` is not an authority |
| Episode ↔ social asset | Quote-job `episode.number`, record path/hash | Good explicit local provenance for 70; 196 provisional. No publication/channel identity |
| Guest ↔ portrait | Current library keyed by guest name; candidate paths/hashes | Good asset version pinning, fragile global guest identity and absolute local paths |

Keep both provenance and ambiguity visible. Prefer explicit identifiers; use human-reviewed alias mappings for names. A successful string/ID match is not sufficient to establish the semantic relationship (e.g. “featured episode” vs “Connected Insights”).

## 9. Missing data / engineering gaps

### A. Required for a useful V1

- One derived episode catalogue covering available identity sources, independent of Rank 4 eligibility. Exclude the export footer; retain thin records without inventing title/date/content.
- Explicit source manifest and availability states: transcript, enrichment, newsletter prose, provisional asset, missing source, shell artifact. Keep official material separate from generated summaries.
- Non-destructive readers and deterministic conflict rules for original vs editorial titles, active vs rank4, and historical output snapshots. Generated production runs must not override sources simply because they are named `latest`.
- Basic text index and reproducible source-passage references using file hashes and original offsets. Handle concatenated transcript turns without dropping otherwise usable text.
- Validation of identifier uniqueness, file mappings, source spans, unresolved references and coverage. Current editorial validators are not a general archive acceptance suite.
- A defined policy for local-only files. A portable first release can omit publishing examples or explicitly package approved source material; it must not silently depend on ignored paths.

Official show notes are absent. V1 should truthfully mark them unavailable and expose existing source types. Show-note ingestion becomes required only if the agreed launch scope promises show notes, rather than navigation among available material.

### B. Valuable but not required for V1

- Save a complete official metadata catalogue (titles, dates, URLs, stable remote IDs, descriptions when supplied); retrieve episode 2's missing transcript and extend transcript coverage beyond Rank 4.
- Parse raw newsletter issue sections into reviewed episode/CI/startup links. Show raw issue content meanwhile; defer unverified appearance badges.
- Add source-backed affiliations, multi-guest structure, theme/industry aliases, structured timestamp segments and verified quote anchors.
- Extend publishing/social inventory with provenance and actual publication records if available; broader guest portraits are optional.
- Review older enrichment, quote nonmatches and source/registry conflicts; retain original text and versioned corrections.

### C. Future intelligence/automation capabilities

Semantic retrieval, archive-wide entity extraction, similarity graphs, source-linked generated insight answers, continuous official ingestion, live startup-news research, automatic newsletter-history reconciliation, stronger recency-aware recommendations and editorial analytics. These require stronger source coverage and evaluation first. Automatic publishing is not justified by the current audit.

## 10. Minimum viable archive requirements

These are data/behavior requirements, not a UI design:

1. Enumerate all accepted catalogue identities, including metadata-only episodes, and report coverage separately from known episode count.
2. Search episode identity and available source text; optional filters can use existing enrichment with coverage labels.
3. Resolve an episode to its original records and available documents without conflating generated drafts with official content.
4. Return exact matching source text and surrounding context; label metadata-only matches honestly.
5. Show timestamps only when present; do not fabricate chapter structure or missing sources.
6. Surface stored themes/lessons with origin and draft/verification limitations. No requirement to enrich every episode before launch.
7. Link related newsletter/social material only when the relation is supported; unresolved candidates remain separate.
8. Rebuild derived data without editing sources and produce a clear validation/coverage report.

V1 does not need recommendation tuning, every company/person as an entity, a vector database, a comprehensive content-management workflow, or full archive backfill.

## 11. Recommended implementation sequence

**No step below has been implemented in this audit.**

1. **Approve scope and authoritative-source policy.** Use rankings for the existing identity baseline, main transcript text for retrieval, and main episode JSON as optional enrichment. Treat newsletter prose as historical editorial source and startup records as a separate curated collection. Decide whether provisional 196/local publishing assets belong in the initial corpus.
2. **Build a small read-only derivation command.** Produce an application-ready episode catalogue plus source manifest and diagnostics in a separate derived location. Join by verified number/URL/slug; preserve source values and conflicts, exclude shells/footer, label provisional identities. This is an additive layer, not a replacement data model for editorial tools.
3. **Add lexical indexing and provenance checks.** Index source text and selected metadata; keep original passage offsets/hashes and availability flags. Test a missing-transcript episode, concatenated early transcript, timestamped active episode, repeated guest, ambiguous newsletter link and stale output snapshot. Use the smallest local index implementation that meets the query need; no framework or database choice is necessary to approve this audit.
4. **Review the derived coverage and search results.** When browse identity, episode-to-source resolution, exact passage tracing and missing-data behavior are correct, it becomes sensible to build the first interface. A full metadata refresh is helpful but not a blocker for an explicitly partial local archive.
5. **Next ingestion priority:** retain a full official metadata response/normalized catalogue, including descriptions and dates; recover episode 2 source text, then expand transcripts according to editorial demand. `episode_discovery.py` already paginates the API but saves only a selected report, so it cannot currently produce the full derived archive dataset unchanged. Transcript retrieval code is reusable but needs portability/format review before broader ingestion.
6. **Then recover newsletter relations.** The existing raw archive offers high-value repairs without new external research. Derive section-aware links and review them, keeping the current CSV untouched until a separate change is approved. Improve CI history only after this mapping is trustworthy.
7. **Only later extend intelligence.** Evaluate recommendation quality against reviewed section identities and source-grounded examples before adding semantic retrieval, generated insights or more automation.

Leave the ranking export, transcripts, curated Rank 4 records, active records, startup sources, history CSV/raw archive, existing scripts and publishing approval assets untouched during initial derivation. Existing loaders provide useful building blocks but **no current script produces the complete catalogue/source/index layer**. Do not repurpose the replacing importer or hard-coded phase2 processor as that layer.

Do not build the interface before the audit is reviewed; do not build an autonomous newsletter agent, automated publisher, comprehensive entity graph, vector search system, or bulk enrichment job as the first engineering step.

## 12. Evidence useful for the future portfolio case study

| Evolution evidence | Repository evidence | Accurate claim and limit |
|---|---|---|
| Manual editorial process | `docs/workflows.md`, raw newsletter archive | Documented editorial tasks and historical material; no measured time savings |
| Structured memory | Importer, history CSV, `docs/name-normalization-report.md`, history validation | Script-assisted extraction and conservative cleanup exist; unresolved extraction errors are part of the story |
| Retrieval repair | `transcript_ingestion.py`, Playwright retrievers, investigation/repair/phase reports | Browser retrieval addressed SPA shells; not a fully complete archive |
| Structured intelligence | 54 rank4 JSON + phase analyses; active generator + 190–192 | Curated selected corpus and heuristic fresh-episode drafts; not automatic high-quality semantic understanding |
| Transparent recommendations | CI v1/v2/v3, startup v1, editorial evaluations | Implemented scoring and human evaluation; current CI history matching is broken, so avoid claiming successful repetition avoidance |
| Production assistance | 10 saved newsletter packages, pipeline validation | Generates briefing/draft scaffolds with review notes; does not demonstrate final publication |
| Discovery evolution | `episode_discovery.py`, discovery snapshots; commits `e658561`, `3c5b237` | On-demand discovery and active-record support; snapshots aren't continuous monitoring |
| Editorial relationship refinement | Coterie evidence, `52121eb` | Specific verified shared-investment priority, not universal relationship knowledge |
| Provenance-aware visual production | Publishing schema/code/tests, template approval, portrait lifecycle, `b555652` | Local deterministic rendering, source checks and human approval lifecycle; no delivery/publishing integration. Pavel remains an editorial paraphrase with provisional transcript provenance |
| Searchable reusable archive | This audit's recommendations | Proposed next stage only; no existing archive interface/search index to demonstrate yet |

A defensible case study can show raw material → extracted records → validation/repair → scored recommendations → editable draft/visual artifacts. It should include human review and known failures. Quantified productivity gains need future measurement; commit titles and validation prose alone do not establish them.

## 13. Open questions / decisions needed

1. Should the first archive include every locally evidenced episode as a thin catalogue entry, while clearly labeling incomplete sources? Recommended: yes, without using rank as a browsing restriction.
2. Should official titles take precedence when available, with current intelligence titles retained as editorial titles? Recommended: preserve both rather than silently overwriting.
3. Is provisional episode 196/Pavel material approved for inclusion, and should ignored local publishing assets be made portable? Its current source receipt explicitly says website correspondence is unverified.
4. Is initial partial transcript coverage acceptable, or is full-archive coverage a launch requirement? Recommended: launch on verified available content and report gaps.
5. Are show notes required at launch? If yes, official description ingestion moves ahead of interface work; newsletter prose should not substitute silently.
6. Who should review recovered newsletter section mappings and the definition of featured vs CI episodes? The raw archive can resolve many cases, but ambiguous cases need editorial judgment.
7. Which official ranking/watchlist snapshot should be authoritative for later refreshes, and how should source updates be reviewed? The local export is not a live connection.

### Audit method and reproducibility notes

Read repository documentation, Python/JavaScript entry points, JSON/CSV/text sources, publishing configuration and source receipts; inspect Git status/history and ignored asset directories. Counts used Python standard-library `pathlib`, `csv`, `json`, `re`, `collections`, and `hashlib` in shell heredocs. No temporary analysis files were committed or saved. Python imports used `-B` to avoid bytecode writes and called only read-only/pure functions, never CLI `main()`.

Key reproducible definitions:

- Rankings: `csv.DictReader(..., delimiter='\t')`; accept numeric `EPISODE NO.` only. Main enrichment: `data/episodes/*/episode_*.json`, excluding the template.
- Transcript mapping: final component of `episode_url` + `_transcript.txt`. Shell duplicates: SHA-256 of `.html` bytes. Timestamp presence: `\[\d{2}:\d{2}:\d{2}\]`, not generic clock patterns.
- Identifiable episode union: numeric ranking IDs, main JSON IDs, CSV numeric featured IDs, structured discovery/output episode numbers, explicit `episode #?N` prose references in the raw archive, then separately provisional publishing ID 196.
- Newsletter counts: `csv.DictReader` nonempty fields and distinct issue numbers; raw issue headings anchored to `Newsletter #N`. Main episode joins were numeric membership, not asserted semantic validity.
- CI match count: sum `appearances` from `connected_insights_recommender_v3.build_history_stats(load_episode_records(), load_newsletter_history())` = 0.
- Transcript-format check: `newsletter_production_pipeline_v1.validate_transcript()` applied to existing text, without retrieval or writes = 47 accepted / 56.
- Quote text presence: lowercase and collapse whitespace in each quote/transcript, then substring check = 156/168; excludes episode 2 and does not verify speaker/context.

These checks establish current local structure and coverage, not live URL validity, transcript accuracy against audio, or fresh editorial approval. Existing source files and scripts were left unchanged.
