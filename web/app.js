'use strict';

// All source text enters the DOM through text nodes. No source HTML is rendered.
const main = document.querySelector('#main');
const announcer = document.querySelector('#announcer');
let navigation = 0;
let lastArchive = '/';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}
function link(text, href, className = '') {
  const node = el('a', className, text);
  node.href = href;
  return node;
}
function download(text, href, className = 'text-link') {
  const node = link(text, href, className); node.setAttribute('download', ''); return node;
}
function fileSize(bytes) {
  return bytes >= 1048576 ? `${(bytes / 1048576).toFixed(2)} MiB` : `${Math.ceil(bytes / 1024)} KiB`;
}
function searchOrigin(value = new URL(location.href).searchParams.get('return')) {
  if (!value || !value.startsWith('/?')) return null;
  try {
    const url = new URL(value, location.origin);
    if (url.origin !== location.origin || url.pathname !== '/' || !url.searchParams.get('q') || url.searchParams.get('q').length > 300) return null;
    return {url: url.pathname + url.search, query: url.searchParams.get('q')};
  } catch (_) { return null; }
}
function withReturn(href, origin = searchOrigin()) {
  if (!origin) return href;
  const target = new URL(href, location.origin);
  target.searchParams.set('return', origin.url);
  return target.pathname + target.search + target.hash;
}
function safeExternal(text, href, className = '') {
  try {
    const url = new URL(href);
    if (!['https:', 'http:'].includes(url.protocol)) return el('span', className, text);
    const node = link(text, url.href, className);
    node.target = '_blank'; node.rel = 'noopener noreferrer';
    return node;
  } catch (_) { return el('span', className, text); }
}
function date(value) {
  if (!value) return 'Date unavailable';
  // Keep the source's publication calendar date, independent of browser timezone.
  const parsed = new Date(value.slice(0, 10) + 'T12:00:00Z');
  return Number.isNaN(parsed.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat('en', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'
  }).format(parsed);
}
function duration(seconds) {
  if (!Number.isFinite(seconds)) return 'Duration unavailable';
  const minutes = Math.floor(seconds / 60), hours = Math.floor(minutes / 60);
  return hours ? `${hours}h ${minutes % 60}m` : `${minutes} min`;
}
function number(value) { return value === null || value === undefined ? '—' : String(value).padStart(2, '0'); }
function episodeNumber(value) {
  const node = el('div', 'episode-number', 'EP.');
  node.append(el('strong', '', number(value)));
  return node;
}
function provenance(data, title = 'Source details') {
  const disclosure = el('details');
  disclosure.append(el('summary', '', title), el('pre', 'provenance', JSON.stringify(data, null, 2)));
  return disclosure;
}
function errorView(error, parent = main) {
  const box = el('div', 'error');
  box.setAttribute('role', 'alert');
  box.append(el('p', '', error.message || 'This view could not be loaded. Please try again.'));
  parent.append(box);
  announcer.textContent = box.textContent;
}
async function api(path) {
  const response = await fetch(path, {headers: {Accept: 'application/json'}});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
  return data;
}
function archiveURL(params) {
  const query = new URLSearchParams(params);
  for (const [key, value] of [...query]) if (!value || (key === 'source' && value === 'all')) query.delete(key);
  return '/' + (query.size ? '?' + query : '');
}
function navigate(href, replace = false) {
  history[replace ? 'replaceState' : 'pushState']({}, '', href);
  render();
}
document.addEventListener('click', event => {
  const anchor = event.target.closest('a');
  if (!anchor || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey ||
      event.shiftKey || event.altKey || anchor.target || anchor.hasAttribute('download')) return;
  const url = new URL(anchor.href);
  if (url.origin !== location.origin || anchor.getAttribute('href').startsWith('#')) return;
  event.preventDefault();
  navigate(url.pathname + url.search + url.hash);
});
window.addEventListener('popstate', render);

