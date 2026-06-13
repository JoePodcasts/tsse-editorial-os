# Playwright Transcript Validation

## Scope

This validation covers a Playwright-based transcript retrieval prototype for Episode 73 only.

- Episode: 73
- Guest: Charles Hudson
- Transcript URL: `https://podcast.sure.ventures/episodes/tsse73-pre-revenue-startups-charles-precursor/transcript`
- Saved transcript: `data/transcripts/tsse73-pre-revenue-startups-charles-precursor_transcript.txt`
- Existing static HTTP shell retained for comparison: `data/transcripts/tsse73-pre-revenue-startups-charles-precursor_transcript.html`

No episode intelligence records were modified.

## Prototype

The prototype is implemented in `playwright_transcript_retrieval.mjs`.

It does the following:

- Launches Chromium through Playwright.
- Opens the Episode 73 transcript route.
- Waits for rendered DOM text containing both expected speaker labels.
- Extracts transcript paragraphs from rendered `<p>` elements.
- Starts at the first `Charles Hudson:` transcript paragraph.
- Stops before the Simplecast footer/cookie content.
- Writes a plain-text transcript artifact.
- Validates byte length, speaker labels, and absence of SPA shell markers before saving.

The script is intentionally Episode 73-specific. It does not iterate over Phase 2 episodes.

## Retrieval Result

The successful run produced:

```json
{
  "episode": 73,
  "outputPath": "/Users/jwanyua/tsse-editorial-os/data/transcripts/tsse73-pre-revenue-startups-charles-precursor_transcript.txt",
  "validation": {
    "byteLength": 23288,
    "characterLength": 23288,
    "paragraphCount": 67,
    "missingSpeakers": [],
    "hasHtmlShell": false,
    "valid": true
  }
}
```

## Shell Check

Static HTTP retrieval still returns the Vite SPA shell:

```text
3281 data/transcripts/tsse73-pre-revenue-startups-charles-precursor_transcript.html
```

The rendered Playwright transcript is materially larger:

```text
23288 data/transcripts/tsse73-pre-revenue-startups-charles-precursor_transcript.txt
```

The saved text file does not contain the HTML shell markers used by the static retrieval path, including:

- `<!DOCTYPE html>`
- `<div id="app"></div>`
- `polyfills-legacy`

## Speaker Validation

Both expected speaker labels are present in the saved transcript:

- `Charles Hudson:`
- `Gopi Rangan:`

The transcript starts with rendered episode dialogue:

```text
Charles Hudson: My view is that for product-market fit, finding a million dollars for most companies is sufficient.
```

The transcript ends before the Simplecast footer and cookie banner.

## Operational Notes

The Playwright managed headless shell failed in this environment, but full Chrome for Testing worked when passed through `--browser-executable`.

Navigation was more reliable with:

- `waitUntil: 'commit'`
- Explicit DOM wait for speaker labels
- Retry attempts around page creation/extraction

This is a prototype validation, not a Phase 2 reprocessing pass. The next step is to decide whether to fold Playwright retrieval into the main transcript ingestion workflow and then re-run audits before updating any episode intelligence records.
