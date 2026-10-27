// Isolated presentation test: run the actual function with a minimal text-node adapter.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const source=readFileSync(new URL('../../web/app.js',import.meta.url),'utf8');
const fn=source.slice(source.indexOf('function syncStatus('),source.indexOf('function filesEntry('));
function el(tag,cls,text='') {
  return {tag,textContent:text,children:[],setAttribute(){},append(...children){this.children.push(...children);}};
}
const context=vm.createContext({el,Intl,Date,document:{createTextNode:text=>({textContent:text})}});
vm.runInContext(fn,context);
const checks=[];
for(const [timestamp,expected] of [
 ['2026-01-06T14:30:00Z','Jan 6, 2026 · 6:30 AM PT'],
 ['2026-07-07T13:30:00Z','Jul 7, 2026 · 6:30 AM PT'],
 ['2026-03-03T14:30:00Z','Mar 3, 2026 · 6:30 AM PT'],
 ['2026-03-10T13:30:00Z','Mar 10, 2026 · 6:30 AM PT'],
 ['2026-11-03T14:30:00Z','Nov 3, 2026 · 6:30 AM PT']]) {
 const node=context.syncStatus({status:'success',last_successful_sync_at:timestamp});
 const time=node.children.find(n=>n.tag==='time');
 assert.equal(time.textContent,expected);assert.equal(time.dateTime,timestamp);
 checks.push({timestamp,display:time.textContent});
}
assert.match(context.syncStatus(null).textContent,/not yet recorded/);
assert.match(context.syncStatus({status:'failed'}).textContent,/not yet recorded/);
console.log(JSON.stringify({passed:true,checks},null,2));
