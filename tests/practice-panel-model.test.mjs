import test from 'node:test';import assert from 'node:assert/strict';
import {practicePanelModel,practiceHeadline,conditionalRaiseComparison,observedCallPrice,roundedCallObservation,roundedPracticeScenario,practicePriceHeadline} from '../practice-decision.js';
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
 assert.equal(practicePanelModel({street:'Preflop',seats:partial,equities:[.3]}).pricePartial,true);
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

test('partial observations return a conditional practice headline instead of a missing-pot placeholder',()=>{
 const result=practicePanelModel({street:'Preflop',seats:{upper_left:{bet:c(25)},upper_right:{bet:c(50)},right:{bet:c(50)}},prompt:c(50),equities:[.245,.159,.129]});
 assert.equal(result.partial,true);
 assert.deepEqual(practiceHeadline(result),{action:'Fold',sensitive:true,policy:'all scenarios agree'});
});
test('disagreeing scenarios use the conservative model baseline and mark sensitivity',()=>{
 const result=practicePanelModel({street:'Flop',pot:c(200),prompt:c(50),seats:{},equities:[.3,.1]});
 assert.deepEqual(practiceHeadline(result),{action:'Fold',sensitive:true,policy:'conservative scenario'});
 assert.equal(practiceHeadline({reason:'Pot unavailable'}),null);
});

test('raise comparison is conditional on visible raise and consistent positive extra-chip EV',()=>{
 const model=practicePanelModel({street:'Turn',pot:c(250),prompt:c(50),seats:{hero:{stack:c(1000)}},equities:[.65,.50]});
 const args={model,counts:[2,3],equities:[.65,.50],stack:1000,raiseVisible:true};
 const r=conditionalRaiseComparison(args);
 assert.equal(r.action,'Raise');assert.equal(r.sizeVerified,false);
 assert.equal(conditionalRaiseComparison({...args,raiseVisible:false}),null);
 assert.equal(conditionalRaiseComparison({...args,stack:50}),null);
 assert.equal(conditionalRaiseComparison({...args,equities:[.65,.1]}).action,null);
 assert.equal(conditionalRaiseComparison({...args,model:{...model,partial:true}}).action,null);
});

test('four visible wagers and a missing seat recover the reported 400 call price',()=>{
 const s={hero:{bet:c(200),stack:c(23800)},upper_left:{bet:c(200)},upper_right:{bet:c(600)},right:{bet:c(600)}};
 assert.deepEqual(observedCallPrice(s,null,['left']),{value:400,source:'visible round wagers',partial:false});
 assert.deepEqual(observedCallPrice(s,null),{value:400,source:'partial round wager difference',partial:true});
 const m=practicePanelModel({street:'Preflop',seats:s,excluded:['left'],equities:[.324]});
 assert.equal(m.call,400);assert.equal(m.pot,1600);assert.equal(m.partial,true);
 assert.equal(observedCallPrice(s,c(300),['left']).reason,'Call price and wagers disagree');
 assert.equal(observedCallPrice(s,c(500)).value,500);
});
test('missing or rounded hero wager cannot establish a difference; partial equal bets cannot establish a check',()=>{
 assert.equal(observedCallPrice({hero:{bet:c(200)},right:{bet:c(200)}},null).reason,'Call price unreadable');
 assert.equal(observedCallPrice({hero:{bet:{value:200,approximate:true}},right:{bet:c(600)}},null).reason,'Rounded call price; exact amount unavailable');
 assert.equal(observedCallPrice({right:{bet:c(600)}},null).reason,'Call price unreadable');
 assert.equal(observedCallPrice({hero:{bet:c(0),total:1000},right:{bet:c(50),total:150}},null).value,50);
});

test('rounded larger wager cannot silently become a smaller exact call price',()=>{
 const s={hero:{bet:c(200)},upper_left:{bet:c(900)},upper_right:{bet:c(900)},right:{bet:{value:1600,approximate:true}}};
 assert.deepEqual(roundedCallObservation(s,null),{value:1400,source:'rounded current-round wager difference'});
 assert.equal(observedCallPrice(s,null,['left']).reason,'Rounded call price; exact amount unavailable');
 assert.deepEqual(roundedCallObservation(s,{value:1400,approximate:true}),{value:1400,source:'rounded call prompt'});
 assert.equal(observedCallPrice(s,c(1400),['left']).value,1400);
});

test('rounded wager scenarios remain explicitly estimates and do not authorize raise sizing',()=>{
 const s={hero:{bet:c(200),stack:c(23800)},upper_left:{bet:c(900)},upper_right:{bet:c(900)},right:{bet:{value:1600,approximate:true}}};
 const args={street:'Preflop',seats:s,prompt:{value:1400,approximate:true},excluded:['left'],equities:[.386]};
 const r=roundedPracticeScenario(args);
 assert.equal(r.call,1400);assert.equal(r.pot,3600);assert.equal(r.estimated,true);assert.equal(r.pricePartial,true);
 assert.equal(conditionalRaiseComparison({model:r,counts:[3],equities:[.386],stack:23800,raiseVisible:true}).action,null);
 assert.equal(roundedPracticeScenario({...args,prompt:c(500)}),null);
});
test('price headline is independent of equity availability',()=>{
 assert.equal(practicePriceHeadline({value:400,partial:false},null),'Your turn · Call cost 400');
 assert.equal(practicePriceHeadline({reason:'Rounded call price; exact amount unavailable'},{value:1400}),'Your turn · Call cost ≈1,400');
 assert.equal(practicePriceHeadline({value:0,partial:false},null),'Your turn · Check available');
 assert.equal(practicePriceHeadline(null,null),'Your turn · Price unavailable');
});

test('highest wager remains the price when preceding player folds',()=>{
 const s={hero:{bet:c(200),stack:c(1000)},left:{status_candidate:'Fold'},right:{bet:c(600)},upper_left:{bet:c(900)},upper_right:{bet:c(200)}};
 assert.equal(observedCallPrice(s,null,['left']).value,700);
 s.upper_left.bet={...c(900),retained:true};
 assert.deepEqual(observedCallPrice(s,null,['left']),{value:700,source:'retained round wager difference',partial:true});
});
test('stack-limited call display does not certify side-pot eligibility',()=>{
 assert.equal(practicePriceHeadline({value:700,partial:false},null,300),'Your turn · All-in call cost 300');
 assert.equal(practicePriceHeadline({value:700,partial:false},null,0),'All-in · no action required');
 assert.equal(practicePanelModel({street:'Preflop',seats:{hero:{stack:c(0)}},equities:[.5]}).reason,'All-in · no action required');
});
