import test from 'node:test';import assert from 'node:assert/strict';import {snapshotCoverage,reconcileSnapshots,BET_SEATS,directNumericSnapshot} from '../live-practice.js';
const c=value=>({value,approximate:false,ocr_confidence:95});
const card=candidate=>({candidate});
function frame(pot=100,stack=1000,bet=20){
 return {street_candidate:'Preflop',hole_slots:[card('As'),card('Kd')],board_slots:Array(5).fill(null),quality:{},number_candidates:{pot:{candidate:c(pot)}},table_observation:{dealer:{candidate:'left'},turn_candidate:'hero',seats:Object.fromEntries(BET_SEATS.map(id=>[id,{stack:c(id==='hero'?stack:1000),bet:c(id==='hero'?bet:20)}]))}};
}
test('coverage distinguishes stale, manual, approximate and automatic candidates',()=>{
 const f=frame();f.table_observation.seats.hero.bet.approximate=true;
 let r=snapshotCoverage(f,{'left.stack':123},true,true);
 assert.equal(r.total,20);assert.equal(r.counts.manual,1);assert.equal(r.counts.approximate,1);assert.equal(r.counts.candidate,18);assert.equal(r.automaticAccuracyVerified,false);
 r=snapshotCoverage(f,{'left.stack':123},false,false);assert.equal(r.counts.unknown,19);assert.equal(r.counts.manual,1);
});
test('conservation supports a direct observation, not exact inference',()=>{
 const a={at:100,result:frame()},b={at:200,result:frame(150,950,70)};
 let r=reconcileSnapshots(a,b,{potIncludesBets:true});assert.equal(r.status,'consistent');assert.equal(r.seats.hero.implied,70);
 b.result.table_observation.seats.hero.bet=null;
 r=reconcileSnapshots(a,b,{potIncludesBets:true});assert.equal(r.seats.hero.status,'hypothesis');assert.equal(r.seats.hero.implied,70);
 b.result.table_observation.seats.hero.bet=c(80);
 r=reconcileSnapshots(a,b,{potIncludesBets:true});assert.equal(r.status,'conflict');
});
test('no inference with uncertain identity, pot, stack or elapsed time',()=>{
 const a={at:100,result:frame()},b={at:200,result:frame(150,950,70)};
 assert.equal(reconcileSnapshots(a,b).status,'unavailable');
 assert.equal(reconcileSnapshots(a,{...b,at:1200},{potIncludesBets:true}).status,'unavailable');
 b.result.number_candidates.pot.candidate.value=160;
 assert.equal(reconcileSnapshots(a,b,{potIncludesBets:true}).status,'unavailable');
 b.result.number_candidates.pot.candidate.value=150;b.result.hole_slots[0]=card('Ah');
 assert.equal(reconcileSnapshots(a,b,{potIncludesBets:true}).status,'unavailable');
});

test('raw numeric evidence remains visible without round confirmation, but expires or clears on OCR error',()=>{
 const f=frame();
 assert.equal(directNumericSnapshot(f,'sampled',100,200).seats.hero.stack.value,1000);
 assert.equal(directNumericSnapshot(f,'sampled',100,1101),null);
 assert.equal(directNumericSnapshot(f,'failed',100,200),null);
 assert.equal(directNumericSnapshot(f,'disabled',100,200),null);
});