function searchForm(params) {
  const form = el('form', 'search-box');
  form.setAttribute('role', 'search'); form.action = '/';
  const label = el('label', 'sr-only', 'Search the archive'); label.htmlFor = 'archive-query';
  const icon = el('span', 'search-icon'); icon.setAttribute('aria-hidden', 'true');
  const input = el('input'); input.id = 'archive-query'; input.name = 'q'; input.type = 'search';
  input.placeholder = 'Search guests, companies, topics, transcripts…';
  input.value = params.get('q') || ''; input.maxLength = 300;
  const button = el('button', '', 'Search'); button.type = 'submit';
  button.append(el('span', '', '→'));
  form.append(label, icon, input, button);
  form.addEventListener('submit', event => {
    event.preventDefault();
    const q = input.value.trim();
    navigate(archiveURL({q, source: params.get('source') || 'all', episode: params.get('episode') || ''}));
  });
  return form;
}
function coverageView(data) {
  const node = el('div', 'coverage');
  node.append(el('span', 'dot'));
  [`${data.episodes} episodes`, `${data.transcript} transcripts`, `${data.show_notes} published show notes`].forEach((text, i) => {
    if (i) node.append(el('span', 'sep', '·'));
    node.append(el('span', 'count', text));
  });
  return node;
}
function syncStatus(data) {
  const node = el('p', 'sync-status');
  node.setAttribute('aria-label', 'Archive synchronization status');
  if (!data || data.status !== 'success') {
    node.textContent = 'Last successful sync not yet recorded.';
    return node;
  }
  const instant = new Date(data.last_successful_sync_at);
  if (Number.isNaN(instant.getTime())) return node;
  const day = new Intl.DateTimeFormat('en-US', {timeZone: 'America/Los_Angeles',
    month: 'short', day: 'numeric', year: 'numeric'}).format(instant);
  const time = new Intl.DateTimeFormat('en-US', {timeZone: 'America/Los_Angeles',
    hour: 'numeric', minute: '2-digit', hour12: true}).format(instant);
  node.append(document.createTextNode('Last successful sync '));
  const stamp = el('time', '', `${day} · ${time} PT`);
  stamp.dateTime = data.last_successful_sync_at; node.append(stamp);
  // A weekly check with two days of grace; never claim continuous freshness.
  if (Date.now() - instant.getTime() > 9 * 86400000) node.append(document.createTextNode(' · Weekly check overdue'));
  return node;
}
function filesEntry(data) {
  const entry = link('', '/archive-files', 'files-entry');
  entry.append(el('strong', '', 'Archive files'), el('span', '', `CSV catalogue · ${data.markdown_files} Markdown episode files`), el('span', 'text-link', 'View archive files →'));
  return entry;
}
async function archiveView(params, ticket) {
  lastArchive = location.pathname + location.search;
  document.title = params.get('q') ? `${params.get('q')} · TSSE Archive` : 'Content Archive · The Sure Shot Entrepreneur';
  const hero = el('section', 'hero' + (params.get('q') ? ' search-mode' : ''));
  hero.append(el('span', 'eyebrow', 'The Sure Shot Entrepreneur'), el('h1', '', 'Content Archive'),
    el('p', 'intro', 'Search episodes, transcripts and published show notes.'), el('span', 'hero-index', 'An archive of entrepreneurial thinking'));
  main.append(hero);
  if (params.get('episode')) {
    const scope = el('div', 'scope');
    scope.append(el('span', '', `Searching within episode ${params.get('episode')}`),
      link('Search whole archive ↗', archiveURL({q: params.get('q') || '', source: params.get('source') || 'all'})));
    main.append(scope);
  }
  main.append(searchForm(params));
  const stats = el('div'); main.append(stats);
  const body = el('section'); main.append(body);
  body.append(el('p', 'loading', 'Loading archive…'));
  try {
    const coveragePromise = Promise.all([api('/api/archive'), api('/api/sync-status')]).then(([data, status]) => {
      if (ticket === navigation) stats.replaceChildren(coverageView(data), filesEntry(data), syncStatus(status.sync));
    });
    const load = params.get('q') ? searchView(params, body, ticket) : browseView(params, body, ticket);
    await Promise.all([coveragePromise, load]);
  } catch (error) { if (ticket === navigation) { body.replaceChildren(); errorView(error, body); } }
}

