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
