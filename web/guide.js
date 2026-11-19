'use strict';

// Memory belongs to this tab. Reading a citation and going Back preserves the conversation.
const guideTurns = [];
let guidePending = false;
let guideSuggestionState = null;
const guideExamples = [
  'How does venture capital work?',
  'What do investors look for in founders?',
  'How can I validate a startup idea?',
  'What mistakes do first-time founders make?',
  'What have TSSE guests said about artificial intelligence?'
];

function guideReply(turn) {
  const section = el('article', 'guide-turn');
  section.append(el('h2', '', turn.question));
  const data = turn.answer;
  if (data.message) section.append(el('p', '', data.message));
  for (const item of data.recommendations || []) {
    const card = el('section', 'guide-episode');
    card.append(el('h3', '', 'Ep. ' + item.episode + ' · ' + item.title));
    if (item.guests.length) card.append(el('p', 'side-label', item.guests.join(' & ')));
    if (item.description) card.append(el('p', '', item.description));
    card.append(link('Listen to the official episode ↗', item.url, 'text-link'));
    for (const source of item.sources) card.append(link('Read supporting passage →', source.url, 'text-link guide-source'));
    section.append(card);
  }
  if (data.suggestions?.length) {
    section.append(el('h3', '', 'Explore further'));
    const suggestions = el('div', 'guide-examples');
    for (const question of data.suggestions) {
      const button = el('button', '', question); button.type = 'button';
      button.onclick = () => {
        if (guidePending) return;
        const field = document.getElementById('guide-question');
        field.value = question;
        guideSuggestionState = data.state;
        field.form.requestSubmit();
      };
      suggestions.append(button);
    }
    section.append(suggestions);
  }
  if (data.mode !== 'live' || !data.recommendations?.length) section.append(link('Search the archive →', data.search, 'text-link'));
  return section;
}

function guideView() {
  document.title = 'Ask the TSSE Archive · The Sure Shot Entrepreneur';
  const area = el('section', 'guide');
  area.append(link('← Browse archive', '/', 'text-link'), el('h1', '', 'Ask the TSSE Archive'),
    el('p', 'intro', 'Discover podcast conversations about the questions on your mind. Explore individual perspectives, then listen for yourself.'));
  const mode = el('p', 'side-label');
  area.append(mode);
  api('/api/chat/status').then(data => {
    mode.textContent = {mock: 'Archive discovery preview', live: 'AI-assisted podcast discovery',
      off: 'Guide paused · browse the archive above'}[data.mode];
  }).catch(() => { mode.textContent = 'Guide status unavailable'; });
  const turns = el('div');
  guideTurns.forEach(turn => turns.append(guideReply(turn)));
  const form = el('form', 'guide-form');
  const label = el('label', '', guideTurns.length ? 'Ask a follow-up or start a new topic' : 'Your question');
  label.htmlFor = 'guide-question';
  const field = el('textarea'); field.id = label.htmlFor; field.required = true; field.maxLength = 600; field.rows = 2;
  const send = el('button', 'primary', 'Ask the archive'); send.type = 'submit';
  const status = el('p', '', guidePending ? 'Checking archive passages…' : ''); status.setAttribute('role', 'status');
  send.disabled = guidePending;
  form.append(label, field, send, status);
  const examples = el('div', 'guide-examples');
  for (const prompt of guideExamples) {
    const button = el('button', '', prompt); button.type = 'button';
    button.onclick = () => { field.value = prompt; field.focus(); };
    examples.append(button);
  }
  area.append(turns, form);
  if (!guideTurns.length) area.append(examples);
  main.append(area);
  form.onsubmit = async event => {
    event.preventDefault();
    const question = field.value.trim();
    if (!question || guidePending) return;
    guidePending = send.disabled = true;
    status.textContent = 'Checking archive passages…';
    const state = guideSuggestionState || guideTurns.at(-1)?.answer.state || {};
    guideSuggestionState = null;
    const history = guideTurns.slice(-4).map(({question}) => ({question}));
    try {
      const response = await fetch('/api/chat', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question, history, state})});
      const answer = await response.json();
      if (!response.ok) throw new Error(answer.error || 'The guide is unavailable.');
      guideTurns.push({question, answer});
      if (guideTurns.length > 20) guideTurns.shift();
      if (area.isConnected) {
        const reply = guideReply({question, answer});
        turns.append(reply); examples.remove(); field.value = '';
        label.textContent = 'Ask a follow-up or start a new topic';
        reply.tabIndex = -1; reply.focus();
        status.textContent = 'Answer ready.';
      }
    } catch (error) {
      status.textContent = error.message || 'The guide is unavailable. Please try again.';
    } finally {
      guidePending = send.disabled = false;
      if (!area.isConnected && location.pathname === '/ask') render();
    }
  };
}
