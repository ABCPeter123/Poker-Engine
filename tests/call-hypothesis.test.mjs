import test from 'node:test';import assert from 'node:assert/strict';
import {observedCallHypothesis} from '../live-practice.js';
const frame=(turn,action,bet=null)=>({hole_slots:[{candidate:'As'},{candidate:'Kd'}],board_slots:Array(5).fill(null),street_candidate:'Preflop',quality:{},table_observation:{turn_candidate:turn,seats:{left:{status_candidate:action,bet},right:{bet:{value:100,approximate:false}}}}});
test('an explicit new call can support an isolated conditional prior wager hypothesis',()=>{
 const a=frame('left',null),b=frame('hero','Call');
 const h=observedCallHypothesis(a,b,100,200);
 assert.equal(h.value,100);assert.equal(h.seat,'left');assert.match(h.source,/assumes/);
 assert.equal(observedCallHypothesis(a,frame('hero',null),100,200),null);
 assert.equal(observedCallHypothesis(a,frame('hero','All-in'),100,200),null);
 assert.equal(observedCallHypothesis(a,frame('hero','Call',{value:25}),100,200),null);
 assert.equal(observedCallHypothesis(frame('left','Call'),b,100,200),null);
 assert.equal(observedCallHypothesis(a,b,100,1200),null);
});
