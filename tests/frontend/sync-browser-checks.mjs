// Run through Codex cua_repl with documented tab and viewport handles.
import {readFile, mkdir, writeFile} from 'node:fs/promises';

export async function runSyncChecks(tab, viewport, repository, base='http://127.0.0.1:8765') {
  const status=JSON.parse(await readFile(repository+'/archive/sync-status.json','utf8'));
  const checks=[];
  const check=(name,passed,evidence)=>{
    checks.push({name,passed:Boolean(passed),evidence});
    if(!passed) throw new Error(name+': '+JSON.stringify(evidence));
  };
  const output=repository+'/docs/screenshots/archive-sync';
  await mkdir(output,{recursive:true});
  const instant=new Date(status.last_successful_sync_at);
  const expected=new Intl.DateTimeFormat('en-US',{timeZone:'America/Los_Angeles',month:'short',day:'numeric',year:'numeric'}).format(instant)
    +' · '+new Intl.DateTimeFormat('en-US',{timeZone:'America/Los_Angeles',hour:'numeric',minute:'2-digit',hour12:true}).format(instant)+' PT';
  for(const [name,width,height] of [['desktop',1366,900],['tablet',768,1024],['mobile',375,812]]) {
    await viewport.set({width,height});
    if(await tab.url()===base+'/') await tab.reload(); else await tab.goto(base+'/');
    await tab.playwright.locator('.sync-status time').waitFor({state:'visible'});
    await tab.playwright.locator('.browse-row').first().waitFor({state:'visible'});
    const home=await tab.playwright.evaluate(()=>({
      date:document.querySelector('.sync-status time').getAttribute('datetime'),
      text:document.querySelector('.sync-status time').textContent,
      status:document.querySelector('.sync-status').textContent,
      width:innerWidth,pageWidth:document.documentElement.scrollWidth,
      y:['.search-box','.coverage','.files-entry','.sync-status','.browse-row'].map(selector=>document.querySelector(selector)?.getBoundingClientRect().top),
      font:getComputedStyle(document.querySelector('.sync-status')).fontSize,
      coverage:document.querySelector('.coverage').textContent
    }));
    check(name+' home reads persisted successful timestamp',home.date===status.last_successful_sync_at,home.date);
    check(name+' home displays Pacific Time',home.text===expected,home.text);
    check(name+' home has no horizontal overflow',home.pageWidth<=home.width,home);
    check(name+' home keeps search, coverage and files above freshness',home.y.every((y,i)=>y!=null&&(!i||y>home.y[i-1])),home.y);
    check(name+' coverage matches successful episode count',home.coverage.includes(status.published_episodes+' episodes'),home.coverage);
    check(name+' status avoids unsupported up-to-date claim',!home.status.includes('Up to date'),home.status);
    await writeFile(output+'/home-'+name+'.jpg',await tab.screenshot({clip:{x:0,y:0,width,height}}));
    await tab.playwright.locator('.files-entry').press('Enter');
    await tab.playwright.locator('.files-hero').waitFor({state:'visible'});
    await tab.playwright.locator('.sync-status time').waitFor({state:'visible'});
    const files=await tab.playwright.evaluate(()=>({date:document.querySelector('.sync-status time').getAttribute('datetime'),
      text:document.querySelector('.sync-status time').textContent,width:innerWidth,pageWidth:document.documentElement.scrollWidth}));
    check(name+' Archive Files shares the persisted Pacific timestamp',files.date===status.last_successful_sync_at&&files.text===expected,files);
    check(name+' Archive Files has no horizontal overflow',files.pageWidth<=files.width,files);
    await writeFile(output+'/files-'+name+'.jpg',await tab.screenshot({clip:{x:0,y:0,width,height}}));
  }
  await tab.goto(base+'/');
  await tab.playwright.locator('.browse-row').first().click();
  await tab.playwright.locator('.content-heading').waitFor({state:'visible'});
  check('Individual episode avoids repeated freshness',await tab.playwright.locator('.sync-status').count()===0);
  const logs=await tab.dev.logs({levels:['error','warn'],limit:50});
  check('No browser errors or warnings',logs.length===0,logs);
  const report={checked_at:new Date().toISOString(),persisted_status:status,checks,passed:checks.every(c=>c.passed)};
  await writeFile(output+'/freshness-validation.json',JSON.stringify(report,null,2)+'\n');
  await viewport.reset();
  return report;
}
