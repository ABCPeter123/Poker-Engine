import test from 'node:test';import assert from 'node:assert/strict';
import {observationSummary,observationScenarioCounts} from '../live-practice.js';
test('partial observations are available without pot confirmation or count selection',()=>{
 const r={number_candidates:{pot:{candidate:{value:250,approximate:false}}},table_observation:{seats:{hero:{stack:{value:1000},bet:{value:50}},left:{card_visible_candidate:true}}}};
 const s=observationSummary(r,{},null,100,true,true);
 assert.equal(s.pot.value,250);assert.equal(s.stackCount,1);assert.equal(s.betCount,1);assert.deepEqual([s.range.min,s.range.max],[1,4]);
 assert.equal(s.stakes.find(x=>x.id==='right').bet,null);
});
test('manual zero, historical amount, and approximate candidate remain distinct',()=>{
 const m={fields:{'hero.stack':{value:700,seen:0,votes:2,pending:null}}};
 const r={number_candidates:{pot:{candidate:{value:1200,approximate:true}}}};
 const s=observationSummary(r,{'hero.bet':0},m,2000,true,true);
 assert.deepEqual(s.pot,{value:1200,source:'approximate candidate'});
 assert.deepEqual(s.stakes[0].bet,{value:0,source:'manual'});
 assert.deepEqual(s.stakes[0].stack,{value:700,source:'last observed'});
 const stale=observationSummary(r,{},m,2000,false,false);assert.equal(stale.pot,null);
});

test('unresolved opponent counts produce conditional scenarios without pretending to confirm a count',()=>{
 assert.deepEqual(observationScenarioCounts(null,{min:0,max:4}),[1,2,3,4]);
 assert.deepEqual(observationScenarioCounts(null,{min:2,max:3}),[2,3]);
 assert.deepEqual(observationScenarioCounts(null,{min:3,max:3}),[3]);
 assert.deepEqual(observationScenarioCounts(null,{min:0,max:0}),[]);
 assert.deepEqual(observationScenarioCounts(2,{min:0,max:4}),[2]);
 assert.deepEqual(observationScenarioCounts(null,{min:4,max:1}),[]);
});

test('unrendered central pot does not hide the visible wager subtotal',()=>{
 const seats=Object.fromEntries(['hero','left','upper_left','upper_right','right'].map(id=>[id,{bet:{value:id==='hero'?50:500,approximate:false}}]));
 const result={street_candidate:'Preflop',table_observation:{seats}};
 let s=observationSummary(result,{},null,100,true,true);
 assert.equal(s.pot,null);
 assert.deepEqual(s.visibleWagers,{value:2050,count:5,approximate:false,complete:true});
 // A separately displayed pot is not added to outstanding wagers.
 result.number_candidates={pot:{candidate:{value:2000,approximate:false}}};
 s=observationSummary(result,{},null,100,true,true);
 assert.equal(s.pot.value,2000);assert.equal(s.visibleWagers.value,2050);
 delete seats.right.bet;seats.left.bet.approximate=true;
 s=observationSummary(result,{},null,100,true,true);
 assert.deepEqual(s.visibleWagers,{value:1550,count:4,approximate:true,complete:false});
 assert.equal(observationSummary(result,{},null,100,false,false).visibleWagers,null);
 assert.equal(observationSummary(result,{},null,100,true,false).visibleWagers,null);
});
