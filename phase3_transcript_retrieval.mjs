#!/usr/bin/env node

import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

const SPEAKER_PATTERN = /^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?[A-Z][A-Za-z .'\u00c0-\u017f-]+:/;
const SPEAKER_MATCH_PATTERN =
  /^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?([A-Z][A-Za-z .'\u00c0-\u017f-]+):/gm;
const METADATA_PATTERN = /^[A-Z]+ \d{1,2}(?:ST|ND|RD|TH), \d{4} \| /;
const SHELL_MARKERS = [
  '<!DOCTYPE html>',
  '<div id="app"></div>',
  'polyfills-legacy',
  'image.simplecastcdn.com/customersites/latest/assets',
];

function parseArgs(argv) {
  const args = {
    browserExecutable: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || '',
    playwrightModulePath: process.env.PLAYWRIGHT_MODULE_PATH || '',
    rankingsPath: 'data/guest_rankings.csv',
    recordsDir: 'data/episodes/rank4',
    outputDir: 'data/transcripts',
    includeExisting: false,
    episodes: null,
    episodeNumber: null,
    episodeUrl: '',
    guestName: '',
  };

  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--browser-executable') {
      args.browserExecutable = argv[++index];
    } else if (arg === '--playwright-module-path') {
      args.playwrightModulePath = argv[++index];
    } else if (arg === '--rankings-path') {
      args.rankingsPath = argv[++index];
    } else if (arg === '--records-dir') {
      args.recordsDir = argv[++index];
    } else if (arg === '--output-dir') {
      args.outputDir = argv[++index];
    } else if (arg === '--include-existing') {
      args.includeExisting = true;
    } else if (arg === '--episodes') {
      args.episodes = argv[++index]
        .split(',')
        .map((episode) => Number.parseInt(episode.trim(), 10))
        .filter(Number.isFinite);
    } else if (arg === '--episode-number') {
      args.episodeNumber = Number.parseInt(argv[++index], 10);
    } else if (arg === '--episode-url') {
      args.episodeUrl = argv[++index];
    } else if (arg === '--guest-name') {
      args.guestName = argv[++index];
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return args;
}

function printHelp() {
  console.log(`Usage: node phase3_transcript_retrieval.mjs [options]

Retrieves rendered transcript text for remaining Rank 4 Phase 3 episodes.

Options:
  --output-dir <path>              Output transcript directory.
  --rankings-path <path>           Guest rankings TSV path.
  --records-dir <path>             Rank 4 JSON records directory.
  --episodes <list>                Comma-separated episode numbers to retrieve.
  --episode-number <number>        Single episode number for direct URL retrieval.
  --episode-url <url>              Single episode or transcript URL to retrieve.
  --guest-name <name>              Optional guest name for direct URL retrieval.
  --include-existing               Include episodes that already have JSON records.
  --browser-executable <path>      Optional Chromium/Chrome executable path.
  --playwright-module-path <path>  Optional Playwright module path.
  -h, --help                       Show this help.
`);
}

async function loadPlaywright(modulePath) {
  const candidates = [modulePath, 'playwright'].filter(Boolean);
  const errors = [];

  for (const candidate of candidates) {
    try {
      const imported = await import(candidate);
      return imported.chromium ? imported : imported.default;
    } catch (error) {
      errors.push(`${candidate}: ${error.message}`);
    }
  }

  throw new Error(
    'Unable to import Playwright. Install playwright or pass --playwright-module-path.\n' +
      errors.join('\n')
  );
}

function parseTsv(text) {
  const [headerLine, ...lines] = text.split(/\r?\n/).filter(Boolean);
  const headers = headerLine.split('\t');
  return lines.map((line) => {
    const values = line.split('\t');
    return Object.fromEntries(headers.map((header, index) => [header, values[index] || '']));
  });
}

function slugFromEpisodeUrl(url) {
  const parsed = new URL(url);
  const parts = parsed.pathname.split('/').filter(Boolean);
  const episodeIndex = parts.indexOf('episodes');
  return episodeIndex === -1 ? parts.at(-1) : parts[episodeIndex + 1];
}

function deriveTranscriptUrl(url) {
  return url.endsWith('/transcript') ? url : `${url.replace(/\/$/, '')}/transcript`;
}

async function loadTargetEpisodes(args) {
  if (args.episodeUrl) {
    if (!Number.isFinite(args.episodeNumber)) {
      throw new Error('--episode-number is required when --episode-url is used.');
    }

    const episodeUrl = args.episodeUrl.replace(/\/transcript\/?$/, '');
    return {
      targets: [
        {
          episode: args.episodeNumber,
          guestName: args.guestName,
          episodeUrl,
          transcriptUrl: deriveTranscriptUrl(episodeUrl),
          slug: slugFromEpisodeUrl(episodeUrl),
        },
      ],
      skipped: [],
      existingEpisodes: [],
    };
  }

  const rankings = parseTsv(await readFile(args.rankingsPath, 'utf8'));
  const recordFiles = await readdir(args.recordsDir).catch(() => []);
  const existingEpisodes = new Set(
    recordFiles
      .map((file) => file.match(/^episode_(\d+)\.json$/)?.[1])
      .filter(Boolean)
      .map(Number)
  );
  const requestedEpisodes = args.episodes ? new Set(args.episodes) : null;
  const skipped = [];
  const targets = [];

  for (const row of rankings) {
    if (row['GUEST RANK'] !== '4') continue;

    const episode = Number.parseInt(row['EPISODE NO.'], 10);
    if (requestedEpisodes && !requestedEpisodes.has(episode)) continue;
    if (!args.includeExisting && existingEpisodes.has(episode)) continue;

    if (!row.URL) {
      skipped.push({
        episode,
        guestName: row['GUEST NAME'],
        reason: 'missing_episode_url',
      });
      continue;
    }

    const slug = slugFromEpisodeUrl(row.URL);
    targets.push({
      episode,
      guestName: row['GUEST NAME'],
      episodeUrl: row.URL,
      transcriptUrl: deriveTranscriptUrl(row.URL),
      slug,
    });
  }

  return { targets, skipped, existingEpisodes: [...existingEpisodes].sort((a, b) => a - b) };
}

function selectTranscriptParagraphs(paragraphs) {
  const metadataIndex = paragraphs.findIndex((paragraph) => METADATA_PATTERN.test(paragraph));
  const firstSpeakerIndex = paragraphs.findIndex((paragraph) =>
    SPEAKER_PATTERN.test(paragraph)
  );
  const footerIndex = paragraphs.findIndex((paragraph) =>
    paragraph.startsWith('Podcast powered by Simplecast')
  );

  if (firstSpeakerIndex === -1) {
    throw new Error('Could not locate the first speaker-labeled transcript paragraph.');
  }

  const firstTranscriptIndex =
    metadataIndex !== -1 && metadataIndex < firstSpeakerIndex
      ? metadataIndex + 1
      : firstSpeakerIndex;

  return paragraphs.slice(
    firstTranscriptIndex,
    footerIndex === -1 ? undefined : footerIndex
  );
}

function validateTranscript(text) {
  const byteLength = Buffer.byteLength(text, 'utf8');
  const speakerMatches = [...text.matchAll(SPEAKER_MATCH_PATTERN)];
  const speakers = [...new Set(speakerMatches.map((match) => match[1]))];
  const hasHtmlShell = SHELL_MARKERS.some((marker) => text.includes(marker));

  return {
    byteLength,
    characterLength: text.length,
    paragraphCount: text.split(/\n{2,}/).filter(Boolean).length,
    speakers,
    hasHost: text.includes('Gopi Rangan:'),
    hasHtmlShell,
    valid:
      byteLength > 10000 &&
      speakers.length >= 2 &&
      !hasHtmlShell,
  };
}

async function extractEpisode(page, episodeData) {
  await page.goto(episodeData.transcriptUrl, { waitUntil: 'commit', timeout: 90000 });
  await page.waitForFunction(
    () =>
      document.body &&
      document.body.innerText.length > 8000 &&
      [...document.querySelectorAll('p')].some((element) =>
        /^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?[A-Z][A-Za-z .'\u00c0-\u017f-]+:/.test(
          element.innerText.trim()
        )
      ),
    null,
    { timeout: 90000 }
  );

  const paragraphs = await page.$$eval('p', (elements) =>
    elements.map((element) => element.innerText.trim()).filter(Boolean)
  );
  const transcriptParagraphs = selectTranscriptParagraphs(paragraphs);
  const text = transcriptParagraphs.join('\n\n').trim() + '\n';
  const validation = validateTranscript(text);

  if (!validation.valid) {
    throw new Error(`Validation failed: ${JSON.stringify(validation)}`);
  }

  return { text, validation };
}

async function extractWithRetries(browser, episodeData) {
  let lastError = null;

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    try {
      const result = await extractEpisode(page, episodeData);
      return { ...result, attempts: attempt };
    } catch (error) {
      lastError = error;
      console.error(`Episode ${episodeData.episode} attempt ${attempt} failed: ${error.message}`);
    } finally {
      await page.close();
    }
  }

  throw lastError || new Error(`Episode ${episodeData.episode} extraction failed.`);
}

async function main() {
  const args = parseArgs(process.argv);
  const { targets, skipped, existingEpisodes } = await loadTargetEpisodes(args);
  const { chromium } = await loadPlaywright(args.playwrightModulePath);
  const launchOptions = { headless: true };

  if (args.browserExecutable) {
    launchOptions.executablePath = args.browserExecutable;
  }

  const browser = await chromium.launch(launchOptions);
  const results = [];
  const failures = [];

  try {
    for (const episodeData of targets) {
      try {
        const { text, validation, attempts } = await extractWithRetries(browser, episodeData);
        const outputPath = resolve(args.outputDir, `${episodeData.slug}_transcript.txt`);
        await mkdir(dirname(outputPath), { recursive: true });
        await writeFile(outputPath, text, 'utf8');
        results.push({
          episode: episodeData.episode,
          guestName: episodeData.guestName,
          episodeUrl: episodeData.episodeUrl,
          transcriptUrl: episodeData.transcriptUrl,
          outputPath,
          attempts,
          validation,
        });
        console.log(`Episode ${episodeData.episode} saved: ${outputPath}`);
      } catch (error) {
        failures.push({
          episode: episodeData.episode,
          guestName: episodeData.guestName,
          transcriptUrl: episodeData.transcriptUrl,
          error: error.message,
        });
      }
    }
  } finally {
    await browser.close();
  }

  console.log(
    JSON.stringify(
      {
        totalTargets: targets.length,
        existingEpisodes,
        retrieved: results.length,
        skipped,
        failures,
        results,
      },
      null,
      2
    )
  );

  if (failures.length > 0) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
