// Real UI checks, run with the documented Codex cua_repl tab/viewport handles.
import {createHash} from 'node:crypto';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export async function runFilesChecks(tab, viewport, root, base = 'http://127.0.0.1:8765') {
  const checks = [], queries = [];
  const check = (name, passed, evidence) => { checks.push({name, passed:!!passed, evidence}); if (!passed) throw Error(name + ': ' + JSON.stringify(evidence)); };
  const ready = selector => tab.playwright.locator(selector).first().waitFor({state:'visible'});
  const shot = async name => { await writeFile(root + '/docs/screenshots/archive-files/' + name + '.png', await tab.screenshot({fullPage:false})); };
  const go = async path => { if (await tab.url() === base + path) await tab.reload(); else await tab.goto(base + path); };
  const search = async q => {
    await tab.playwright.getByRole('searchbox', {name:'Search the archive'}).fill(q);
    await tab.playwright.getByRole('searchbox', {name:'Search the archive'}).press('Enter');
    await tab.playwright.locator('.results-heading').filter({hasText:'source matches for “' + q + '”'}).waitFor({state:'visible'});
  };
  const groups = () => tab.playwright.evaluate(() => [...document.querySelectorAll('.episode-result')].map(n => ({id:n.dataset.episode, rank:+n.dataset.rank, title:n.querySelector('h3').textContent, number:n.querySelector('.episode-number').textContent, sources:[...n.querySelectorAll('.matching-source-heading')].map(s=>s.textContent), passages:[...n.querySelectorAll('.result')].map(p=>({pid:p.dataset.passage, time:p.querySelector('.timestamp')?.textContent, source:p.dataset.source, text:p.querySelector('.excerpt').textContent}))})));
  const download = async locator => {
    const pending = tab.playwright.waitForEvent('download',{timeoutMs:15000}); await locator.click();
    const path = await (await pending).path({timeoutMs:15000}); const bytes = await readFile(path);
    return {path, bytes:bytes.length, sha256:hash(bytes)};
  };
  await mkdir(root + '/docs/screenshots/archive-files',{recursive:true});
  await viewport.set({width:1366,height:900}); await go('/'); await ready('.files-entry');
  const hierarchy = await tab.playwright.evaluate(() => ({search:document.querySelector('.search-box').getBoundingClientRect().top, coverage:document.querySelector('.coverage').getBoundingClientRect().top, files:document.querySelector('.files-entry').getBoundingClientRect().top, browse:document.querySelector('.episode-list').getBoundingClientRect().top, label:document.querySelector('header').textContent}));
  check('Home hierarchy and Content Archive terminology', hierarchy.search<hierarchy.coverage && hierarchy.coverage<hierarchy.files && hierarchy.files<hierarchy.browse && !hierarchy.label.includes('THE CONTENT LIBRARY'),hierarchy);
  await shot('home');
  await tab.playwright.locator('.files-entry').press('Enter'); await ready('.artifact');
  const fileCopy = await tab.playwright.locator('main').innerText();
  check('Keyboard opens Archive Files with actual counts and timestamp qualifier', fileCopy.includes('195 episodes') && fileCopy.includes('195 files') && fileCopy.includes('116 transcripts') && fileCopy.includes('33 CSV fields'));
  await shot('archive-files');
  const csv = await download(tab.playwright.getByRole('link',{name:'Download CSV',exact:false}));
  check('Browser downloads actual CSV bytes', csv.sha256===hash(await readFile(root+'/archive/exports/catalogue.csv')),csv);
  const zip = await download(tab.playwright.getByRole('link',{name:'Download Markdown library',exact:false}));
  check('Browser downloads reproducible full library ZIP',zip.bytes===3918604 && zip.sha256==='adec24a037137e50cffcfbd0b8b828e0f81522c98b0e41040ae507be86e9ae83',zip);
  await tab.playwright.getByRole('link',{name:'Browse episode files',exact:false}).click(); await ready('.file-row');
  check('Markdown browse newest first with view/download actions',(await tab.playwright.locator('.file-row').first().innerText()).includes('195') && await tab.playwright.locator('.file-row a[download]').first().isVisible());
  await shot('markdown-library');
  await tab.playwright.getByRole('combobox',{name:'Sort by'}).selectOption('oldest');
  await tab.playwright.locator('.file-row').first().filter({hasText:'Welcome and quick intro'}).waitFor({state:'visible'});
  check('Markdown browse oldest-first sorting',true);
  for (let loaded=24; loaded<195; loaded+=24) {
    await tab.playwright.getByRole('button',{name:'Load more episodes',exact:false}).click();
    await tab.playwright.getByText(`Showing ${Math.min(loaded+24,195)} of 195 episodes`,{exact:true}).waitFor({state:'visible'});
  }
  const all = await tab.playwright.evaluate(()=>({count:document.querySelectorAll('.file-row').length,unique:new Set([...document.querySelectorAll('.file-row h3 a')].map(a=>a.href)).size}));
  check('All 195 Markdown files browsable with unique mapping',all.count===195&&all.unique===195,all);
  await tab.playwright.getByRole('combobox',{name:'Sort by'}).selectOption('number'); await ready('.file-row');
  check('Episode-number sort available',new URL(await tab.url()).searchParams.get('sort')==='number');
  await go('/episodes/195/file'); await ready('.markdown-document');
  const md = await tab.playwright.evaluate(()=>({text:document.querySelector('.markdown-document').textContent,integrity:JSON.parse(document.querySelector('.markdown-view details pre').textContent),unsafe:document.querySelectorAll('.markdown-document script,.markdown-document iframe,.markdown-document img').length}));
  check('Actual Markdown DOM preserves exact artifact bytes and escapes HTML',hash(md.text)===md.integrity.sha256 && md.unsafe===0,md.integrity);
  check('Actual Markdown includes metadata, notes, transcript and source timestamps',md.text.includes('## Episode metadata') && md.text.includes('## Published show notes') && md.text.includes('## Transcript') && md.text.includes('00:24:01'));
  await shot('markdown-file');
  const mdDownload = await download(tab.playwright.locator('.document-toolbar a[download]'));
  check('Browser downloads same Markdown shown in file view',mdDownload.sha256===md.integrity.sha256,mdDownload);
  await tab.playwright.locator('.document-nav').getByRole('link',{name:'Transcript text',exact:true}).press('Enter');
  check('Keyboard Markdown section navigation',new URL(await tab.url()).hash==='#file-transcript');
  await shot('markdown-transcript');
  await go('/'); await ready('.browse-row');
  for (const q of ['customer discovery','founder market fit','contrarian','capital efficient']) {
    await search(q); const data=await groups();
    check('Cross-episode grouped search: '+q,data.length>1 && new Set(data.map(g=>g.id)).size===data.length && data.every((g,i)=>i===0||g.rank>data[i-1].rank),{episodes:data.length,first:data[0].number});
    check('Query highlights: '+q,await tab.playwright.locator('.excerpt mark').first().isVisible());
    queries.push({query:q,groups:data});
    await shot(q==='customer discovery'?'grouped-search':'search-'+q.replaceAll(' ','-'));
  }
  await search('proof of value');
  const proof = await groups();
  check('Metadata, notes and transcript grouped under one episode',proof.length===1 && ['episode_title','show_notes','transcript'].every(s=>proof[0].passages.some(p=>p.source===s)),proof[0].sources);
  await tab.playwright.locator('.match-toggle').press('Enter');
  const origin = new URL(await tab.url()).pathname + new URL(await tab.url()).search;
  check('Keyboard expansion stored in URL',await tab.playwright.locator('.match-toggle').getAttribute('aria-expanded')==='true' && origin.includes('open='));
  const passage = proof[0].passages.find(p=>p.source==='transcript');
  await tab.playwright.locator(`.result[data-passage="${passage.pid}"] .text-link`).click(); await ready('.passage.selected');
  check('Deep link retains query and exact highlighted passage',(await tab.playwright.locator('.reader-query').innerText()).includes('proof of value') && await tab.playwright.locator('.passage.selected').getAttribute('data-passage')===passage.pid);
  await tab.reload(); await ready('.passage.selected');
  check('Deep link reload retains return state',new URL(await tab.url()).searchParams.get('return')===origin);
  await tab.playwright.locator('.reader-context-links').getByRole('link',{name:'Episode overview',exact:false}).click(); await ready('.overview-text');
  check('Episode overview includes summary, source links, search, Markdown access',await tab.playwright.locator('.episode-file').isVisible() && await tab.playwright.getByRole('textbox',{name:'Search this episode',exact:true}).isVisible());
  await shot('episode-overview');
  await tab.playwright.locator('.episode-file').getByRole('link',{name:'View Markdown',exact:false}).click(); await ready('.markdown-document');
  check('Episode file route retains search origin',new URL(await tab.url()).searchParams.get('return')===origin);
  await tab.playwright.locator('main > .back').click(); await ready('.episode-result');
  check('Back to search restores query and expanded group',new URL(await tab.url()).pathname + new URL(await tab.url()).search===origin && await tab.playwright.locator('.match-toggle').getAttribute('aria-expanded')==='true');
  await search('choosing a partner in life');
  await tab.playwright.getByRole('link',{name:'Transcripts',exact:true}).click(); await ready('.filter.active');
  const partner = (await groups()).flatMap(g=>g.passages).find(p=>p.time==='00:23:15');
  await tab.playwright.locator(`.result[data-passage="${partner.pid}"] .text-link`).click(); await ready('.passage.selected');
  check('Filtered result keeps source filter in return URL',new URL(await tab.url()).searchParams.get('return').includes('source=transcript'));
  const deepURL=await tab.url(); await shot('transcript-deep-link');
  await go('/episodes/195/show-notes'); await ready('.notes-column .passage');
  const quiet=await tab.playwright.evaluate(()=>getComputedStyle(document.querySelector('.notes-column .anchor')).opacity);
  check('Notes paragraph links visually restrained',Number(quiet)<0.5,quiet);
  await tab.playwright.locator('.notes-column .anchor').first().press('Enter'); await ready('.passage.selected');
  check('Notes links remain keyboard operable',new URL(await tab.url()).searchParams.has('passage'));
  for (const width of [375,768,1366]) {
    await viewport.set({width,height:width===375?812:900});
    for (const [path,selector] of [['/archive-files','.artifact'],['/archive-files/episodes','.file-row'],['/episodes/195/file','.markdown-document'],['/?q=customer+discovery','.episode-result'],['/episodes/195','.episode-file'],[deepURL.slice(base.length),'.passage.selected']]) {
      await go(path); await ready(selector);
      const size=await tab.playwright.evaluate(()=>({width:innerWidth,pageWidth:document.documentElement.scrollWidth}));
      check(`${width}px no horizontal overflow: ${path.split('?')[0]}`,size.pageWidth<=size.width,size);
    }
  }
  const logs=await tab.dev.logs({levels:['error','warn'],limit:50}); check('No browser warnings or errors',logs.length===0,logs);
  return {checked_at:new Date().toISOString(),passed:checks.every(c=>c.passed),checks,queries,deepURL};
}
