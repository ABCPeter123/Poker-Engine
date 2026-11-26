import test from 'node:test';import assert from 'node:assert/strict';
import {updateActionEvidence,heroCardPresence} from '../live-practice.js';
const frame=(action,holes=[{candidate:'As'},{candidate:'Kd'}])=>({hole_slots:holes,table_observation:{seats:{left:{status_candidate:action}}}});
const active={phase:'active'};
test('repeated action labels persist without becoming new wager events',()=>{
 let m=updateActionEvidence(null,frame('Call'),active,'Flop',100);
 m=updateActionEvidence(m,frame('Call'),active,'Flop',200);
 assert.deepEqual(m.seats.left,{action:'Call',firstSeen:100,lastSeen:200});
 m=updateActionEvidence(m,frame(null),active,'Flop',300);
 assert.equal(m.seats.left.action,'Call');
 m=updateActionEvidence(m,frame('Fold'),active,'Flop',400);
 m=updateActionEvidence(m,frame('Call'),active,'Flop',500);
 assert.equal(m.seats.left.action,'Fold');
 m=updateActionEvidence(m,frame(null),{phase:'active',started:true},'Preflop',600);
 assert.equal(m.seats.left,undefined);
});
test('physical absence is distinct from unreadable visible cards',()=>{
 assert.equal(heroCardPresence(frame(null,[null,null])),'absent');
 assert.equal(heroCardPresence(frame(null,[{candidate:null},null])),'visible');
 assert.equal(heroCardPresence({}),'unknown');
});