function browseRow(record, files = false) {
  if (files) {
    const row = el('div', 'file-row');
    const middle = el('div');
    const title = el('h3', 'browse-title'); title.append(link(record.official_title, record.file.url));
    middle.append(title, el('p', 'source-hint', `Markdown · UTF-8 · ${fileSize(record.file.bytes)}`));
    const actions = el('div', 'file-row-actions');
    actions.append(link('View file →', record.file.url, 'text-link'), download('Download .md ↓', record.file.download_url));
    row.append(episodeNumber(record.episode_number), middle, el('span', 'browse-date', date(record.published_at)), actions);
    return row;
  }
  const row = link('', record.url, 'browse-row');
  row.append(episodeNumber(record.episode_number));
  const middle = el('div'); middle.append(el('h3', 'browse-title', record.official_title));
  const sources = el('div', 'source-hint');
  if (record.sources.transcript.available) sources.append(el('span', '', 'Transcript'));
  if (record.sources.show_notes.available) sources.append(el('span', '', 'Published show notes'));
  middle.append(sources);
  row.append(middle, el('span', 'browse-date', date(record.published_at)), el('span', 'arrow', '↗'));
  return row;
}
async function browseView(params, body, ticket, files = false) {
  const sort = params.get('sort') || 'newest';
  const data = await api('/api/episodes?' + new URLSearchParams({sort}));
  if (ticket !== navigation) return;
  body.replaceChildren();
  const toolbar = el('div', 'toolbar');
  const title = el('h2', '', files ? 'Episode files' : 'All episodes');
  const wrap = el('div', 'select-wrap');
  const label = el('label', '', 'Sort by'); label.htmlFor = 'sort';
  const select = el('select'); select.id = 'sort';
  for (const [value, text] of [['newest', 'Newest first'], ['oldest', 'Oldest first'], ['number', 'Episode number']]) {
    const option = el('option', '', text); option.value = value; select.append(option);
  }
  select.value = sort;
  select.addEventListener('change', () => navigate(files ? '/archive-files/episodes?sort=' + select.value : archiveURL({sort: select.value})));
  wrap.append(label, select); toolbar.append(title, wrap); body.append(toolbar);
  const list = el('div', 'episode-list'); body.append(list);
  list.append(...data.episodes.map(record => browseRow(record, files)));
  let loaded = data.episodes.length;
  const bottom = el('div', 'list-bottom');
  const status = el('span', 'subtle', `Showing ${loaded} of ${data.total} episodes`);
  const more = el('button', 'secondary', 'Load more episodes ↓'); more.type = 'button';
  if (loaded < data.total) bottom.append(status, more); else bottom.append(status);
  body.append(bottom);
  more.addEventListener('click', async () => {
    more.disabled = true;
    try {
      const next = await api('/api/episodes?' + new URLSearchParams({sort, offset: loaded}));
      if (ticket !== navigation) return;
      const rows = next.episodes.map(record => browseRow(record, files)); list.append(...rows);
      loaded += rows.length;
      status.textContent = `Showing ${loaded} of ${next.total} episodes`;
      if (loaded >= next.total) more.remove();
      (files ? rows[0]?.querySelector('a') : rows[0])?.focus();
      announcer.textContent = status.textContent;
    } catch (error) { if (ticket === navigation) errorView(error, bottom); }
    finally { more.disabled = false; }
  });
  announcer.textContent = `${data.total} episodes available. Showing ${loaded}.`;
}

