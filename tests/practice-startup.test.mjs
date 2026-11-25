import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer,request} from 'node:http';
import {preparePractice,practiceFrame,closePracticeWorker} from '../practice-frame-bridge.mjs';

test('prepare before capture, abandoned upload cannot strand replacement session', {timeout:60000}, async t=>{
 process.env.POKER_PYTHON=process.platform==='win32'?'python':'python3';
 const server=createServer((req,res)=>req.url==='/ready'?preparePractice(req,res,server.address().port):practiceFrame(req,res,server.address().port));
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
 t.after(()=>{closePracticeWorker();server.closeAllConnections?.();return new Promise(r=>server.close(r));});
 const port=server.address().port,origin='http://127.0.0.1:'+port;
 const headers=session=>({Origin:origin,'X-Practice-Consent':'yes','X-Frame-Session':session});
 const a='session-test-a',b='session-test-b';
 const ready=async session=>fetch(origin+'/ready',{method:'POST',headers:headers(session)});
 const submit=async(session,sequence)=>fetch(origin+'/frame',{method:'POST',headers:{...headers(session),'Content-Type':'image/png','X-Frame-Sequence':String(sequence)},body:Buffer.alloc(24)});
 assert.equal((await submit(a,1)).status,409);
 const response=await ready(a);assert.equal(response.status,200);assert.equal((await response.json()).ready,true);
 assert.equal((await submit(a,2)).status,409);
 // Start sending an incomplete body. No recognition result can be generated.
 const upload=request(origin+'/frame',{method:'POST',headers:{...headers(a),'Content-Type':'image/png','Content-Length':100,'X-Frame-Sequence':'1'}});
 upload.on('error',()=>{});
 await new Promise((resolve,reject)=>upload.write(Buffer.alloc(10),e=>e?reject(e):resolve()));
 upload.destroy();
 const next=await ready(b);assert.equal(next.status,200);assert.equal((await next.json()).ready,true);
 assert.equal((await submit(a,1)).status,409);
 const invalid=await submit(b,1);assert.equal(invalid.status,400);assert.match((await invalid.json()).error,/Invalid PNG/);
 assert.equal((await submit(b,1)).status,400);
});
