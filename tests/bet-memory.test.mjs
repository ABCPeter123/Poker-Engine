
import test from 'node:test';
import assert from 'node:assert/strict';
import {createBetMemory,updateBetMemory,correctTrackedBet,BET_SEATS,trackedBetLabel,interruptBetMemory,retainedRoundBet,observedHandCommitment} from '../live-practice.js';
const c=candidate=>({candidate});
const r=(value,street='Preflop',options={})=>({street_candidate:street,quality:{},hole_slots:[c('As'),c('Kd')],board_slots:['2c','3h','4d','5s','6h'].map((x,i)=>i<({Preflop:0,Flop:3,Turn:4,River:5})[street]?c(x):null),table_observation:{dealer:{candidate:'hero'},seats:{hero:{bet:value===null?null:{value,approximate:!!options.approximate,ocr_confidence:options.confidence??95},stack:options.stack===undefined?null:{value:options.stack,ocr_confidence:95}}}}});
const step=(s,v,t,street='Preflop',opts={})=>updateBetMemory(s,r(v,street,opts),{capturedAt:t,now:t+100,ocr:opts.ocr??true});
const seed=()=>step(step(step(createBetMemory(),50,100),50,200),50,300);
test('all seats initialize to zero; first increase needs repeat',()=>{let s=createBetMemory();for(const id of BET_SEATS){assert.equal(s.seats[id].value,0);assert.equal(trackedBetLabel(s.seats[id]),'? (unobserved)');}s=step(s,50,100);s=step(s,50,200);assert.equal(s.seats.hero.value,0);s=step(s,50,300);assert.equal(s.seats.hero.value,50);});
test('missing OCR and isolated enormous amount do not replace retained value',()=>{let s=seed();s=step(s,50000,400);assert.equal(s.seats.hero.value,50);s=step(s,null,500);assert.equal(s.seats.hero.value,50);s=step(s,100,600);s=step(s,100,700);assert.equal(s.seats.hero.value,100);});
test('repeated bad high value has a recovery path',()=>{let s=seed();for(const t of [400,500,600])s=step(s,50000,t);assert.equal(s.seats.hero.value,50000);for(const t of [700,800,900]){s=step(s,100,t);assert.equal(s.seats.hero.value,50000);}s=step(s,100,1000);assert.equal(s.seats.hero.value,100);assert.equal(s.seats.hero.source,'correction');});
test('isolated lower values and absent zero do not reduce amount',()=>{let s=seed();s=step(s,0,400);s=step(s,null,500);s=step(s,0,600);assert.equal(s.seats.hero.value,50);});
test('confirmed new street resets all tracked values; transient regression does not',()=>{let s=seed();s=step(s,null,400,'Flop');assert.equal(s.seats.hero.value,50);s=step(s,null,500,'Flop');assert.equal(s.street,'Flop');assert.equal(s.seats.hero.value,0);s=step(s,100,600,'Flop');s=step(s,100,700,'Flop');s=step(s,null,800,'Preflop');assert.equal(s.seats.hero.value,100);s=step(s,100,900,'Flop');assert.equal(s.seats.hero.value,100);s=step(s,null,1000,'Preflop');s=step(s,null,1100,'Preflop');assert.equal(s.seats.hero.value,0);});
test('manual correction blocks in-flight older result',()=>{const s=correctTrackedBet(seed(),'hero',25,1000);assert.equal(s.seats.hero.value,25);assert.equal(step(s,50000,900),s);assert.throws(()=>correctTrackedBet(s,'hero',-1,1200));});
test('low confidence and stale sample cannot seed increase',()=>{let s=seed();s=step(s,50000,400,'Preflop',{confidence:40});assert.equal(s.seats.hero.pending,null);assert.equal(updateBetMemory(s,r(50000),{capturedAt:500,now:7000,ocr:true}),s);});
test('approximate lower amount remains disputed',()=>{let s=seed();for(const t of [400,500,600,700,800])s=step(s,20,t,'Preflop',{approximate:true});assert.equal(s.seats.hero.value,50);});
test('stack conservation supports large increase with two repeated samples',()=>{let s=step(step(step(createBetMemory(),50,100,'Preflop',{stack:19950}),50,200,'Preflop',{stack:19950}),50,300,'Preflop',{stack:19950});s=step(s,5000,400,'Preflop',{stack:15000});s=step(s,5000,500,'Preflop',{stack:15000});assert.equal(s.seats.hero.value,5000);});
test('new preflop hole cards reset after two observations',()=>{let s=seed();for(const t of [400,500])s=updateBetMemory(s,{...r(null),hole_slots:[c('Qs'),c('Jd')]},{capturedAt:t,now:t+100,ocr:true});assert.equal(s.seats.hero.value,0);assert.equal(s.hole,'Jd Qs');});

test('capture interruption drops provisional votes but retains accepted bets',()=>{let s=seed();s=step(s,50000,400);s=step(s,50000,500);s=interruptBetMemory(s);assert.equal(s.seats.hero.value,50);assert.equal(s.seats.hero.pending,null);s=step(s,50000,600);assert.equal(s.seats.hero.value,50);});

test('retained round reading remains visible after missing OCR; forward street archives prior observations',()=>{
 let s=seed();s=step(s,null,400);
 assert.equal(retainedRoundBet(s,'hero','Preflop').value,50);
 s=step(s,null,500,'Flop');assert.equal(retainedRoundBet(s,'hero','Preflop'),undefined);
 s=step(s,null,600,'Flop');
 assert.equal(s.closedRounds.length,1);assert.equal(s.closedRounds[0].seats.hero.value,50);
 assert.equal(observedHandCommitment(s,'hero').value,50);
 s=step(s,100,700,'Flop');s=step(s,100,800,'Flop');
 assert.deepEqual(observedHandCommitment(s,'hero'),{value:150,observedRounds:2,rounds:2,approximate:false,complete:false});
 s=step(s,null,900,'Preflop');s=step(s,null,1000,'Preflop');
 assert.equal(s.closedRounds.length,0);assert.equal(observedHandCommitment(s,'hero'),null);
});
