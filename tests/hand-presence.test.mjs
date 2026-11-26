import test from 'node:test';import assert from 'node:assert/strict';
import {updateHandPresence,updateBetMemory,createBetMemory,observedHandCommitment} from '../live-practice.js';
const c=candidate=>({candidate});
const frame=(street='Preflop',holes=[c('As'),c('Kd')],bet=50,dealer='hero')=>({hole_slots:holes,board_slots:['2c','3h','4d','5s','6h'].map((x,i)=>i<({Preflop:0,Flop:3,Turn:4,River:5})[street]?c(x):null),street_candidate:street,quality:{},table_observation:{dealer:{candidate:dealer},seats:{hero:{bet:bet===null?null:{value:bet,ocr_confidence:95}}}}});
test('missing rank is not absence; brief disappearance does not end hand',()=>{
 let h=updateHandPresence(null,frame(),100);assert.equal(h.started,true);
 h=updateHandPresence(h,frame('Preflop',[c(null),c(null)]),200);assert.equal(h.phase,'active');
 h=updateHandPresence(h,frame('Preflop',[null,null]),300);
 h=updateHandPresence(h,frame('Preflop',[null,null]),600);assert.equal(h.phase,'active');
 h=updateHandPresence(h,frame(),800);assert.equal(h.started,false);assert.equal(h.absentCount,0);
});
test('ledger survives a false preflop, skipped street and confirmed disappearance',()=>{
 let h=null,b=createBetMemory();
 function step(r,t){h=updateHandPresence(h,r,t);b=updateBetMemory(b,r,{capturedAt:t,now:t+1,ocr:true,hand:h});}
 step(frame(),100);step(frame(),200);step(frame(),300);
 assert.equal(observedHandCommitment(b,'hero').value,50);
 step(frame('Preflop',[c('As'),c('Kd')],50,'left'),400);assert.equal(b.seats.hero.value,50);
 step(frame('Turn',undefined,100),500);step(frame('Turn',undefined,100),600);step(frame('Turn',undefined,100),700);
 assert.deepEqual(observedHandCommitment(b,'hero'),{value:150,observedRounds:2,rounds:3,approximate:false,complete:false});
 assert.equal(b.closedRounds[1].skipped,true);
 step(frame('Preflop',[null,null],null),800);step(frame('Preflop',[null,null],null),1300);step(frame('Preflop',[null,null],null),1800);
 assert.equal(h.phase,'ended');assert.equal(observedHandCommitment(b,'hero').value,150);
 step(frame('Preflop',[c('Qs'),c('Jh')],null),2000);assert.equal(h.started,true);assert.equal(observedHandCommitment(b,'hero'),null);
});
test('same showdown cards returning after prolonged absence do not reset ledger',()=>{
 let h=updateHandPresence(null,frame('River'),100);
 for(const t of [200,700,1200])h=updateHandPresence(h,frame('River',[null,null]),t);
 assert.equal(h.phase,'ended');h=updateHandPresence(h,frame('River'),1400);assert.equal(h.started,false);assert.equal(h.phase,'active');
});
