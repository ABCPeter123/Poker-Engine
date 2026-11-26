import test from 'node:test';import assert from 'node:assert/strict';
import {simplePracticeAction,simplePriceDetail} from '../practice-decision.js';
test('practice actions are short and retain sizes and uncertainty',()=>{
 for(const [input,output] of [['Check','CHECK'],['Fold','FOLD'],['Call 2,000','CALL 2,000'],['Call ≈2,000','CALL ≈2,000'],['Call at least 400','CALL AT LEAST 400'],['Raise to 600 (conditional)','RAISE TO 600']])assert.equal(simplePracticeAction(input),output);
});
test('observation messages never turn into action headlines',()=>{
 for(const input of ['Your turn · Call cost ≈2,000','Call cost 2,000','Raise (size unavailable)','Check available',null])assert.equal(simplePracticeAction(input),'NO SUGGESTION');
 assert.equal(simplePriceDetail(null,{value:2000}),'Call cost ≈2,000');
 assert.equal(simplePriceDetail(null,null),'Call price unknown');
});
