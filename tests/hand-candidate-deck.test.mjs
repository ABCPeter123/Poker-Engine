import test from 'node:test';import assert from 'node:assert/strict';
import {handCandidateDeck,updateDisplayEvidence,createBetMemory} from '../live-practice.js';
import {effectiveCards} from '../manual-observations.js';
import {practiceActionFallback} from '../practice-decision.js';
const c=candidate=>({candidate}), hand={phase:'active'},state=createBetMemory();
const frame={hole_slots:[c('3s'),c('3c')],board_slots:['9h','6d','2c','8d','7d'].map(c),street_candidate:'River',quality:{}};
test('river screenshot retained nine remains usable for whole hand',()=>{
 let m=updateDisplayEvidence(null,frame,state,state,{at:100,hand});
 const miss={...frame,board_slots:[c(null),...frame.board_slots.slice(1)]};
 for(let at=200;at<=12000;at+=200)m=updateDisplayEvidence(m,miss,state,state,{at,hand});
 const d=handCandidateDeck(effectiveCards(miss,{}),m,hand);
 assert.deepEqual(d.labels.board,['9h','6d','2c','8d','7d']);
 assert.deepEqual(d.retained,[2]);assert.equal(d.street,'River');
 assert.equal(handCandidateDeck(effectiveCards(miss,{}),m,{phase:'ended'}),null);
 const corrected={'board.0':'Th'};
 assert.equal(handCandidateDeck(effectiveCards(miss,corrected),m,hand,corrected).labels.board[0],'Th');
});
test('hand inventory uses new readable identities and does not invent an unseen river',()=>{
 let m=updateDisplayEvidence(null,frame,state,state,{at:100,hand});
 const changed={...frame,board_slots:[c('Th'),...frame.board_slots.slice(1)]};
 m=updateDisplayEvidence(m,changed,state,state,{at:200,hand});
 const miss={...frame,board_slots:[null,...frame.board_slots.slice(1)]};
 assert.equal(handCandidateDeck(effectiveCards(miss,{}),m,hand).labels.board[0],'Th');
 const turn={...frame,board_slots:[...frame.board_slots.slice(0,4),null],street_candidate:'Turn'};
 const mt=updateDisplayEvidence(null,turn,state,state,{at:100,hand});
 const river={...frame,board_slots:[...frame.board_slots.slice(0,4),c(null)]};
 assert.equal(handCandidateDeck(effectiveCards(river,{}),mt,hand),null);
 const duplicate={...frame,hole_slots:[c('3c'),c('3c')]};
 assert.equal(handCandidateDeck(effectiveCards(duplicate,{}),m,hand),null);
 const reset=updateDisplayEvidence(m,turn,state,state,{at:300,hand:{...hand,started:true}});
 assert.equal(reset.fields['board.4'].value,null);
});
test('fallback is a separate conservative local practice action only on observed legal turn',()=>{
 const a={fresh:true,turn:'hero',heroVisible:true,prompt:{value:11300,approximate:true},price:null,stack:24200};
 assert.equal(practiceActionFallback(a).action,'FOLD');
 assert.equal(practiceActionFallback({...a,prompt:{value:0,source:'explicit check prompt'}}).action,'CHECK');
 for(const b of [{fresh:false},{turn:'right'},{heroVisible:false},{stack:0},{allIn:true},{prompt:null},{price:{reason:'Call price and wagers disagree'}}])assert.equal(practiceActionFallback({...a,...b}),null);
});