function excerptText(text, query, length = 380) {
  const tokens = query.match(/[\p{L}\p{N}]+/gu) || [];
  const indexes = tokens.map(token => text.toLocaleLowerCase().indexOf(token.toLocaleLowerCase())).filter(i => i >= 0);
  const center = indexes.length ? Math.min(...indexes) : 0;
  const start = Math.max(0, center - 100), end = Math.min(text.length, start + length);
  return (start ? '…' : '') + text.slice(start, end).trim() + (end < text.length ? '…' : '');
}
function highlighted(text, query) {
  const fragment = document.createDocumentFragment();
  const tokens = [...new Set(query.match(/[\p{L}\p{N}]+/gu) || [])].sort((a, b) => b.length - a.length);
  if (!tokens.length) { fragment.append(document.createTextNode(text)); return fragment; }
  // Tokens contain only letters/numbers, so no regex metacharacters are accepted.
  const matcher = new RegExp(tokens.join('|'), 'giu');
  let cursor = 0;
  for (const match of text.matchAll(matcher)) {
    fragment.append(document.createTextNode(text.slice(cursor, match.index)), el('mark', '', match[0]));
    cursor = match.index + match[0].length;
  }
  fragment.append(document.createTextNode(text.slice(cursor)));
  return fragment;
}
function resultView(doc, query) {
  const row = el('article', 'result source-match');
  row.dataset.source = doc.source_type; row.dataset.passage = doc.passage_id;
  const content = el('div');
  const top = el('div', 'result-top');
  top.append(el('span', 'badge ' + doc.source_type, doc.source_label));
  if (doc.timestamp) top.append(el('span', 'timestamp', doc.timestamp.replace(/[\[\]]/g, '')));
  if (doc.speaker_label) top.append(el('span', 'source-speaker', doc.speaker_label));
  const excerpt = el('p', 'excerpt'); excerpt.append(highlighted(excerptText(doc.text, query), query));
  const actions = el('div', 'result-actions');
  const action = doc.source_type === 'transcript' ? 'View in transcript →' : doc.source_type === 'show_notes' ? 'View published show notes →' : 'View episode →';
  const reason = doc.ranking.exact_phrase_bonus ? 'Exact phrase · lexical match' : 'All search terms in this passage';
  const sourceLink = link(action, withReturn(doc.url, {url: location.pathname + location.search}), 'text-link');
  sourceLink.dataset.resultPath = doc.url;
  actions.append(sourceLink, el('span', 'match-reason', reason));
  content.append(top, excerpt, actions, provenance({passage_id: doc.passage_id, locator: doc.locator,
    speaker_accuracy: doc.speaker_accuracy || 'not_applicable', ranking: doc.ranking}));
  row.append(content);
  return row;
}
function groupedResults(documents, query, truncated) {
  const groups = new Map();
  documents.forEach((doc, rank) => {
    if (!groups.has(doc.episode_id)) groups.set(doc.episode_id, {docs: [], rank, record: doc});
    groups.get(doc.episode_id).docs.push(doc);
  });
  const container = el('div', 'results grouped-results');
  for (const {docs, rank, record} of groups.values()) {
    const group = el('article', 'episode-result');
    group.dataset.episode = record.episode_id; group.dataset.rank = rank;
    const header = el('div', 'episode-result-header');
    const title = el('h3');
    const overviewURL = record.url.split('?')[0].replace(/\/(transcript|show-notes)$/, '');
    const titleLink = link(record.title, withReturn(overviewURL, {url: location.pathname + location.search}));
    titleLink.dataset.resultPath = overviewURL; title.append(titleLink);
    const heading = el('div'); heading.append(title, el('span', 'subtle', date(record.published_at)));
    header.append(episodeNumber(record.episode_number), heading);
    group.append(header);
    const sources = new Map();
    // Episode order follows its highest-ranked match; source sections and their
    // passages keep their first-occurrence order in the existing ranked list.
    docs.forEach(doc => {
      const key = ['transcript', 'show_notes'].includes(doc.source_type) ? doc.source_type : 'metadata';
      if (!sources.has(key)) sources.set(key, []);
      sources.get(key).push(doc);
    });
    const matches = el('div', 'episode-matches'); matches.id = 'matches-' + record.episode_id.split(':').pop();
    const extras = [];
    const openIds = (new URL(location.href).searchParams.get('open') || '').split(',');
    let expanded = openIds.includes(record.episode_id.split(':').pop());
    for (const [kind, passages] of sources) {
      const section = el('section', 'matching-source');
      const label = {metadata: 'Metadata', transcript: 'Transcript', show_notes: 'Published show notes'}[kind];
      section.append(el('h4', 'matching-source-heading', `${label} · ${passages.length} ${passages.length === 1 ? 'match' : 'matches'}`));
      passages.forEach((doc, index) => {
        const node = resultView(doc, query);
        if (index) { node.hidden = !expanded; extras.push(node); }
        section.append(node);
      });
      matches.append(section);
    }
    group.append(matches);
    const footer = el('div', 'group-footer');
    const episodeLink = link('View episode →', withReturn(overviewURL, {url: location.pathname + location.search}), 'text-link');
    episodeLink.dataset.resultPath = overviewURL; footer.append(episodeLink);
    if (extras.length) {
      const toggle = el('button', 'match-toggle'); toggle.type = 'button';
      const update = () => {
        toggle.textContent = expanded ? 'Show fewer matches ↑' : `Show all ${docs.length}${truncated ? ' loaded' : ''} matches ↓`;
        toggle.setAttribute('aria-expanded', String(expanded));
        extras.forEach(node => { node.hidden = !expanded; });
      };
      toggle.setAttribute('aria-controls', matches.id); update();
      toggle.addEventListener('click', () => {
        expanded = !expanded; update();
        const params = new URLSearchParams(location.search);
        const ids = new Set((params.get('open') || '').split(',').filter(Boolean));
        const id = record.episode_id.split(':').pop();
        if (expanded) ids.add(id); else ids.delete(id);
        if (ids.size) params.set('open', [...ids].join(',')); else params.delete('open');
        history.replaceState({}, '', archiveURL(Object.fromEntries(params)));
        lastArchive = location.pathname + location.search;
        container.querySelectorAll('[data-result-path]').forEach(anchor => {
          anchor.href = withReturn(anchor.dataset.resultPath, {url: lastArchive});
        });
      });
      footer.append(toggle);
    }
    group.append(footer); container.append(group);
  }
  return {container, episodeCount: groups.size};
}
async function searchView(params, body, ticket) {
  const q = params.get('q'); const source = params.get('source') || 'all';
  const limit = Math.min(100, Math.max(30, Number(params.get('limit')) || 30));
  const data = await api('/api/search?' + new URLSearchParams({q, source, limit, episode: params.get('episode') || ''}));
  if (ticket !== navigation) return;
  body.replaceChildren();
  const toolbar = el('div', 'toolbar');
  const filters = el('nav', 'filters'); filters.setAttribute('aria-label', 'Filter search by source');
  for (const [key, name] of [['all', 'All sources'], ['metadata', 'Metadata'], ['transcript', 'Transcripts'], ['show_notes', 'Show notes']]) {
    const anchor = link(name, archiveURL({q, source: key, episode: params.get('episode') || ''}), 'filter' + (source === key ? ' active' : ''));
    if (source === key) anchor.setAttribute('aria-current', 'true');
    filters.append(anchor);
  }
  toolbar.append(filters, link('Clear search', archiveURL({episode: params.get('episode') || ''}), 'clear-link'));
  body.append(toolbar);
  const heading = el('div', 'results-heading');
  const count = `${data.results.length}${data.has_more ? '+' : ''} source matches`;
  const grouped = groupedResults(data.results, q, data.has_more);
  heading.append(el('span', 'count', `${grouped.episodeCount} episodes · ${count} for “${q}”`), el('span', '', 'Best match per episode first'));
  body.append(heading);
  if (!data.results.length) {
    const empty = el('div', 'empty');
    empty.append(el('h2', '', 'No matching sources'), el('p', '', 'Try fewer words, another spelling, or a broader source filter. Search looks for every query word within the same source passage.'));
    body.append(empty);
  } else {
    body.append(grouped.container);
    const note = el('p', 'inline-warning', 'Speaker labels come from the published source and have not been verified against audio.');
    body.append(note);
    if (data.has_more && limit < 100) {
      body.append(el('p', 'inline-warning', 'Match counts refer to the sources loaded here. Load more to broaden these episode groups.'));
      body.append(link('Show more matches ↓', archiveURL({q, source, episode: params.get('episode') || '', limit: Math.min(limit + 30, 100)}), 'secondary load-more'));
    } else if (data.has_more) {
      body.append(el('p', 'inline-warning', 'Showing the first 100 matches. Narrow the query or search within an episode for more specific results.'));
    }
  }
  announcer.textContent = count;
}

