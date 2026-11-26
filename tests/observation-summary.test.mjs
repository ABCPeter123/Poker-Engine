import test from 'node:test';import assert from 'node:assert/strict';
import {observationSummary} from '../live-practice.js';
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
