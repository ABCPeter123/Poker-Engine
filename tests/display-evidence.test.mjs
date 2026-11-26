import test from 'node:test';import assert from 'node:assert/strict';import {updateDisplayEvidence,displayEvidenceValues,observedOpponentRange,createBetMemory} from '../live-practice.js';
const r=(value,card='3s')=>({hole_slots:[null,null],board_slots:[{candidate:card},null,null,null,null],quality:{},table_observation:{seats:{hero:{stack:value===null?null:{value}},left:{card_visible_candidate:true},upper_left:{status_candidate:'Fold'}}}});
const s=createBetMemory(),step=(m,v,t,card='3s',state=s,prior=s)=>updateDisplayEvidence(m,r(v,card),state,prior,{at:t,sampled:true});
test('display retains readings on misses, not stale action evidence',()=>{
 let m=step(null,19825,100);m=step(m,19825,200);m=step(m,null,300,null);
 let d=displayEvidenceValues(m,1500);
 assert.equal(d.values['hero.stack'],19825);assert.equal(d.details['hero.stack'].state,'last seen');assert.equal(d.values['board.0'],'3s');
 m=step(m,1982,1600,'8s');d=displayEvidenceValues(m,1600);
 assert.equal(d.values['hero.stack'],19825);assert.equal(d.details['hero.stack'].state,'disputed');assert.equal(d.values['board.0'],'3s');
 m=step(m,1982,1700,'8s');assert.equal(displayEvidenceValues(m,1700).values['hero.stack'],1982);
});
test('confirmed new hand clears old values; out-of-order data ignored',()=>{
 let m=step(null,19825,100);assert.equal(step(m,12,99),m);
 const prior={...s,street:'River',generation:1},next={...s,street:'Preflop',generation:2};
 m=step(m,null,200,null,next,prior);
 assert.equal(displayEvidenceValues(m,200).values['hero.stack'],undefined);
});
test('participant observations do not invent empty or folded seats',()=>{
 const a=observedOpponentRange(r(10));
 assert.deepEqual([a.min,a.max],[1,3]);assert.deepEqual(a.excluded,['upper_left']);
 const b=observedOpponentRange(r(10),{'right.participation':'Empty seat','upper_right.status':'Playing'});
 assert.deepEqual([b.min,b.max],[2,2]);
});

test('greyed avatars and empty chairs narrow the count, silhouettes do not',()=>{
 const f=r(10);f.seat_evidence={seats:{right:{avatar_appearance:{candidate:'dimmed'}},upper_right:{avatar_appearance:{candidate:'silhouette'}}}};
 let result=observedOpponentRange(f);
 assert.deepEqual([result.min,result.max],[1,2]);
 assert.ok(result.excluded.includes('right'));
 f.table_observation.seats.upper_right={card_visible_candidate:true};
 result=observedOpponentRange(f);assert.deepEqual([result.min,result.max],[2,2]);
 f.table_observation.seats.right={turn_candidate:true};
 result=observedOpponentRange(f);assert.deepEqual([result.min,result.max],[2,3]);assert.ok(result.unknown.includes('right'));
 assert.deepEqual(observedOpponentRange(f,{'right.status':'Fold'}).excluded.sort(),['right','upper_left']);
});
