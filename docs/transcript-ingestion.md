# Transcript Ingestion Prototype

This document describes the transcript ingestion prototype for TSSE episode transcripts.

## Purpose

Transcript ingestion is the missing foundational capability for Episode Intelligence.
It enables the project to move from placeholder records to real episode metadata sourced directly from TSSE transcripts.

## URL derivation rules

TSSE transcript URLs follow a standard pattern.

- Episode URL: `https://podcast.sure.ventures/episodes/<slug>`
- Transcript URL: `https://podcast.sure.ventures/episodes/<slug>/transcript`

Implementation notes:

- If the input URL already ends with `/transcript`, it is returned unchanged.
- Trailing slashes on the episode URL are normalized before appending `/transcript`.

## Storage conventions

Transcripts are stored locally under `data/transcripts/`.

Filename convention:

- `data/transcripts/<episode-slug>_transcript.html`

Where `<episode-slug>` is derived from the episode path.

Example:

- Episode URL: `https://podcast.sure.ventures/episodes/100-angel-investments`
- Saved file: `data/transcripts/100-angel-investments_transcript.html`

## Error handling

The prototype handles the following failure modes:

- Missing or invalid episode URL
- Failure to derive a transcript URL
- Network errors when fetching the transcript
- HTTP errors from the TSSE site
- Unexpected response content

The script reports errors clearly and exits with a traceback when a fetch fails.

## Validation process

After saving a transcript, the prototype performs a lightweight validation check:

- file exists
- file length is greater than 100 characters
- file contains an HTML payload (`<html`)

This validation is intentionally simple for the prototype stage.

## Usage

Run the prototype with an episode URL:

```bash
python3 transcript_ingestion.py --episode-url "https://podcast.sure.ventures/episodes/100-angel-investments"
```

Or test using the first Rank 4 episode from `data/guest_rankings.csv`:

```bash
python3 transcript_ingestion.py --sample-rank4
```

## Next steps

Once transcripts are stored locally, the next step is to extract structured intelligence from the transcript HTML and populate `data/episodes/rank4/*.json`.

This prototype is intentionally narrow: it only derives and retrieves transcripts, stores them locally, and verifies the result.
