import test from 'node:test';import assert from 'node:assert/strict';
import {updateTurnMemory,conditionalDeck,updateCardMemory,candidateCards,deckObservationStatus} from '../live-practice.js';
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
 assert.equal(conditionalDeck(absent,am,hand,'Turn',300).key,candidateCards(frame).key);
 assert.equal(conditionalDeck(absent,{...am,confirmedDeck:null},hand,'Turn',300),null);
 assert.equal(conditionalDeck(absent,am,hand,'Turn',300,candidateCards(frame)).key,candidateCards(frame).key);
 const conflict={...miss,hole_slots:[c(null),c('3c')]};
 assert.equal(conditionalDeck(conflict,updateCardMemory(prior,conflict,300),hand,'Turn',300),null);
});

test('retained preflop ten survives a cleared simulation gate only with independent repeated deck evidence',()=>{
 const f={hole_slots:[c('3c'),c('Ts')],board_slots:Array(5).fill(null),street_candidate:'Preflop',quality:{}};
 const seed=updateCardMemory(updateCardMemory(null,f,100),f,200);
 const miss={...f,hole_slots:[c('3c'),null]};
 const held=updateCardMemory(seed,miss,300);
 assert.equal(held.confirmedDeck.at,200);
 assert.equal(conditionalDeck(miss,held,hand,'Preflop',300,null).key,candidateCards(f).key);
 assert.equal(conditionalDeck(miss,{...held,confirmedDeck:null},hand,'Preflop',300,null),null);
 assert.equal(conditionalDeck(miss,held,hand,'Preflop',5300,null),null);
 const conflict=updateCardMemory(held,{...miss,hole_slots:[c('2c'),null]},400);
 assert.equal(conflict.confirmedDeck,null);
 assert.equal(conditionalDeck(miss,held,{phase:'ended'},'Preflop',300,null),null);
 assert.equal(deckObservationStatus({candidate:null,memory:held,street:'Flop',fresh:true}),'Retained card · street not confirmed');
 assert.equal(deckObservationStatus({candidate:null,memory:held,street:'Preflop',fresh:true}),'Retained card · deck validation pending');
});
