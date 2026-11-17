# TSSE category classification · Phase 1B

Start with the [editorial review](proposed/review.md) and [coverage matrix](proposed/coverage.md). The [nine category definitions](taxonomy.json) have editor approval for planning. Episode memberships, category–theme links, and the [nine Phase 1 themes](../catalogue.json) await separate decisions.

## Inputs and method

The November 10 canonical snapshot has 197 published episodes, 197 official transcripts, 197 published show notes, 18,770 transcript passages and 2,231 show-note passages. The initial counts were independently reconstructed from the manifest, catalogue and production source segmenter. Phase 1 remains at revision `bbb034b`. It supplied 88 previously curated passages, the editorial propositions and their documented attribution limits. The discovery catalogue continues to be independently reproducible.

1. Load the nine ordered definitions and their versioned [signal vocabulary](signals.json). Reuse Phase 1’s canonical archive loader, raw/projection hash checks and production lexical-v2 passage IDs. Group documents by Simplecast ID. All records with public presence marked present enter the inventory.
2. Examine every episode against every category. Search its title and the editorial portion of its published notes for subject anchors. Stop note corroboration at recognizable biography, nonprofit or promotional headings. This heuristic does not catch every variant. Notes and titles can corroborate a subject, but cannot generate a membership by themselves.
3. Within a transcript, screen exact sentence-like spans of 65–700 characters for a topical anchor and a separate contextual expression from the same facet. Exclude questions and common introductions. Favor the body of the conversation by omitting passages wholly before the first 6% or 350 characters and passages starting after 96%. Rank by the number of distinct context matches (capped at four), with one extra point above 130 characters. Break ties by source position and passage ID. Separate retained hits by at least 800 characters and require different passage IDs. The window count measures separated pieces of text, not independent people or statistical confidence.
4. Propose **strong** when a title or note anchor is corroborated by at least three separated transcript windows. Propose **secondary** with two such windows plus editorial corroboration, seven windows without it, or a selected Phase 1 passage explicitly mapped to this category. An editor evaluating strength should ask whether a subject shapes a substantial part of the episode or a meaningful supporting segment. Repeated lexical evidence is a proxy for that distinction.
5. Apply the [source-context decisions](context-review.json). The second pass compared apparent omissions with the published titles, chapter headings or summaries, then reopened transcript passages using alternate formulations. Examples include “12 months of technical defensibility” in episode 96, the “5Ps” in 103, and “proof of value” in 195. This pass also ruled out hits where the speaker described a former employer, an investor’s conviction, or a marketplace for recruiting software. An explicit contextual decision can change strength, add a source-exact passage or exclude a pair. Contextual strength reflects the role of the discussion in the episode. These are model-assisted editorial proposals, never a human sign-off.
6. Keep up to two separated excerpts per association, prioritizing a frozen contextual selection and then a relevant Phase 1 passage. A record may have one sufficient passage even if the wider episode was examined. When available, retain up to two subject-matching show-note references, preferring overlap with the selected transcript words. Extract evidence unchanged from the canonical text and link to the existing reader. Use the source label on the parent passage or “unknown”. A start time is present only if a genuine bracketed marker begins the excerpt. End times remain null.
7. Review category–theme connections independently. The primary relationship expresses the recurring question’s most natural navigation home. Secondary connections name the narrower aspect and pin specific Phase 1 evidence, such as insurance carriers in a distribution theme. An omitted relationship has no proposed link in this release. Category membership by itself supplies no new editorial theme. Episode 24 illustrates the distinction: simplifying a complex idea can help with recruiting even though the wider pitch-clarity theme sits under fundraising.

Replaying the curated inputs is deterministic. Selecting new interpretations is a judgment task; the precise model revision and sampling controls for the initial contextual pass were unavailable. No external service is required for a replay. Screening can miss long arguments, unusual phrasing and mistranscriptions. The field `independent_windows` refers only to separated *lexically detected* windows. Zero may accompany valid contextual evidence. Use the linked transcript and preceding/following turns to assess meaning. Frequent use of the same expression in a guest introduction can still inflate a candidate’s apparent strength.

## Data contract

|File|Role and join|
|---|---|
|[taxonomy.json](taxonomy.json)|Definition owner. Stable `id` is the join key. Stable `slug` is the future route. Wording, scope and order come from the editor’s brief.|
|[inventory.json](proposed/inventory.json)|One row per canonical episode, including source URL, title, explicit outcome and zero or more category IDs.|
|[associations.json](proposed/associations.json)|Unique episode–category pairs with strength, interpretation, source references, review metadata and a SHA-256 fingerprint over excerpt records and note IDs.|
|[evidence.json](proposed/evidence.json)|Deduplicated verbatim excerpts. Keys encode canonical passage ID, Unicode code-point offset within the passage, and length. One passage can supply different excerpts. The reader highlights its parent passage.|
|[theme-links.json](theme-links.json)|Proposed primary and secondary joins to original theme IDs. Each fingerprint covers the actual Phase 1 selection records, including their exact spans and rationale.|
|[manifest.json](proposed/manifest.json)|Archive fingerprint, classification version and independently derived source counts.|

To open a supporting note in the existing reader, use the episode’s internal route followed by `/show-notes?passage=<show_note_passage_id>`. The original episode URL comes from the inventory. The research data contains no audio-verified quote attribution.

## Reproduce or extend

Run from the repository root with the project Python runtime and standard library:

```sh
python3 -B research/themes/categories/classify.py --check
python3 -B -m unittest discover -s research/themes/categories -p 'test_*.py'
python3 -B -m unittest discover -s research/themes -p test_themes.py
```

To regenerate the proposal after a research edit, omit `--check`. Use a branch and inspect the data/report diff. For a future snapshot, recompute the source counts, inspect changed source IDs, review new episodes and update the version and representative examples. Changed source hashes produce different passage IDs; manually relocate a selection and review its meaning again. Keep signed human decisions outside the generated directory, keyed by category, episode or theme, version, and evidence fingerprint. Match a decision to the exact version reviewed before making a public release.

The [Phase 2 plan](phase-2.md) extends the existing archive reader. The current draft contains research only.
