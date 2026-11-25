import test from 'node:test';import assert from 'node:assert/strict';import {CurrentStateQueue} from '../frame-queue.js';
const m=(n,t)=>({presentedFrames:n,capturedAt:t});
test('fresh state sampling has at most one in-flight snapshot and no historical backlog',()=>{
 const q=new CurrentStateQueue(100);let encoded=0;const encode=()=>{encoded++;return null;};
 assert.equal(q.enqueue(m(1,0),encode).id,1);
 for(let n=2;n<=60;n++)assert.equal(q.enqueue(m(n,n*16.67),encode),null);
 assert.equal(encoded,1);q.complete(1);
 const item=q.enqueue(m(61,1017),encode);
 assert.equal(item.capturedAt,1017);assert.equal(item.id,2);assert.equal(encoded,2);
 assert.equal(q.report(1020).intentionalSkips,59);
 assert.equal(q.report(1020).lastSnapshotAgeMs,1020);
 q.complete(2);assert.equal(q.report(1020).lastSnapshotAgeMs,3);
});
test('sampling interval and source gaps are separate',()=>{
 const q=new CurrentStateQueue(100);
 q.enqueue(m(1,0),()=>null);q.complete(1);
 assert.equal(q.enqueue(m(3,33),()=>null),null);
 assert.equal(q.report(33).sourceMissed,1);assert.equal(q.report(33).intentionalSkips,1);
 assert.equal(q.enqueue(m(4,100),()=>null).id,2);
 assert.throws(()=>q.complete(3),/mismatch/);
});
