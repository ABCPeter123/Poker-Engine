import test from 'node:test';import assert from 'node:assert/strict';
import {rangeStudy,reviewedFrequency} from '../research/strategy-study.mjs';
test('offline range study produces explicit scenario results',()=>{
 const r=rangeStudy({hole:[12,25],opponents:3,pot:10300,call:10000,iterations:200,seed:42});
 assert.equal(r.scenarios.length,3);
 assert.equal(r.breakEven,10000/20300);
 for(const s of r.scenarios){assert.ok(s.equity>=0&&s.equity<=1);assert.equal(s.showdownCallEV,s.equity*20300-10000);}
 assert.deepEqual(r,rangeStudy({hole:[12,25],opponents:3,pot:10300,call:10000,iterations:200,seed:42}));
});
test('small samples do not produce extreme opponent frequency estimates',()=>{
 assert.equal(reviewedFrequency(0,0).smoothed,.5);
 assert.equal(reviewedFrequency(1,1).smoothed,.6);
 assert.equal(reviewedFrequency(9,10).raw,.9);
 assert.throws(()=>reviewedFrequency(2,1));
});