function episodeFile(record, compact = false) {
  const area = el('section', 'episode-file' + (compact ? ' compact' : ''));
  area.setAttribute('aria-label', 'Episode file');
  area.append(el('h2', 'side-label', 'Episode file'), el('p', 'file-format', `Markdown · UTF-8 · ${fileSize(record.file.bytes)}`));
  if (!compact) area.append(el('p', 'sidebar-note', 'One portable document with episode metadata, published show notes and the source transcript. Source timestamps are preserved where present.'));
  const actions = el('div', 'file-actions');
  actions.append(link('View Markdown →', withReturn(record.file.url), 'text-link'), download('Download .md ↓', record.file.download_url));
  area.append(actions); return area;
}
async function archiveFilesView(url, ticket) {
  document.title = 'Archive Files · TSSE Content Archive';
  main.append(link('← Back to Content Archive', '/', 'back'));
  const header = el('section', 'files-hero');
  header.append(el('span', 'eyebrow', 'The Sure Shot Entrepreneur'), el('h1', '', url.pathname.endsWith('/episodes') ? 'Structured episode library' : 'Archive files'),
    el('p', 'intro', url.pathname.endsWith('/episodes') ? 'One portable Markdown document for every published episode.' : 'The complete published collection, in two portable formats.'));
  main.append(header);
  const loading = el('p', 'loading', 'Checking archive files…'); main.append(loading);
  const data = await api('/api/files');
  if (ticket !== navigation) return;
  loading.remove();
  if (!url.pathname.endsWith('/episodes')) main.append(syncStatus(data.sync));
  if (url.pathname.endsWith('/episodes')) {
    const intro = el('div', 'library-intro');
    intro.append(el('p', 'subtle', `${data.markdown_files} files · UTF-8 · Source timestamps preserved where present`),
      download(`Download Markdown library ↓ · ${fileSize(data.zip_bytes)}`, data.zip_download_url, 'secondary'));
    main.append(intro);
    const list = el('section'); main.append(list);
    await browseView(url.searchParams, list, ticket, true); return;
  }
  const catalogue = el('section', 'artifact');
  catalogue.append(el('span', 'artifact-number', '01'));
  const csvBody = el('div');
  csvBody.append(el('h2', '', 'Episode catalogue'), el('p', 'artifact-facts', `${data.csv_rows} episodes · CSV · UTF-8 · ${fileSize(data.csv_bytes)}`),
    el('p', 'artifact-copy', 'The complete published episode catalogue, ready to open in a spreadsheet or use in another content workflow.'));
  const fieldList = el('ul', 'field-list');
  for (const [key, label] of [['episode_id', 'Episode number and IDs'], ['title', 'Official title'], ['published_at', 'Publication date'], ['duration_seconds', 'Duration'], ['url', 'Official episode URL'], ['episode_type', 'Format / type'], ['speakers_json', 'Source speaker labels'], ['transcript_status', 'Content availability']]) {
    if (data.csv_fields.includes(key)) fieldList.append(el('li', '', label));
  }
  const fields = el('details'); fields.append(el('summary', '', `See all ${data.csv_fields.length} CSV fields`), el('p', 'csv-fields', data.csv_fields.join(', ')));
  csvBody.append(fieldList, fields);
  const csvActions = el('div', 'artifact-actions'); csvActions.append(download('Download CSV ↓', data.csv_download_url, 'primary-action'));
  catalogue.append(csvBody, csvActions); main.append(catalogue);
  const library = el('section', 'artifact'); library.append(el('span', 'artifact-number', '02'));
  const mdBody = el('div');
  mdBody.append(el('h2', '', 'Structured episode library'), el('p', 'artifact-facts', `${data.markdown_files} files · Markdown · UTF-8`),
    el('p', 'artifact-copy', 'One document per published episode, containing episode metadata, published show notes and the source transcript.'),
    el('p', 'artifact-copy', `Source timestamps are preserved where present (${data.timestamped_transcripts} transcripts). The files remain useful independently of this application.`));
  const libraryActions = el('div', 'artifact-actions');
  libraryActions.append(link('Browse episode files →', '/archive-files/episodes', 'primary-action'),
    download('Download Markdown library ↓', data.zip_download_url), el('span', 'subtle', `ZIP · ${fileSize(data.zip_bytes)}`));
  library.append(mdBody, libraryActions); main.append(library);
  main.append(el('p', 'files-footnote', 'Downloads are the existing generated exports. The ZIP contains only the Markdown documents, including their existing source-reference sections. Speaker labels are source-preserved and have not been verified against audio.'));
}
async function markdownView(record, ticket) {
  const section = el('section', 'markdown-view'); main.append(section);
  section.append(el('h2', 'content-heading', 'Episode file'));
  const loading = el('p', 'loading', 'Loading the generated Markdown document…'); section.append(loading);
  const file = await api(`/api/episodes/${record.remote_id}/file`);
  if (file.text === undefined) {
    // Public hosting serves the existing Markdown bytes directly from the CDN.
    const response = await fetch(file.download_url, {cache: 'no-cache'});
    if (!response.ok) throw new Error('This episode file is temporarily unavailable. Please try again.');
    const raw = await response.arrayBuffer();
    const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', raw)), byte => byte.toString(16).padStart(2, '0')).join('');
    if (hash !== file.sha256) throw new Error('This episode file is being updated. Please reload and try again.');
    file.text = new TextDecoder('utf-8', {fatal: true}).decode(raw);
  }
  if (ticket !== navigation) return;
  loading.remove();
  const toolbar = el('div', 'document-toolbar');
  const info = el('div'); info.append(el('code', 'document-name', file.filename), el('p', 'subtle', `Actual generated file · Markdown · UTF-8 · ${fileSize(file.bytes)}`));
  toolbar.append(info, download('Download .md ↓', file.download_url, 'secondary')); section.append(toolbar);
  section.append(el('p', 'source-note', 'This is the actual portable document. Source HTML is shown literally inside Markdown fences; no HTML is executed. Source timestamps are preserved where present.'));
  const nav = el('nav', 'document-nav'); nav.setAttribute('aria-label', 'Markdown document sections');
  for (const [id, label] of [['metadata', 'Metadata'], ['notes', 'Published show notes'], [file.text.includes('## Transcript — source-preserving text projection') ? 'transcript' : 'transcript-html', file.text.includes('## Transcript — source-preserving text projection') ? 'Transcript text' : 'Transcript availability'], ['references', 'Source references']]) nav.append(link(label, '#file-' + id));
  section.append(nav);
  const pre = el('pre', 'markdown-document'); pre.tabIndex = 0; pre.setAttribute('aria-label', 'Actual Markdown file');
  const starts = [{index: 0, id: 'metadata'}];
  const headings = {'Published show notes — preserved source HTML': 'notes', 'Transcript — preserved source HTML': 'transcript-html', 'Transcript — source-preserving text projection': 'transcript', 'Source references': 'references'};
  for (const match of file.text.matchAll(/^## (.+)\n/gm)) if (headings[match[1]]) starts.push({index: match.index, id: headings[match[1]]});
  starts.forEach((start, index) => {
    const chunk = el('span', 'markdown-section', file.text.slice(start.index, starts[index + 1]?.index));
    chunk.id = 'file-' + start.id; pre.append(chunk);
  });
  section.append(pre, provenance({filename: file.filename, bytes: file.bytes, sha256: file.sha256}, 'File integrity'));
  if (/^#file-[a-z-]+$/.test(location.hash)) requestAnimationFrame(() => document.getElementById(location.hash.slice(1))?.scrollIntoView());
}

function sidebar(record, includeFile = true) {
  const aside = el('aside');
  const sources = el('div', 'source-availability'); sources.append(el('h2', 'side-label', 'Available source material'));
  for (const [kind, label, route] of [['transcript', 'Transcript', '/transcript'], ['show_notes', 'Published show notes', '/show-notes']]) {
    const source = record.sources[kind];
    const row = source.available ? link('', withReturn(record.url + route), 'availability') : el('div', 'availability unavailable');
    row.append(el('span', '', label), el('span', '', source.available ? '↗' : source.availability));
    sources.append(row);
  }
  aside.append(sources, el('p', 'sidebar-note', 'Official published sources, preserved in the local archive.'));
  if (includeFile && record.file) aside.append(episodeFile(record, true));
  const search = el('div', 'sidebar-search');
  const label = el('label', 'side-label', 'Search this episode'); label.htmlFor = 'episode-query';
  const form = el('form'); form.setAttribute('role', 'search');
  const input = el('input'); input.id = 'episode-query'; input.name = 'q'; input.placeholder = 'Find a word or phrase…'; input.maxLength = 300; input.required = true;
  const button = el('button', '', '→'); button.type = 'submit'; button.setAttribute('aria-label', 'Search this episode');
  form.append(input, button); search.append(label, form); aside.append(search);
  form.addEventListener('submit', event => {
    event.preventDefault();
    navigate(archiveURL({q: input.value.trim(), episode: record.episode_number, source: 'all'}));
  });
  return aside;
}
function overview(record, column) {
  column.append(el('h2', 'content-heading', 'About this episode'),
    el('p', 'overview-text', record.summary || 'No short description is available in the official record.'));
  if (record.selected_match) {
    const doc = record.selected_match;
    const match = el('div', 'metadata-match');
    match.append(el('span', 'badge', 'Matched ' + (doc.source_type === 'speaker_labels' ? 'source speaker labels' : doc.source_type.replaceAll('_', ' '))),
      el('p', '', doc.text), provenance({passage_id: doc.passage_id, locator: doc.locator}));
    if (doc.source_type === 'speaker_labels') match.append(el('p', 'inline-warning', 'Source labels only; identities have not been verified against audio.'));
    column.append(match);
  }
  const links = el('div', 'read-links');
  if (record.sources.transcript.available) links.append(link('Read transcript →', withReturn(record.url + '/transcript')));
  if (record.sources.show_notes.available) links.append(link('Read published show notes →', withReturn(record.url + '/show-notes')));
  column.append(links);
  if (record.file) column.append(episodeFile(record));
}
function passageBody(text, label) {
  const body = el('div', 'passage-text');
  // Typographic emphasis only. The prefix and remaining words are unmodified.
  const position = label ? text.indexOf(label + ':') : -1;
  if (position >= 0 && position < 25) {
    const end = position + label.length + 1;
    body.append(document.createTextNode(text.slice(0, position)), el('strong', 'speaker', text.slice(position, end)), document.createTextNode(text.slice(end)));
  } else body.textContent = text;
  return body;
}
async function reader(record, kind, pid, column, ticket) {
  const heading = kind === 'transcript' ? 'Transcript' : 'Published show notes';
  column.className = 'reading-column' + (kind === 'show_notes' ? ' notes-column' : '');
  column.append(el('h2', 'content-heading', heading));
  const loading = el('p', 'loading', 'Loading published source…'); column.append(loading);
  try {
    const data = await api(`/api/episodes/${record.remote_id}/content?` + new URLSearchParams({source: kind, ...(pid ? {passage: pid} : {})}));
    if (ticket !== navigation) return;
    loading.remove();
    const note = kind === 'transcript' ? 'Speaker labels are preserved from the published transcript source and have not been verified against audio.' : 'Published show notes, displayed as source text. The original HTML is preserved in the archive.';
    column.append(el('p', 'source-note', note));
    if (kind === 'transcript' && record.sources.transcript.timestamps.state !== 'present') {
      column.append(el('p', 'source-note', 'This published transcript does not contain timestamps. Passage links still open the exact source text.'));
    }
    if (pid) {
      const selected = el('div', 'selected-notice');
      selected.append(el('span', '', '↓ Your selected source passage is highlighted'), link('Read from the beginning ↑', withReturn(record.url + (kind === 'transcript' ? '/transcript' : '/show-notes'))));
      column.append(selected);
    }
    const context = el('div', 'reader-context');
    const contextCopy = el('div', 'reader-context-copy'); contextCopy.append(el('strong', '', `EP. ${number(record.episode_number)} · ${record.official_title}`));
    const origin = searchOrigin();
    if (origin) contextCopy.append(el('span', 'reader-query', `Search result: “${origin.query}”`));
    const contextLinks = el('div', 'reader-context-links');
    if (origin) contextLinks.append(link('Back to search results', origin.url));
    contextLinks.append(link('Episode overview ↗', withReturn(record.url)));
    context.append(contextCopy, contextLinks);
    column.append(context);
    const reading = el('div', 'reading'); reading.setAttribute('aria-label', heading + ' source text');
    // Python locators use Unicode code points. Array.from avoids offset drift
    // for astral characters (emoji etc.) in JavaScript's UTF-16 strings.
    const points = Array.from(data.text); let cursor = 0;
    let selectedNode = null;
    data.passages.forEach((span, index) => {
      const {start, end} = span.locator;
      if (start > cursor) reading.append(el('span', 'source-space', points.slice(cursor, start).join('')));
      const section = el('section', 'passage' + (span.passage_id === pid ? ' selected' : ''));
      section.id = 'passage-' + span.passage_id;
      section.dataset.passage = span.passage_id;
      section.dataset.start = start; section.dataset.end = end;
      if (span.passage_id === pid) { section.setAttribute('aria-label', 'Selected source passage'); section.tabIndex = -1; selectedNode = section; }
      const url = record.url + (kind === 'transcript' ? '/transcript' : '/show-notes') + '?' + new URLSearchParams({passage: span.passage_id});
      const anchor = link(kind === 'transcript' && span.timestamp ? span.timestamp.replace(/[\[\]]/g, '') : kind === 'show_notes' ? '↗' : '¶', withReturn(url), 'anchor');
      anchor.setAttribute('aria-label', `Link to ${span.timestamp || 'passage ' + (index + 1)}`);
      section.append(anchor, passageBody(points.slice(start, end).join(''), span.speaker_label));
      reading.append(section); cursor = end;
    });
    if (cursor < points.length) reading.append(el('span', 'source-space', points.slice(cursor).join('')));
    column.append(reading, provenance(data.selected_passage ? {
      passage_id: data.selected_passage.passage_id, locator: data.selected_passage.locator,
      source: data.provenance
    } : data.provenance, 'Published source provenance'));
    if (selectedNode) {
      // Identity comes from the index, never a substring search.
      requestAnimationFrame(() => {
        if (ticket !== navigation) return;
        selectedNode.focus({preventScroll: true}); selectedNode.scrollIntoView({block: 'center'});
      });
      announcer.textContent = 'Selected source passage opened and highlighted.';
    }
  } catch (error) {
    if (ticket !== navigation) return;
    loading.remove(); errorView(error, column);
    if (pid) column.append(link('Open the full source without this passage →', withReturn(record.url + (kind === 'transcript' ? '/transcript' : '/show-notes')), 'text-link'));
  }
}
async function episodeView(url, ticket) {
  const parts = url.pathname.split('/');
  const identity = parts[2]; const kind = parts[3] === 'transcript' ? 'transcript' : parts[3] === 'show-notes' ? 'show_notes' : parts[3] === 'file' ? 'file' : 'overview';
  const pid = url.searchParams.get('passage');
  const origin = searchOrigin();
  main.append(link(origin ? '← Back to search results' : '← Back to archive', origin?.url || lastArchive, 'back'));
  const loading = el('p', 'loading', 'Loading episode…'); main.append(loading);
  const record = await api(`/api/episodes/${encodeURIComponent(identity)}` + (kind === 'overview' && pid ? '?' + new URLSearchParams({passage: pid}) : ''));
  if (ticket !== navigation) return;
  if (identity !== record.remote_id) history.replaceState({}, '', record.url + (parts[3] ? '/' + parts[3] : '') + url.search);
  loading.remove(); document.title = `${record.official_title} · TSSE Archive`;
  const header = el('section', 'episode-header');
  header.append(el('span', 'eyebrow', `Episode ${number(record.episode_number)}`), el('h1', '', record.official_title));
  const meta = el('div', 'episode-meta');
  meta.append(el('span', '', date(record.published_at)), el('span', '', '·'), el('span', '', duration(record.duration_seconds)));
  if (record.episode_type) meta.append(el('span', '', '·'), el('span', '', record.episode_type[0].toUpperCase() + record.episode_type.slice(1) + ' episode'));
  meta.append(safeExternal('Official episode ↗', record.episode_url, 'official')); header.append(meta); main.append(header);
  const tabs = el('nav', 'tabs'); tabs.setAttribute('aria-label', 'Episode source views');
  for (const [tab, label, route] of [['overview', 'Overview', ''], ['transcript', 'Transcript', '/transcript'], ['show_notes', 'Published show notes', '/show-notes'], ['file', 'Episode file', '/file']]) {
    if (tab === 'file' ? !record.file : tab !== 'overview' && !record.sources[tab].available) continue;
    const node = link(label, withReturn(record.url + route), 'tab' + (kind === tab ? ' active' : ''));
    if (kind === tab) node.setAttribute('aria-current', 'page'); tabs.append(node);
  }
  main.append(tabs);
  if (kind === 'file') { await markdownView(record, ticket); return; }
  const layout = el('div', 'episode-layout'); const column = el('div');
  layout.append(column, sidebar(record, kind !== 'overview')); main.append(layout);
  if (kind === 'overview') overview(record, column);
  else await reader(record, kind, pid, column, ticket);
}
async function render() {
  const ticket = ++navigation;
  performance.mark('archive-view-start');
  delete main.dataset.viewMilliseconds;
  main.replaceChildren(); announcer.textContent = '';
  // Move focus before fetching data. Doing this after the asynchronous load
  // would steal focus from someone already typing into the search field.
  main.focus({preventScroll: true});
  window.scrollTo(0, 0);
  const url = new URL(location.href);
  try {
    if (url.pathname === '/') await archiveView(url.searchParams, ticket);
    else if (['/archive-files', '/archive-files/episodes'].includes(url.pathname)) await archiveFilesView(url, ticket);
    else if (/^\/episodes\/[^/]+(?:\/transcript|\/show-notes|\/file)?$/.test(url.pathname)) await episodeView(url, ticket);
    else throw new Error('This archive page does not exist.');
  } catch (error) { if (ticket === navigation) errorView(error); }
  if (ticket === navigation) {
    const measurement = performance.measure('archive-view', 'archive-view-start');
    // Observable timing for local performance checks, with no diagnostic UI.
    main.dataset.viewMilliseconds = measurement.duration.toFixed(1);
  }
}
render();
