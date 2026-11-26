import test from 'node:test';import assert from 'node:assert/strict';
import {practicePanelModel} from '../practice-decision.js';
const c=value=>({value,approximate:false});
const seats=Object.fromEntries(['hero','left','upper_left','upper_right','right'].map(id=>[id,{bet:c(id==='hero'?50:500),stack:c(20000)}]));
test('complete visible preflop wager subtotal supports explicitly conditional calculation',()=>{
 const r=practicePanelModel({street:'Preflop',seats,prompt:c(450),equities:[.25,.30]});
 assert.equal(r.pot,2050);assert.equal(r.call,450);assert.equal(r.source,'visible preflop wagers');assert.equal(r.unanimous,'Call');assert.equal(r.conditional,true);
});
test('missing or contradictory evidence does not invent a price or pot',()=>{
 assert.equal(practicePanelModel({street:'Flop',seats,prompt:c(450),equities:[.3]}).reason,'Pot unavailable');
 assert.equal(practicePanelModel({street:'Preflop',seats,prompt:c(400),equities:[.3]}).reason,'Call price and wagers disagree');
 const partial={...seats,right:{bet:null}};
 assert.equal(practicePanelModel({street:'Preflop',seats:partial,equities:[.3]}).reason,'Call price unreadable');
 const r=practicePanelModel({street:'Flop',seats:partial,pot:c(2000),prompt:c(450),equities:[.1,.3]});
 assert.equal(r.unanimous,null);
 assert.equal(r.source,'displayed pot');
});

test('first-to-act and folded seats do not block an explicit price with partial visible preflop wagers',()=>{
 const partial={hero:{stack:c(20000)},left:{bet:c(25)},right:{bet:c(50)},upper_left:{status_candidate:'Fold'}};
 const result=practicePanelModel({street:'Preflop',seats:partial,prompt:c(50),equities:[.5,.6]});
 assert.equal(result.pot,75);
 assert.equal(result.call,50);
 assert.equal(result.partial,true);
 assert.equal(result.wagerCount,2);
 assert.equal(result.unanimous,'Call');
 assert.equal(result.source,'partial visible preflop wagers');
 assert.equal(practicePanelModel({street:'Preflop',seats:partial,equities:[.5]}).reason,'Call price unreadable');
});
test('an explicit price needs no opponent wagers when the pot is displayed',()=>{
 const r=practicePanelModel({street:'Flop',pot:c(1000),prompt:c(0),seats:{hero:{stack:c(1000)}},equities:[.1,.2]});
 assert.equal(r.unanimous,'Check');
 assert.equal(r.partial,false);
 assert.equal(r.wagerCount,0);
});
