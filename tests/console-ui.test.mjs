import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('all workspaces use shared console styling and navigation',()=>{
 for(const path of ['index.html','analysis.html','screen-review.html']){
  const html=read(path);
  assert.ok(html.includes('href="./console.css"'));
  assert.ok(html.includes('class="console-nav"'));
  assert.equal((html.match(/aria-current="page"/g)||[]).length,1);
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);
  assert.equal(new Set(ids).size,ids.length,path+' duplicate IDs');
 }
});
test('local server serves the console and saved review provenance module',()=>{
 const server=read('server.mjs');
 for(const path of ['console.css','review-provenance.js'])assert.ok(server.includes("'/"+path+"':'"+path+"'"));
});
test('console theme does not load remote resources or animate the capture surface',()=>{
 const css=read('console.css');
 assert.doesNotMatch(css,/@import|url\s*\(/i);
 assert.doesNotMatch(css,/@keyframes/);
});
