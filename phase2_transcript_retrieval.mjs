#!/usr/bin/env node

import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

const PHASE2_EPISODES = [
  {
    episode: 25,
    slug: 'x-factor',
    url: 'https://podcast.sure.ventures/episodes/x-factor/transcript',
  },
  {
    episode: 26,
    slug: 'chief-engineer',
    url: 'https://podcast.sure.ventures/episodes/chief-engineer/transcript',
  },
  {
    episode: 34,
    slug: 'commerce',
    url: 'https://podcast.sure.ventures/episodes/commerce/transcript',
  },
  {
    episode: 50,
    slug: 'childhood-not-resume',
    url: 'https://podcast.sure.ventures/episodes/childhood-not-resume/transcript',
  },
  {
    episode: 51,
    slug: 'persuasive-fintech',
    url: 'https://podcast.sure.ventures/episodes/persuasive-fintech/transcript',
  },
  {
    episode: 53,
    slug: 'ubiquity',
    url: 'https://podcast.sure.ventures/episodes/ubiquity/transcript',
  },
  {
    episode: 54,
    slug: 'homebrew',
    url: 'https://podcast.sure.ventures/episodes/homebrew/transcript',
  },
  {
    episode: 55,
    slug: 'look-where-others-are-not-looking',
    url: 'https://podcast.sure.ventures/episodes/look-where-others-are-not-looking/transcript',
  },
  {
    episode: 60,
    slug: 'prioritize-cash-team-and-momentum-in-that-order',
    url: 'https://podcast.sure.ventures/episodes/prioritize-cash-team-and-momentum-in-that-order/transcript',
  },
  {
    episode: 63,
    slug: 'show-your-assumptions',
    url: 'https://podcast.sure.ventures/episodes/show-your-assumptions/transcript',
  },
  {
    episode: 70,
    slug: 'tsse70-cvcs-not-devil-patrick-counterpart',
    url: 'https://podcast.sure.ventures/episodes/tsse70-cvcs-not-devil-patrick-counterpart/transcript',
  },
  {
    episode: 73,
    slug: 'tsse73-pre-revenue-startups-charles-precursor',
    url: 'https://podcast.sure.ventures/episodes/tsse73-pre-revenue-startups-charles-precursor/transcript',
  },
  {
    episode: 74,
    slug: 'tsse74-business-with-gratitude-heather-humanvc',
    url: 'https://podcast.sure.ventures/episodes/tsse74-business-with-gratitude-heather-humanvc/transcript',
  },
  {
    episode: 75,
    slug: 'tsse75-fintech-startup-ideas-dan-rosen-commercevc',
    url: 'https://podcast.sure.ventures/episodes/tsse75-fintech-startup-ideas-dan-rosen-commercevc/transcript',
  },
  {
    episode: 79,
    slug: 'tsse79-sell-authentically-nuno-goncalves-chamaeleonvc',
    url: 'https://podcast.sure.ventures/episodes/tsse79-sell-authentically-nuno-goncalves-chamaeleonvc/transcript',
  },
];

const SPEAKER_PATTERN = /^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?[A-Z][A-Za-z .'\u00c0-\u017f-]+:/;
const METADATA_PATTERN = /^[A-Z]+ \d{1,2}(?:ST|ND|RD|TH), \d{4} \| /;

function parseArgs(argv) {
  const args = {
    browserExecutable: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || '',
    playwrightModulePath: process.env.PLAYWRIGHT_MODULE_PATH || '',
    outputDir: 'data/transcripts',
  };

  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--browser-executable') {
      args.browserExecutable = argv[++index];
    } else if (arg === '--playwright-module-path') {
      args.playwrightModulePath = argv[++index];
    } else if (arg === '--output-dir') {
      args.outputDir = argv[++index];
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
  console.log(`Usage: node phase2_transcript_retrieval.mjs [options]

Retrieves rendered transcript text for the 15 Phase 2 episodes.

Options:
  --output-dir <path>              Output transcript directory.
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
  const speakerMatches = [
    ...text.matchAll(/^(?:\[\d{2}:\d{2}:\d{2}\]\s*)?([A-Z][A-Za-z .'\u00c0-\u017f-]+):/gm),
  ];
  const speakers = [...new Set(speakerMatches.map((match) => match[1]))];
  const hasHtmlShell =
    text.includes('<!DOCTYPE html>') ||
    text.includes('<div id="app"></div>') ||
    text.includes('polyfills-legacy') ||
    text.includes('image.simplecastcdn.com/customersites/latest/assets');

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
      text.includes('Gopi Rangan:') &&
      !hasHtmlShell,
  };
}

async function extractEpisode(page, episodeData) {
  await page.goto(episodeData.url, { waitUntil: 'commit', timeout: 90000 });
  await page.waitForFunction(
    () =>
      document.body &&
      document.body.innerText.includes('Gopi Rangan:') &&
      document.body.innerText.length > 8000,
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
  const { chromium } = await loadPlaywright(args.playwrightModulePath);
  const launchOptions = { headless: true };

  if (args.browserExecutable) {
    launchOptions.executablePath = args.browserExecutable;
  }

  const browser = await chromium.launch(launchOptions);
  const results = [];

  try {
    for (const episodeData of PHASE2_EPISODES) {
      const { text, validation, attempts } = await extractWithRetries(browser, episodeData);
      const outputPath = resolve(args.outputDir, `${episodeData.slug}_transcript.txt`);
      await mkdir(dirname(outputPath), { recursive: true });
      await writeFile(outputPath, text, 'utf8');
      results.push({
        episode: episodeData.episode,
        sourceUrl: episodeData.url,
        outputPath,
        attempts,
        validation,
      });
      console.log(`Episode ${episodeData.episode} saved: ${outputPath}`);
    }
  } finally {
    await browser.close();
  }

  console.log(JSON.stringify({ total: results.length, results }, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
