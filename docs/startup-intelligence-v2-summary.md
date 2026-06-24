# Startup Intelligence Layer v2 Summary

## Purpose

Startup Intelligence Layer v2 enriches the 14 approved Startup Corner watchlist records using official company websites and repository-documented sources only.

Sources used:

- `docs/sources.md`
- `data/newsletter_history.csv`
- official company websites listed in `docs/sources.md`
- official company About, Team, Story, or homepage pages when available

No third-party news sites were used as primary sources. No Sure relationship, guest relationship, or founder detail was inferred when direct official evidence was unavailable. After Episode 191 production, transcript-supported Coterie relationship metadata was added because the episode directly states that Gopi Rangan and Justin Smith-Lorenzetti are co-investors in Coterie.

## Fields Enriched

Across `data/startups/*.json`, v2 enriched:

- `industries`: expanded from a single sourced category into scoring-ready industry tags.
- `themes`: added company-positioning themes from official website copy.
- `founder_names`: populated only where official pages identified founders.
- `founder_background`: populated only where official pages described founder or founding context.
- `notable_milestones`: added official-site-supported milestones where available.
- `last_news_date`: populated only where an official company page provided a dated news item.
- `source_urls`: expanded with official pages and local repository sources, including `fields_supported`.
- `confidence_notes`: added field-level notes for every v2-populated field.

## Enrichment Coverage

| Company | Industries | Themes | Founder names | Notable milestones | Last news date |
|---|---:|---:|---:|---:|---|
| Lumber | 7 | 5 | 2 | 1 | No |
| TrustLayer | 6 | 5 | 0 | 0 | No |
| PAXAFE | 8 | 6 | 0 | 1 | No |
| Coterie | 6 | 6 | 0 | 2 | No |
| Hi Marley | 6 | 6 | 3 | 3 | No |
| Ava | 5 | 5 | 0 | 0 | No |
| Insurate | 6 | 4 | 0 | 0 | No |
| Juno | 5 | 5 | 2 | 0 | No |
| FirstShift | 6 | 5 | 0 | 0 | No |
| Balance Cash | 6 | 6 | 0 | 0 | No |
| Rigor.ai | 5 | 4 | 0 | 0 | No |
| Honeycomb | 6 | 5 | 0 | 2 | 2026-06-09 |
| Konfyd | 5 | 5 | 0 | 0 | No |
| Weav | 6 | 6 | 1 | 0 | No |

## Strongest Intelligence Coverage

These records now have the strongest v2 coverage for future recommendation scoring:

- Lumber: rich industry/theme coverage plus official founder names from its About page.
- Hi Marley: strong theme coverage, official founder story, launch milestone, and company-scale positioning.
- Juno: clear product category, family/benefits themes, and official cofounder details.
- Weav: clear insurance-AI themes plus official founder/leadership evidence.
- Honeycomb: strong industry/theme coverage plus recent official Newsroom items and `last_news_date`.
- PAXAFE: strong logistics, cold-chain, IoT, and decision-intelligence themes from official homepage and About page.

## Remaining Gaps

Fields still requiring manual review or additional approved sources:

- `sure_relationship`: left blank for all startups because v2 found no direct official or repository-supported relationship detail beyond watchlist inclusion.
- `guest_relationships`: populated only for Coterie where the Episode 191 transcript directly supports a shared-investment relationship with Justin Smith-Lorenzetti; otherwise left blank.
- `founder_names` and `founder_background`: still blank for TrustLayer, PAXAFE, Coterie, Ava, Insurate, FirstShift, Balance Cash, Rigor.ai, Honeycomb, and Konfyd.
- `last_news_date`: populated only for Honeycomb because other reviewed official pages did not provide a clear dated news item suitable for the field.
- `notable_milestones`: sparse for several companies because v2 avoided treating generic product positioning as a milestone.

## Startups Requiring Manual Review

High-priority manual review:

- TrustLayer: founder and Sure relationship details.
- PAXAFE: founder details and whether the newsletter-history FreightTech 100 item should remain as a milestone.
- Coterie: founder details; the 2018 launch milestone and Justin Smith-Lorenzetti shared-investment relationship are now supported by approved sources.
- Ava: official company category in `docs/sources.md` says AI Meeting Intelligence, while the official website currently positions Ava as a credit-building app.
- FirstShift: official homepage metadata supports AI supply-chain planning, but the rendered page exposed limited body text.
- Balance Cash: founder details and any relationship context.
- Rigor.ai: founder details, product details beyond the homepage, and relationship context.
- Honeycomb: founder details and review of recent official Newsroom items.
- Konfyd: founder details and relationship context.

## Data Quality Limitations

- Official websites vary in how much structured text they expose.
- Some pages expose product positioning but not founder or company-history data.
- Some newsletter-history milestones remain marked `needs_manual_review` because the source is the newsletter dataset rather than a current official company announcement.
- The startup watchlist establishes eligibility, but it does not document the specific Sure relationship type.
- V2 uses official company websites and repository sources only, so it intentionally excludes third-party coverage that might otherwise improve milestone and founder coverage.

## Validation Results

Validation performed:

- All 14 startup JSON files parse successfully.
- All records contain the required v1 schema fields.
- Every record has at least one `source_urls` entry for `docs/sources.md`.
- Every record with newsletter appearances has a `source_urls` entry for `data/newsletter_history.csv`.
- Every record has official-source attribution for v2 `industries` and `themes`.
- Founder fields are populated only when official pages identify founders.
- Sure and guest relationship fields remain sparse; Coterie now has transcript-supported relationship evidence from Episode 191.

## Readiness for Startup Recommendation Engine v1

The v2 layer is sufficient to support a first recommendation engine that scores:

- episode-to-startup industry overlap
- episode-to-startup theme overlap
- newsletter recency and frequency
- recent activity where available

The engine scores verified shared-investment relationships as a first-choice Startup Corner priority. Other Sure relationship or guest relationship signals should remain inactive unless manually enriched with approved evidence.

## Recommended Next Steps

1. Manually verify relationship data.
   - Add Sure relationship type and evidence only where approved for editorial use.

2. Add founder evidence for sparse records.
   - Use official company team/about pages or approved internal materials.

3. Normalize startup categories.
   - Resolve category conflicts such as Ava's current official positioning versus the older source-registry category.

4. Add official milestone review.
   - Confirm which newsletter-history milestone rows should remain in `notable_milestones`.

5. Continue improving Startup Recommendation Engine v1.
   - Keep shared-investment scoring active only for verified relationship fields, and continue industry/theme/newsletter-recency scoring for all other cases.
