import test from 'node:test';
import assert from 'node:assert/strict';
import {assertFrameProvenance,frameProvenance,savedFrameTime} from '../review-provenance.js';
const p={sha256:'a'.repeat(64),bytes:100,width:1536,height:709,format:'image/png'};
test('recognition response must identify exact frozen frame',()=>{
 assert.deepEqual(assertFrameProvenance(p,p),p);
 for(const change of [{sha256:'b'.repeat(64)},{width:1000},{height:700},{bytes:101}])assert.throws(()=>assertFrameProvenance({...p,...change},p));
 assert.throws(()=>assertFrameProvenance(undefined,p));
});
test('invalid provenance cannot be exported as an identified image',()=>{
 for(const change of [{sha256:'bad'},{bytes:1},{width:0},{height:NaN},{format:'image/jpeg'}])assert.throws(()=>frameProvenance({...p,...change}));
});
test('saved video timestamp is captured independently from response timing',()=>{
 assert.equal(savedFrameTime('recording',0),0);
 assert.equal(savedFrameTime('recording',12.345),12.345);
 assert.equal(savedFrameTime('image',12),null);
 assert.equal(savedFrameTime('recording',NaN),null);
});
