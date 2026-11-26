import test from 'node:test';import assert from 'node:assert/strict';
import {updateTurnMemory,conditionalDeck,updateCardMemory,candidateCards} from '../live-practice.js';
const hand={phase:'active'},c=candidate=>({candidate});
const frame={hole_slots:[c('8s'),c('9c')],board_slots:[c('7s'),c('6h'),c('4s'),c('Ts'),null],street_candidate:'Turn',quality:{}};
test('turn display retains fading ring until another cue or hand boundary',()=>{
 let m=updateTurnMemory(null,{table_observation:{turn_candidate:'hero'}},hand,'Turn',100);
 m=updateTurnMemory(m,{},hand,'Turn',200);assert.equal(m.seat,'hero');assert.equal(m.seen,100);
 m=updateTurnMemory(m,{table_observation:{turn_candidate:'left'}},hand,'Turn',300);assert.equal(m.seat,'left');
 assert.equal(updateTurnMemory(m,{},hand,'River',400),null);
 assert.equal(updateTurnMemory(m,{}, {phase:'ended'},'Turn',400),null);
});
test('conditional deck fills only independently confirmed recent isolated card misses',()=>{
 const prior=updateCardMemory(updateCardMemory(null,frame,100),frame,200);
 const miss={...frame,hole_slots:[c(null),c('9c')]};
 const m=updateCardMemory(prior,miss,300);
 const d=conditionalDeck(miss,m,hand,'Turn',300);
 assert.equal(d.key,candidateCards(frame).key);assert.deepEqual(d.retained,[0]);
 assert.equal(conditionalDeck(miss,m,{phase:'ended'},'Turn',300),null);
 assert.equal(conditionalDeck(miss,m,hand,'River',300),null);
 assert.equal(conditionalDeck(miss,m,hand,'Turn',7000),null);
 const absent={...frame,hole_slots:[null,c('9c')]},am=updateCardMemory(prior,absent,300);
 assert.equal(conditionalDeck(absent,am,hand,'Turn',300),null);
 assert.equal(conditionalDeck(absent,am,hand,'Turn',300,candidateCards(frame)).key,candidateCards(frame).key);
 const conflict={...miss,hole_slots:[c(null),c('3c')]};
 assert.equal(conditionalDeck(conflict,updateCardMemory(prior,conflict,300),hand,'Turn',300),null);
});
