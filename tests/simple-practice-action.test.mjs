import test from 'node:test';import assert from 'node:assert/strict';
import {simplePracticeAction,simplePriceDetail,practiceCheckFallback} from '../practice-decision.js';
test('practice actions are short and retain sizes and uncertainty',()=>{
 for(const [input,output] of [['Check','CHECK'],['Fold','FOLD'],['Call 2,000','CALL 2,000'],['Call ≈2,000','CALL ≈2,000'],['Call at least 400','CALL AT LEAST 400'],['Raise to 600 (conditional)','RAISE TO 600']])assert.equal(simplePracticeAction(input),output);
});
test('observation messages never turn into action headlines',()=>{
 for(const input of ['Your turn · Call cost ≈2,000','Call cost 2,000','Raise (size unavailable)','Check available',null])assert.equal(simplePracticeAction(input),'NO SUGGESTION');
 assert.equal(simplePriceDetail(null,{value:2000}),'Call cost ≈2,000');
 assert.equal(simplePriceDetail(null,null),'Call price unknown');
});

test('explicit free check has a baseline independent of equity or pot',()=>{
 const a={fresh:true,turn:'hero',heroVisible:true,prompt:{value:0,approximate:false,source:'explicit check prompt'},price:null,stack:null};
 assert.deepEqual(practiceCheckFallback(a),{action:'CHECK',detail:'Free check · practice baseline'});
 for(const b of [{fresh:false},{turn:'right'},{heroVisible:false},{stack:0},{allIn:true},{prompt:{value:200,source:'explicit check prompt'}},{prompt:{value:0}},{prompt:{value:0,approximate:true,source:'explicit check prompt'}},{price:{reason:'Call price and wagers disagree'}},{price:{value:200}}])assert.equal(practiceCheckFallback({...a,...b}),null);
});
