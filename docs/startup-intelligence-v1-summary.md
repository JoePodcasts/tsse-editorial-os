# Startup Intelligence Layer v1 Summary

## Purpose

Startup Intelligence Layer v1 creates structured records for the approved Startup Corner watchlist using only repository-local sources.

Sources used:

- `docs/startup-intelligence-design.md`
- `docs/sources.md`
- `data/newsletter_history.csv`

No web browsing was performed. No recent news, founder details, Sure relationship details, or guest relationships were invented.

## Records Created

Created `data/startups/` with one JSON file per approved watchlist company:

| Company | File | Prior Startup Corner appearances normalized |
|---|---|---:|
| Lumber | `data/startups/lumber.json` | 4 |
| TrustLayer | `data/startups/trustlayer.json` | 1 |
| PAXAFE | `data/startups/paxafe.json` | 5 |
| Coterie | `data/startups/coterie.json` | 2 |
| Hi Marley | `data/startups/hi_marley.json` | 2 |
| Ava | `data/startups/ava.json` | 3 |
| Insurate | `data/startups/insurate.json` | 2 |
| Juno | `data/startups/juno.json` | 3 |
| FirstShift | `data/startups/firstshift.json` | 4 |
| Balance Cash | `data/startups/balance_cash.json` | 0 |
| Rigor.ai | `data/startups/rigor_ai.json` | 0 |
| Honeycomb | `data/startups/honeycomb.json` | 3 |
| Konfyd | `data/startups/konfyd.json` | 0 |
| Weav | `data/startups/weav.json` | 0 |

Total records created: 14.

## Fields Successfully Populated

The following fields were populated from repository-local evidence:

- `company_name`: from the approved watchlist.
- `canonical_slug`: generated from approved company names.
- `website`: from `docs/sources.md`.
- `category`: from `docs/sources.md`.
- `industries`: initialized from the sourced category.
- `previous_newsletter_appearances`: normalized from `data/newsletter_history.csv` where the company name or a clear alias appeared.
- `source_urls`: initialized with the official website listed in `docs/sources.md`.
- `confidence_notes`: populated with source and limitation notes.
- `evidence_status.newsletter_history_reviewed`: set to `true` because v1 parsed local newsletter history.

The following clear aliases were normalized:

- `HoneyComb` -> Honeycomb
- `Firstshift AI` -> FirstShift
- `Coterie Insurance` -> Coterie
- `Coterie - a vision driven by AI and human creativity` -> Coterie
- `PAXAFE Named a FreightTech 100 company` -> PAXAFE
- `Hi Marley is CNBC's World's Top InsurTech 2024` -> Hi Marley
- `Lumber makes The Business Case for Supporting Women in Construction` -> Lumber

## Fields Requiring Manual Research

These fields were intentionally left blank or empty unless repository-local evidence existed:

- `themes`
- `founder_names`
- `founder_background`
- `sure_relationship.relationship_type`
- `sure_relationship.relationship_notes`
- `sure_relationship.evidence`
- `guest_relationships`
- `last_news_date`

Some `notable_milestones` were created only when the newsletter history value itself named the company and described a milestone. These entries are marked `needs_manual_review` and should not be treated as verified current news until reviewed.

## Data Quality Limitations

Newsletter history is useful but not fully normalized:

- `startup_corner_company` mixes company names, aliases, and headline-style descriptions.
- `publication_date` is empty for all rows, so `last_news_date` cannot be derived.
- Some Startup Corner values refer to companies outside the current approved watchlist.
- Some headline-style values may correspond to watchlist companies but do not name the company clearly enough for automated mapping.
- Company category comes from `docs/sources.md`; richer industries and themes still require manual enrichment.
- Founder and relationship fields require authoritative review before they can be used in recommendation scoring.

Unmapped `startup_corner_company` values retained for future review:

- Joshu
- Mile Auto
- Joshin
- BalkanID
- TaskHuman
- Koop
- MileAuto ranked among Inc. 5000 fastest growing companies
- Decent Honored at the Rosie Awards 2024
- Transforming Construction Workforce Management With AI
- Personalized Neurodiversity Support to Employees

## Validation Results

Validation performed:

- All 14 JSON records parse successfully.
- All records include the required minimum fields:
  - `company_name`
  - `website`
  - `category`
  - `industries`
  - `themes`
  - `founder_names`
  - `founder_background`
  - `sure_relationship`
  - `guest_relationships`
  - `notable_milestones`
  - `last_news_date`
  - `previous_newsletter_appearances`
  - `source_urls`
  - `confidence_notes`
- All approved watchlist companies have exactly one startup intelligence record.
- No external web data was used.

## Recommended Next Steps

1. Manually review each startup profile.
   - Confirm website, category, richer industry tags, and editorial themes.

2. Enrich founder and relationship fields.
   - Add founder names, founder background, Sure relationship notes, and evidence.

3. Normalize newsletter history further.
   - Decide whether ambiguous headline-style entries should map to approved watchlist companies.
   - Preserve raw values even when canonical company names are added.

4. Add reviewed milestone evidence.
   - Use official company websites, company blogs, press pages, and approved Sure materials only after source approval.

5. Build validation tooling.
   - Add a script that confirms all watchlist companies exist, required fields are present, and no non-watchlist company can be recommended.

6. Implement Startup Recommendation Engine v1.
   - Use the v1 startup records as the candidate data layer.
   - Score only reviewed fields and return explainable recommendations.
