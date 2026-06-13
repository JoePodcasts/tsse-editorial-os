#!/usr/bin/env node

import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

const EPISODE_73_TRANSCRIPT_URL =
  'https://podcast.sure.ventures/episodes/tsse73-pre-revenue-startups-charles-precursor/transcript';

const DEFAULT_OUTPUT =
  'data/transcripts/tsse73-pre-revenue-startups-charles-precursor_transcript.txt';

const REQUIRED_SPEAKERS = ['Charles Hudson:', 'Gopi Rangan:'];

function parseArgs(argv) {
  const args = {
    output: DEFAULT_OUTPUT,
    browserExecutable: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || '',
    playwrightModulePath: process.env.PLAYWRIGHT_MODULE_PATH || '',
  };

  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--output') {
      args.output = argv[++index];
    } else if (arg === '--browser-executable') {
      args.browserExecutable = argv[++index];
    } else if (arg === '--playwright-module-path') {
      args.playwrightModulePath = argv[++index];
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
  console.log(`Usage: node playwright_transcript_retrieval.mjs [options]

Retrieves the rendered transcript text for Episode 73 only.

Options:
  --output <path>                  Output transcript path.
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
      return await import(candidate);
    } catch (error) {
      errors.push(`${candidate}: ${error.message}`);
    }
  }

  throw new Error(
    'Unable to import Playwright. Install playwright or pass --playwright-module-path.\n' +
      errors.join('\n')
  );
}

async function extractTranscript(page) {
  await page.goto(EPISODE_73_TRANSCRIPT_URL, {
    waitUntil: 'commit',
    timeout: 90000,
  });

  await page.waitForFunction(
    (speakers) =>
      document.body &&
      speakers.every((speaker) => document.body.innerText.includes(speaker)),
    REQUIRED_SPEAKERS,
    { timeout: 60000 }
  );

  const paragraphs = await page.$$eval('p', (elements) =>
    elements.map((element) => element.innerText.trim()).filter(Boolean)
  );

  const firstTranscriptIndex = paragraphs.findIndex((paragraph) =>
    paragraph.startsWith('Charles Hudson:')
  );
  const footerIndex = paragraphs.findIndex((paragraph) =>
    paragraph.startsWith('Podcast powered by Simplecast')
  );

  if (firstTranscriptIndex === -1) {
    throw new Error('Could not locate the first Episode 73 transcript paragraph.');
  }

  const transcriptParagraphs = paragraphs.slice(
    firstTranscriptIndex,
    footerIndex === -1 ? undefined : footerIndex
  );

  return transcriptParagraphs.join('\n\n').trim() + '\n';
}

function validateTranscript(transcriptText) {
  const byteLength = Buffer.byteLength(transcriptText, 'utf8');
  const missingSpeakers = REQUIRED_SPEAKERS.filter(
    (speaker) => !transcriptText.includes(speaker)
  );
  const hasHtmlShell =
    transcriptText.includes('<!DOCTYPE html>') ||
    transcriptText.includes('<div id="app"></div>') ||
    transcriptText.includes('index-') ||
    transcriptText.includes('polyfills-legacy');

  return {
    byteLength,
    characterLength: transcriptText.length,
    paragraphCount: transcriptText.split(/\n{2,}/).filter(Boolean).length,
    missingSpeakers,
    hasHtmlShell,
    valid:
      byteLength > 10000 &&
      !hasHtmlShell &&
      missingSpeakers.length === 0 &&
      transcriptText.includes('product-market fit'),
  };
}

async function main() {
  const args = parseArgs(process.argv);
  const { chromium } = await loadPlaywright(args.playwrightModulePath);
  const launchOptions = { headless: true };

  if (args.browserExecutable) {
    launchOptions.executablePath = args.browserExecutable;
  }

  const browser = await chromium.launch(launchOptions);
  try {
    let transcriptText = '';
    let lastError = null;

    for (let attempt = 1; attempt <= 3; attempt += 1) {
      const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
      try {
        transcriptText = await extractTranscript(page);
        break;
      } catch (error) {
        lastError = error;
        console.error(`Attempt ${attempt} failed: ${error.message}`);
      } finally {
        await page.close();
      }
    }

    if (!transcriptText) {
      throw lastError || new Error('Transcript extraction failed.');
    }

    const validation = validateTranscript(transcriptText);

    if (!validation.valid) {
      throw new Error(`Transcript validation failed: ${JSON.stringify(validation)}`);
    }

    const outputPath = resolve(args.output);
    await mkdir(dirname(outputPath), { recursive: true });
    await writeFile(outputPath, transcriptText, 'utf8');

    console.log(
      JSON.stringify(
        {
          episode: 73,
          sourceUrl: EPISODE_73_TRANSCRIPT_URL,
          outputPath,
          validation,
        },
        null,
        2
      )
    );
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
