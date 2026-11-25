import test from 'node:test';
import assert from 'node:assert/strict';
import {currentNumericSample,freshBetValue,createBetMemory,updateBetMemory} from '../live-practice.js';
const r=street=>({street_candidate:street,board_slots:street==='Preflop'?Array(5).fill(null):[{candidate:'As'},{candidate:'Kd'},{candidate:'Qc'},null,null],hole_slots:[{candidate:'7s'},{candidate:'8d'}],table_observation:{seats:{}},number_candidates:{pot:{candidate:{value:500}}}});
const frame=(s,street,t)=>updateBetMemory(s,r(street),{capturedAt:t,now:t+1});
test('prior numeric evidence cleared at first uncertain boundary and cannot return on confirmation',()=>{
 let s=createBetMemory();s=frame(s,'Preflop',100);const prior=s;s=frame(s,'Preflop',200);
 const sample=currentNumericSample(null,r('Preflop'),s,prior,{capturedAt:200,now:201,sampled:true});assert.equal(sample.table.pot.value,500);
 const first=frame(s,'Flop',300);assert.equal(currentNumericSample(sample,r('Flop'),first,s,{capturedAt:300,now:301}),null);
 const second=frame(first,'Flop',400);assert.equal(currentNumericSample(sample,r('Flop'),second,first,{capturedAt:400,now:401}),null);
 assert.equal(second.generation,s.generation+1);
});
test('fresh zero distinct from expired or uncertain wager',()=>{
 const s={street:'Flop',uncertain:false,seats:{hero:{observed:true,value:0,lastSeen:100}}};
 assert.equal(freshBetValue(s,'hero','Flop',101),0);
 assert.equal(freshBetValue(s,'hero','Flop',5101),undefined);
 assert.equal(freshBetValue({...s,uncertain:true},'hero','Flop',101),undefined);
});
test('delayed numeric results cannot become fresh',()=>{
 const s={street:'Flop',generation:1};
 assert.equal(currentNumericSample(null,r('Flop'),s,s,{capturedAt:100,now:5200,sampled:true}),null);
});
