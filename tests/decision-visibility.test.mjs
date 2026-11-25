import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const html=readFileSync(new URL('../screen-review.html',import.meta.url),'utf8');
const view=readFileSync(new URL('../live-practice-view.js',import.meta.url),'utf8');
test('decision status is separate from the hidden card overlay',()=>{
 const overlay=html.slice(html.indexOf('id="live-overlay"'),html.indexOf('id="screen-decision"'));
 assert.ok(overlay.includes('id="live-cards"'));
 assert.ok(!overlay.includes('id="live-action"'));
 for(const id of ['screen-decision','live-action','live-action-detail','decision-status-text','decision-status-detail'])assert.equal(html.split('id="'+id+'"').length-1,1);
});
test('both decision surfaces share status updates and permission gate',()=>{
 assert.ok(view.includes("['live-action','decision-status-text']"));
 assert.ok(view.includes("['live-action-detail','decision-status-detail']"));
 assert.ok(view.includes("$('screen-decision').hidden=!canRun()"));
 assert.ok(view.includes("if(!$('practice-consent').checked){show('Practice permission required'"));
});
