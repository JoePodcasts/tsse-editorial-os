// Run inside Codex's cua_repl, passing its documented tab and viewport handles.
// No separate browser driver or runtime dependency is installed.
import {createHash} from 'node:crypto';

export async function runArchiveChecks(tab, viewport, base = 'http://127.0.0.1:8765') {
  const checks = [];
  function check(name, passed, evidence) {
    checks.push({name, passed: Boolean(passed), evidence});
    if (!passed) throw new Error(name + ': ' + JSON.stringify(evidence));
  }
  const view = () => tab.playwright.evaluate(() => [...document.querySelectorAll('.result')].map(n => ({
    number: n.closest('.episode-result').querySelector('.episode-number').textContent, source: n.dataset.source,
    text: n.querySelector('.excerpt').textContent, time: n.querySelector('.timestamp')?.textContent,
    speaker: n.querySelector('.source-speaker')?.textContent, pid: n.dataset.passage,
    href: n.querySelector('.text-link').getAttribute('href')
  })));
  const search = async q => {
    await tab.playwright.getByRole('searchbox', {name: 'Search the archive'}).fill(q);
    await tab.playwright.getByRole('searchbox', {name: 'Search the archive'}).press('Enter');
    await tab.playwright.locator('.results-heading').filter({hasText: 'source matches for “' + q + '”'}).waitFor({state: 'visible'});
    return view();
  };
  const sourceFidelity = async () => {
    const data = await tab.playwright.evaluate(() => ({
      text: [...document.querySelector('.reading').children].map(n => n.classList.contains('passage')
        ? n.querySelector('.passage-text').textContent : n.textContent).join(''),
      provenance: JSON.parse(document.querySelector('.reading-column > details pre').textContent),
      unsafeElements: document.querySelectorAll('.reading img,.reading iframe,.reading script').length
    }));
    const expected = (data.provenance.source || data.provenance).derived_text.sha256;
    const actual = createHash('sha256').update(data.text).digest('hex');
    return {expected, actual, unsafeElements: data.unsafeElements};
  };
  const noOverflow = () => tab.playwright.evaluate(() => ({width: innerWidth, pageWidth: document.documentElement.scrollWidth}));
  const back = async () => { await tab.playwright.locator('main > .back').click(); };

  await viewport.set({width: 1366, height: 900});
  if (await tab.url() === base + '/') await tab.reload();
  else await tab.goto(base + '/');
  await tab.playwright.locator('.browse-row').first().waitFor({state: 'visible'});
  const coverage = await tab.playwright.locator('.coverage').innerText();
  check('Live archive coverage', coverage.includes('195 episodes') && coverage.includes('195 transcripts') && coverage.includes('195 published show notes'), coverage);
  check('Newest-first browse', (await tab.playwright.locator('.browse-row').first().innerText()).includes('195'));
  await tab.playwright.getByRole('combobox', {name: 'Sort by'}).selectOption('oldest');
  await tab.playwright.getByRole('link', {name: /EP\. 01 Welcome and quick intro/}).waitFor({state: 'visible'});
  check('Oldest-first browse', (await tab.playwright.locator('.browse-row').first().innerText()).includes('Welcome and quick intro'));
  for (let loaded = 24; loaded < 195; loaded += 24) {
    await tab.playwright.getByRole('button', {name: 'Load more episodes', exact: false}).click();
    await tab.playwright.getByText(`Showing ${Math.min(loaded + 24, 195)} of 195 episodes`, {exact: true}).waitFor({state: 'visible'});
  }
  const browse = await tab.playwright.evaluate(() => ({count: document.querySelectorAll('.browse-row').length,
    unique: new Set([...document.querySelectorAll('.browse-row')].map(n => n.href)).size}));
  check('Browse all 195 without duplicates', browse.count === 195 && browse.unique === 195, browse);

  let rows = await search('proof of value');
  check('Official title result: episode 195', rows.some(r => r.number === 'EP.195' && r.source === 'episode_title'), rows[0]);
  check('Unified source-type rendering', ['episode_title', 'show_notes', 'transcript'].every(source => rows.some(r => r.source === source)));
  rows = await search('Gokul Rajaram');
  check('Source-speaker metadata result: episode 2', rows.some(r => r.number === 'EP.02' && r.source === 'speaker_labels'), rows[0]);
  await tab.playwright.locator('.result[data-source="speaker_labels"] .text-link').click();
  await tab.playwright.locator('.metadata-match').waitFor({state: 'visible'});
  check('Metadata result opens episode and discloses speaker limitation', (await tab.playwright.locator('.metadata-match').innerText()).includes('not been verified against audio'));
  await back();
  await search('Commerce Ventures');
  await tab.playwright.getByRole('link', {name: 'Show notes', exact: true}).click();
  await tab.playwright.locator('.filter.active').filter({hasText: 'Show notes'}).waitFor({state: 'visible'});
  rows = await view();
  const notes = rows.find(r => r.number === 'EP.75');
  check('Published show-note result: episode 75', notes?.source === 'show_notes', notes);
  await tab.playwright.locator(`.result[data-passage="${notes.pid}"] .text-link`).click();
  await tab.playwright.locator('.passage.selected').waitFor({state: 'visible'});
  check('Notes deep link selects its passage ID', (await tab.playwright.locator('.passage.selected').getAttribute('data-passage')) === notes.pid);
  const safeNotes = await sourceFidelity();
  check('Full notes preserve projection and render no source HTML', safeNotes.actual === safeNotes.expected && safeNotes.unsafeElements === 0, safeNotes);
  await back();
  await search('relentlessly resourceful');
  await tab.playwright.getByRole('link', {name: 'Transcripts', exact: true}).click();
  await tab.playwright.locator('.filter.active').filter({hasText: 'Transcripts'}).waitFor({state: 'visible'});
  rows = await view();
  const older = rows.find(r => r.number === 'EP.02' && r.time === '00:12:34');
  check('Older transcript result: episode 2 at 00:12:34', Boolean(older), older);
  await tab.playwright.locator(`.result[data-passage="${older.pid}"] .text-link`).click();
  await tab.playwright.locator('.passage.selected').waitFor({state: 'visible'});
  const before = await tab.playwright.locator('.passage.selected .passage-text').textContent();
  check('Transcript deep link selects exact passage ID', (await tab.playwright.locator('.passage.selected').getAttribute('data-passage')) === older.pid);
  await tab.reload();
  await tab.playwright.locator('.passage.selected').waitFor({state: 'visible'});
  check('Direct reload retains source text and passage identity', (await tab.playwright.locator('.passage.selected .passage-text').textContent()) === before && (await tab.playwright.locator('.passage.selected').getAttribute('data-passage')) === older.pid);
  const safeTranscript = await sourceFidelity();
  check('Full transcript DOM matches source projection hash', safeTranscript.actual === safeTranscript.expected, safeTranscript);
  await back();
  rows = await search('choosing a partner in life');
  const recent = rows.find(r => r.number === 'EP.191' && r.time === '00:23:15');
  check('Recent transcript result: episode 191 with time and source speaker', recent?.speaker === 'Justin Smith-Lorenzetti', recent);
  await tab.playwright.locator(`.result[data-passage="${recent.pid}"] .text-link`).click();
  await tab.playwright.locator('.passage.selected').waitFor({state: 'visible'});
  const deepURL = await tab.url();
  check('Recent transcript opens highlighted source context', (await tab.playwright.locator('.passage.selected').innerText()).includes('choosing a partner in life'));
  await tab.playwright.getByRole('textbox', {name: 'Search this episode', exact: true}).fill('partner');
  await tab.playwright.getByRole('textbox', {name: 'Search this episode', exact: true}).press('Enter');
  await tab.playwright.getByText(/source matches for “partner”/).waitFor({state: 'visible'});
  rows = await view();
  check('Search this episode restricts actual retrieval', rows.length > 0 && rows.every(r => r.number === 'EP.191'), {matches: rows.length});
  await search('<img src=x onerror=alert(1)>NoSuchArchiveToken9ZZZZ');
  await tab.playwright.getByRole('heading', {name: 'No matching sources'}).waitFor({state: 'visible'});
  const noResults = await tab.playwright.evaluate(() => ({unsafe: document.querySelectorAll('main img,main iframe,main script').length,
    heading: document.querySelector('.results-heading').textContent}));
  check('No-results state and HTML-like input are safe text', noResults.unsafe === 0 && noResults.heading.includes('<img'), noResults);

  await tab.goto(base + '/episodes/74/transcript');
  await tab.playwright.locator('.reading').waitFor({state: 'visible'});
  const untimed = await tab.playwright.evaluate(() => ({note: [...document.querySelectorAll('.source-note')].map(n => n.textContent).join(' '),
    times: [...document.querySelectorAll('.passage .anchor')].filter(n => n.textContent.includes(':')).length,
    speakers: [...document.querySelectorAll('.speaker')].slice(0, 3).map(n => n.textContent)}));
  check('Untimed transcript shows no invented timestamps', untimed.times === 0 && untimed.note.includes('does not contain timestamps'), untimed);
  check('Source speaker labels remain intact', untimed.speakers.includes('Heather Hartnett:'), untimed.speakers);
  await tab.goto(base + '/episodes/2/transcript?passage=' + '0'.repeat(64));
  await tab.playwright.locator('.error').waitFor({state: 'visible'});
  check('Stale passage gets a useful recovery path', (await tab.playwright.locator('.error').innerText()).includes('no longer in the current index') && await tab.playwright.getByRole('link', {name: 'Open the full source without this passage', exact: false}).isVisible());

  await viewport.set({width: 375, height: 812});
  await tab.goto(base + '/');
  await tab.playwright.locator('.browse-row').first().waitFor({state: 'visible'});
  const mobileHome = await noOverflow();
  check('375px home has no horizontal overflow', mobileHome.pageWidth <= mobileHome.width, mobileHome);
  await search('choosing a partner in life');
  const mobileResults = await noOverflow();
  check('375px search has no horizontal overflow', mobileResults.pageWidth <= mobileResults.width, mobileResults);
  await tab.playwright.locator(`.result[data-passage="${recent.pid}"] .text-link`).click();
  await tab.playwright.locator('.passage.selected').waitFor({state: 'visible'});
  const mobileReader = await noOverflow();
  check('375px transcript has no horizontal overflow', mobileReader.pageWidth <= mobileReader.width, mobileReader);
  await viewport.set({width: 768, height: 1024});
  await tab.reload();
  await tab.playwright.locator('.passage.selected').waitFor({state: 'visible'});
  const tablet = await noOverflow();
  check('768px reader has no horizontal overflow', tablet.pageWidth <= tablet.width, tablet);
  await viewport.set({width: 1366, height: 900});
  await tab.reload();
  await tab.playwright.locator('.passage.selected').waitFor({state: 'visible'});
  const desktop = await noOverflow();
  check('1366px reader has no horizontal overflow', desktop.pageWidth <= desktop.width, desktop);
  const logs = await tab.dev.logs({levels: ['error', 'warn'], limit: 50});
  check('No browser console errors or warnings', logs.length === 0, logs);
  return {checked_at: new Date().toISOString(), checks, passed: checks.every(c => c.passed), deepURL};
}
