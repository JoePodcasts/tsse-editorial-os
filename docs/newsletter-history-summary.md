# Newsletter History Dataset Summary

## 1. Total newsletter issues

- Total records: 45

## 2. Unique Connected Insights guests

- Unique Connected Insights guest values: 44

## 3. Most frequently featured Connected Insights guests

The dataset currently stores Connected Insights labels rather than normalized guest names in many cases. The most frequent values are:

1. `Look where others are not looking` — 2 occurrences
2. `Leadership Is More Human Than Corporate` — 1 occurrence
3. `Competition Is Irrelevant When You're Building Infrastructure` — 1 occurrence
4. `Conviction in the absence of traditional metrics` — 1 occurrence
5. `Start with Your Childhood, Not Your Resume` — 1 occurrence

## 4. Unique Startup Corner companies

- Unique Startup Corner companies: 26

## 5. Most frequently featured startups

1. `PAXAFE` — 4 occurrences
2. `FirstShift` — 3 occurrences
3. `Juno` — 3 occurrences
4. `Ava` — 3 occurrences
5. `Lumber` — 3 occurrences

Additional frequent startups:
- `Joshu` — 3 occurrences
- `Insurate` — 2 occurrences
- `Honeycomb` — 2 occurrences

## 6. Issues with missing fields

### Missing field counts

- `featured_episode`: 27 issues missing
- `featured_guest`: 26 issues missing
- `connected_insight_guest`: 0 issues missing
- `startup_corner_company`: 3 issues missing
- `community_organization`: 7 issues missing
- `publication_date`: 45 issues missing
- `central_theme`: 45 issues missing

### Issues missing critical fields

#### Missing `startup_corner_company`

- Issues: 32, 33, 34

#### Missing `featured_guest`

- Issues: 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 49, 51, 52, 53, 54, 62, 63, 64, 65, 66, 67, 71, 72

#### Missing `featured_episode`

- Issues: 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 49, 51, 52, 53, 54, 62, 63, 64, 65, 66, 67, 70, 71, 72

## 7. Dataset quality assessment

### Strengths

- The importer successfully parsed 45 historical newsletter issues from the archive.
- Connected Insights values are complete for all parsed records.
- Startup Corner values are complete for the vast majority of issues.

### Limitations

- `featured_guest` and `featured_episode` are missing in many older issues because the archive text does not include explicit episode/guest metadata in a consistent, machine-readable way.
- `publication_date` and `central_theme` are missing for every issue, indicating those fields were not available in the source archive or not labeled consistently.
- Connected Insights values currently include section titles in some cases rather than normalized guest names. This reduces the usefulness of the field for guest-based analysis.
- There are minor startup name inconsistencies in the dataset, for example `Honeycomb` vs `HoneyComb`, which should be normalized before using the dataset for reporting or recommendation logic.

### Recommended next steps

1. Improve archive extraction rules to capture `featured_guest` and `featured_episode` more reliably from narrative text.
2. Add normalization for Connected Insights guest names to distinguish guest titles from the section headline.
3. Standardize startup company names across the dataset.
4. Add a post-import validation step that flags missing `featured_guest` and `featured_episode` for manual review.
