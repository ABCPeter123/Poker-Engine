import test from 'node:test';import assert from 'node:assert/strict';
import {updateActionEvidence,heroCardPresence,updateHeroWagerEvidence} from '../live-practice.js';
const frame=(action,holes=[{candidate:'As'},{candidate:'Kd'}])=>({hole_slots:holes,table_observation:{seats:{left:{status_candidate:action}}}});
const active={phase:'active'};
test('repeated action labels persist without becoming new wager events',()=>{
 let m=updateActionEvidence(null,frame('Call'),active,'Flop',100);
 m=updateActionEvidence(m,frame('Call'),active,'Flop',200);
 assert.deepEqual(m.seats.left,{action:'Call',firstSeen:100,lastSeen:200,street:'Flop'});
 m=updateActionEvidence(m,frame(null),active,'Flop',300);
 assert.equal(m.seats.left.action,'Call');
 m=updateActionEvidence(m,frame('Fold'),active,'Flop',400);
 m=updateActionEvidence(m,frame('Call'),active,'Flop',500);
 assert.equal(m.seats.left.action,'Fold');
 m=updateActionEvidence(m,frame(null),active,'Turn',550);
 assert.equal(m.seats.left.action,'Fold');
 m=updateActionEvidence(m,frame(null),{phase:'active',started:true},'Preflop',600);
 assert.equal(m.seats.left,undefined);
});
test('physical absence is distinct from unreadable visible cards',()=>{
 assert.equal(heroCardPresence(frame(null,[null,null])),'absent');
 assert.equal(heroCardPresence(frame(null,[{candidate:null},null])),'visible');
 assert.equal(heroCardPresence({}),'unknown');
});

test('explicit hero fold is recorded even when hole cards disappear',()=>{
 const r={hole_slots:[null,null],table_observation:{seats:{hero:{status_candidate:'Fold'}}}};
 const m=updateActionEvidence(null,r,active,'Flop',100);
 assert.equal(m.seats.hero.action,'Fold');
});
test('conflicted text does not overwrite accepted action',()=>{
 let m=updateActionEvidence(null,frame('Call'),active,'Flop',100);
 m=updateActionEvidence(m,{...frame('Raise'),table_observation:{seats:{left:{status_candidate:'Raise',status_reader_conflict:true}}}},active,'Flop',200);
 assert.equal(m.seats.left.action,'Call');
 m=updateActionEvidence(m,frame('Call'),active,'Turn',300);
 assert.equal(m.seats.left.street,'Flop');
});
test('hero accepted wager delta is retained independently of action text',()=>{
 const state=(value,lastSeen)=>({street:'Flop',generation:1,uncertain:false,seats:{hero:{observed:true,value,lastSeen,approximate:false}}});
 const a=state(200,100),b=state(600,200);
 const x=updateHeroWagerEvidence(null,a,b,active,200);
 assert.deepEqual(x,{street:'Flop',before:200,after:600,added:400,at:200});
 assert.equal(updateHeroWagerEvidence(x,b,b,active,300),x);
 assert.equal(updateHeroWagerEvidence(x,b,{...state(900,400),generation:2},active,400),x);
 assert.equal(updateHeroWagerEvidence(x,b,b,{...active,started:true},500),null);
});
