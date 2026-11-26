import test from 'node:test';import assert from 'node:assert/strict';
import {raiseBounds,start,legal,act} from '../table-engine.js';
import {conservativeRaiseBounds,observePracticeBlind,practiceRaiseSizing,sizedPracticeHeadline} from '../practice-decision.js';
const state={bet:300,committed:100,stack:1000,bb:50,minIncrement:200,actedAt:100,opponentCanAct:true};
test('exact simulator raise-to versus chips added, short all-in and reopened action',()=>{
 const r=raiseBounds(state);assert.equal(r.minTo,500);assert.equal(r.maxTo,1100);assert.equal(r.legalMinTo,500);assert.equal(r.raise,true);
 assert.equal(raiseBounds({...state,bet:350,actedAt:300}).raise,false);
 assert.equal(raiseBounds({...state,bet:500,actedAt:300}).minTo,700);
 assert.equal(raiseBounds({...state,bet:500,actedAt:300}).raise,true);
 const short=raiseBounds({...state,stack:300});assert.equal(short.shortAllInOnly,true);assert.equal(short.legalMinTo,400);
 assert.equal(raiseBounds({...state,opponentCanAct:false}).raise,false);
 assert.equal(raiseBounds({...state,bet:0,committed:0,actedAt:null,minIncrement:50}).minTo,50);
 assert.throws(()=>raiseBounds({...state,minIncrement:0}));
});
test('actual local simulator validates raises against its exact bounds',()=>{
 let s=start({stacks:[1000,1000,1000],hero:0,button:0,sb:25,bb:50});
 assert.equal(legal(s).minTo,100);
 assert.throws(()=>act(s,'raise',99));
 s=act(s,'raise',150);assert.equal(legal(s).minTo,250);
});
test('screen bound is conservative not a claimed minimum',()=>{
 const args={street:'Preflop',heroBet:25,stack:975,call:75,bigBlind:50,raiseVisible:true};
 const r=conservativeRaiseBounds(args);
 assert.deepEqual(r,{safeTo:200,maxTo:1000,additional:175,highest:100,increment:100,exactMinimum:false,conditional:true});
 assert.equal(conservativeRaiseBounds({...args,raiseVisible:false}),null);
 assert.equal(conservativeRaiseBounds({...args,stack:100}),null);
 assert.equal(conservativeRaiseBounds({...args,heroBet:null}),null);
 assert.equal(conservativeRaiseBounds({...args,street:'Turn',bigBlind:null}),null);
 const open=conservativeRaiseBounds({...args,street:'Flop',heroBet:0,call:0,bigBlind:50});
 assert.equal(open.safeTo,50);
});
test('blind observations require consistent exact non-all-in evidence within a hand',()=>{
 const f={street_candidate:'Preflop',table_observation:{seats:{left:{status_candidate:'Big blind',bet_chip_present:true,bet:{value:50},stack:{value:1000}}}}};
 let b=observePracticeBlind(null,f,{phase:'active',started:true},100);assert.equal(b.confirmed,false);
 b=observePracticeBlind(b,f,{phase:'active'},200);assert.equal(b.confirmed,true);
 assert.equal(observePracticeBlind(b,{street_candidate:'Flop'},{phase:'active'},300),b);
 assert.equal(observePracticeBlind(b,{street_candidate:'Flop'},{phase:'active',started:true},400),null);
 assert.equal(observePracticeBlind(b,f,{phase:'ended'},400),null);
});

test('opening wager can be sized from explicit zero evidence and a known blind',()=>{
 const args={street:'Flop',hero:{stack:{value:1000},bet_chip_present:false},call:0,bigBlind:50,raiseVisible:true,zeroWagerEvidence:true};
 assert.equal(practiceRaiseSizing(args).bounds.safeTo,50);
 assert.equal(practiceRaiseSizing(args).assumedZero,true);
 assert.equal(practiceRaiseSizing({...args,zeroWagerEvidence:false}).reason,'Your current-street wager is unreadable');
 assert.equal(practiceRaiseSizing({...args,bigBlind:null}).reason,'Big blind not established');
 assert.equal(practiceRaiseSizing({...args,hero:{...args.hero,bet:{value:25,approximate:true}}}).reason,'Your current-street wager is unreadable');
});
test('a practice raise headline always includes a size or falls back to baseline',()=>{
 const model={call:0,unanimous:'Check',outcomes:['Check']};
 const raise={action:'Raise'};
 assert.deepEqual(sizedPracticeHeadline(model,raise,{reason:'Big blind not established'}),{text:'Check',raise:false,reason:'Big blind not established'});
 assert.equal(sizedPracticeHeadline(model,raise,{bounds:{safeTo:50}}).text,'Raise to 50 (conditional)');
});
test('rounded positive stack does not prevent blind observation',()=>{
 const f={street_candidate:'Preflop',table_observation:{seats:{left:{status_candidate:'Big blind',bet_chip_present:true,bet:{value:50},stack:{value:10000,approximate:true}}}}};
 let b=observePracticeBlind(null,f,{phase:'active',started:true},100);
 b=observePracticeBlind(b,f,{phase:'active'},200);
 assert.equal(b.confirmed,true);assert.equal(b.value,50);
});
