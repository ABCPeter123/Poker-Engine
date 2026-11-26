import test from 'node:test';import assert from 'node:assert/strict';
import {scenarioProgress} from '../live-practice.js';
test('same-deck results remain usable when opponent scenarios change',()=>{
 const cache=new Map([[2,.42],[3,.31]]);
 assert.deepEqual(scenarioProgress('deck',[2,3],cache),{state:'ready',equities:[.42,.31]});
 assert.deepEqual(scenarioProgress('deck',[3],cache),{state:'ready',equities:[.31]});
 assert.equal(scenarioProgress('deck',[3,4],cache).state,'pending');
 cache.set(4,.25);
 assert.deepEqual(scenarioProgress('deck',[3,4],cache),{state:'ready',equities:[.31,.25]});
});
test('failed scenarios are distinct from pending and never considered complete',()=>{
 assert.equal(scenarioProgress('deck',[2],new Map([[2,null]])).state,'failed');
 assert.equal(scenarioProgress('deck',[2],new Map()).state,'pending');
 assert.equal(scenarioProgress('deck',[],new Map()).state,'no opponents');
});
