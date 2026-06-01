# Newsletter Archive Importer

This document describes the first-version importer for historical TSSE newsletter issues.

## Purpose

The importer is designed to parse a plain-text archive located at `data/newsletter_archive_sample.txt` and populate `data/newsletter_history.csv` with structured newsletter issue metadata.

## Expected Archive Structure

The importer assumes the archive is organized by issue headings and labeled fields. The core extraction rules are:

- Each issue begins with a heading like `Issue 31`, `Issue 32`, etc.
- Issue metadata appears in labeled lines such as:
  - `Episode: 186`
  - `Featured Guest: Debjit Mukerji`
  - `Connected Insights Guest: Karthee Madasamy`
  - `Startup Corner Company: PAXAFE`
  - `Community Organization: MedShare`
  - `Central Theme: Deep Tech`
  - `Publication Date: ...`
- If the issue heading includes a separator and a date, the importer attempts to capture it.

## Extraction Rules

The importer currently extracts the following fields from each issue block:

- `issue_number`
- `featured_episode`
- `featured_guest`
- `connected_insight_guest`
- `startup_corner_company`
- `community_organization`
- `publication_date`
- `central_theme`

Field extraction is case-insensitive and supports both `:` and `-` separators.

## Assumptions

- The archive is text-based and uses explicit labels for the key newsletter sections.
- Issue blocks are separated by lines starting with `Issue <number>`.
- A single issue block contains all available fields for that issue.
- If a field cannot be found with the expected label pattern, it is left blank.

## Difficult Fields

The following fields are the most difficult to extract reliably from a free-form newsletter archive:

- `publication_date`
  - Publication date is often missing or presented in an inconsistent format.
- `central_theme`
  - Themes may be described in prose rather than as a distinct labeled field.
- `community_organization`
  - Community involvement may be mentioned within narrative text instead of as a dedicated label.

## Recommendations

To improve future archive import quality, the newsletter archive should be structured with consistent, machine-readable labels:

1. Standardize each newsletter issue heading as `Issue <number>`.
2. Use explicit labeled fields for each metadata item, e.g.:
   - `Episode:`
   - `Featured Guest:`
   - `Connected Insights Guest:`
   - `Startup Corner Company:`
   - `Community Organization:`
   - `Publication Date:`
   - `Central Theme:`
3. Keep each label on its own line.
4. Avoid embedding multiple metadata values in one sentence.
5. Consider providing a separate CSV or JSON export for historical issues.

## Current Status

At the time of this implementation, the importer is ready to run but the archive sample file `data/newsletter_archive_sample.txt` was not present in the repository workspace. Once that file is available, the importer can parse it and update `data/newsletter_history.csv`.

## Findings from the sample archive

- Parsed issues: 45 (Newsletter #31 through Newsletter #75).
- Recurring sections observed in every issue (in roughly this order):
  - Email Intro / Host note
  - New Podcast (episode title and summary)
  - Quote (episode highlights)
  - Connected Insights (a past episode or guest used as thematic connection)
  - Startup Corner (featured startup and short description)
  - Community Involvement (nonprofit or community org)

- Consistency and extraction pattern:
  - Every issue begins with a heading like `Newsletter #<n>:` which provides a reliable block boundary.
  - Labeled sections (e.g., `Startup Corner:`, `Community Involvement:`) are common and provide stable anchors for extraction.
  - The podcast episode number and guest are frequently present in prose such as `In Episode 188, my guest is Ian Sandler` — this required heuristics to extract reliably.
  - Connected Insights frequently uses a short title (e.g., `Connected Insights: Leadership Is More Human Than Corporate`) and then references a past episode and guest in the following paragraphs.

- Fields reliably extracted with current heuristics:
  - `issue_number` (very reliable due to heading format)
  - `startup_corner_company` (labeled and often clearly formatted)
  - `community_organization` (labeled)

- Fields that required heuristics and were harder to extract:
  - `featured_episode` and `featured_guest` — often embedded in narrative sentences rather than in a single labeled line; heuristics were added to capture `In Episode <n>, my guest is <Name>` patterns.
  - `connected_insight_guest` — the Connected Insights section often contains a title and then a narrative that mentions the guest; we capture the guest only when a clear pattern (`In Episode <n>, <Name>`) is found near the Connected Insights title.
  - `publication_date` — rarely present explicitly in the archive headings; usually missing.
  - `central_theme` — sometimes available as a short label, but frequently expressed in prose (hard to normalize automatically).

- Examples of extraction limitations observed:
  - Guest attributions sometimes include trailing organization text (e.g., `Gilad Shai from BMI`) which may require post-processing to normalize.
  - Some Connected Insights entries include only a short title and do not name the guest in the header; the guest appears later in the paragraph and required section-specific matching.

## Recommendations (practical next steps)

1. Keep publishing the archive as plain text but standardize a small set of labeled fields for each issue (even simple one-line labels for `Episode:`, `Guest:`, `Connected Insights Guest:` would dramatically improve extraction quality).
2. Add optional CSV/JSON export of every newsletter at publish time to serve as canonical machine-readable historical data.
3. For the importer, consider incrementally improving name normalization (strip trailing `from <org>`, unify punctuation, and optionally cross-reference guest names with the guest database to improve quality).
4. If full fidelity is required, consider a lightweight human review step for parsed records (e.g., a short verification UI showing parsed fields for validation).
