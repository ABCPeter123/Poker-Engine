import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {fileURLToPath} from 'node:url';

let child=null,ready=null,pending=null,serial=0,owner=null,idleTimer=null,preparedSession=null,lastSequence=0;
const prefix='POKER_FRAME ',maxBytes=8*1024*1024;
function reply(res,code,value){if(res.destroyed||res.writableEnded)return;res.writeHead(code,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(JSON.stringify(value));}
function shutdown(reason='Recognition worker stopped'){
 clearTimeout(idleTimer);idleTimer=null;preparedSession=null;lastSequence=0;const old=child;child=null;
 if(ready){ready.reject(Error(reason));ready=null;}
 if(pending){clearTimeout(pending.timer);pending.reject(Error(reason));pending=null;}
 if(old){old.stdin.destroy();old.kill();}
}
process.once('exit',()=>{if(child)child.kill();});
function start(){
 if(child&&ready)return ready.promise;
 const python=process.env.POKER_PYTHON||(process.platform==='win32'?'py':'python3');
 const script=fileURLToPath(new URL('./pokerist/frame_worker.py',import.meta.url));
 const proc=spawn(python,['-u',script],{stdio:['pipe','pipe','pipe'],windowsHide:true});
 child=proc;let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});ready={promise,resolve,reject};
 let diagnostics='';proc.stderr.on('data',chunk=>{diagnostics=(diagnostics+chunk.toString()).slice(-1800);});
 proc.stdin.on('error',()=>{if(child===proc)shutdown('Recognition input closed');});
 const rl=createInterface({input:proc.stdout,crlfDelay:Infinity});
 rl.on('line',line=>{if(child!==proc||!line.startsWith(prefix))return;let msg;try{msg=JSON.parse(line.slice(prefix.length));}catch{return;}if(msg.ready){ready.resolve(msg);return;}if(pending&&msg.id===pending.id){const p=pending;pending=null;clearTimeout(p.timer);msg.error?p.reject(Error(msg.error)):p.resolve(msg);}});
 proc.once('error',e=>{if(child===proc)shutdown(e.message);});
 proc.once('exit',code=>{if(child===proc)shutdown('Recognition worker exited ('+code+'). '+diagnostics);});
 const timer=setTimeout(()=>{if(child===proc)shutdown('Python initialization timed out');},180000);promise.then(()=>clearTimeout(timer),()=>clearTimeout(timer));return promise;
}
async function recognize(data,session,ocr){
 clearTimeout(idleTimer);await start();
 if(!child||!ready)throw Error('Recognition worker unavailable');
 return await new Promise((resolve,reject)=>{
  const id=++serial,timer=setTimeout(()=>shutdown('Recognition frame timed out'),50000);
  pending={id,resolve,reject,timer};
  child.stdin.write(JSON.stringify({id,session,ocr,png:data.toString('base64')})+'\n');
 });
}
function authorized(req,port){
 const allowed=new Set(['http://127.0.0.1:'+port,'http://localhost:'+port]);
 return req.method==='POST'&&allowed.has(req.headers.origin)&&allowed.has('http://'+req.headers.host)&&req.headers['x-practice-consent']==='yes';
}
function sessionOf(req){
 const value=req.headers['x-frame-session'];return typeof value==='string'&&/^[a-zA-Z0-9-]{8,80}$/.test(value)?value:null;
}
function release(token){
 if(owner!==token)return;
 owner=null;clearTimeout(idleTimer);idleTimer=setTimeout(()=>shutdown(),30000);idleTimer.unref?.();
}
function claim(req,res,session){
 clearTimeout(idleTimer);idleTimer=null;
 const token={session};owner=token;
 const cancel=()=>{
  if(owner!==token||res.writableEnded)return;
  // A disconnected client must not strand the next session behind a worker
  // that is still processing its abandoned request.
  owner=null;shutdown('Recognition client disconnected');
 };
 req.once('aborted',cancel);res.once('close',cancel);
 return token;
}
export async function preparePractice(req,res,port){
 if(!authorized(req,port)){reply(res,403,{error:'Local authorized practice frames only.'});return;}
 const session=sessionOf(req);if(!session){reply(res,400,{error:'Invalid frame session'});return;}
 // An explicit start replaces an abandoned session, never a frame within it.
 if(owner){
  if(owner.session===session){reply(res,409,{error:'Session already preparing or processing'});return;}
  owner=null;shutdown('Replaced by new recognition session');
 }
 const token=claim(req,res,session);
 try{
  const info=await start();
  if(owner!==token)return;
  preparedSession=session;lastSequence=0;
  reply(res,200,{ready:true,ocr:info.ocr,ocr_error:info.ocr_error});
 }catch(e){if(owner===token)reply(res,503,{error:String(e.message||e).slice(-1800)});}
 finally{release(token);}
}
export async function practiceFrame(req,res,port){
 if(!authorized(req,port)||req.headers['content-type']!=='image/png'){reply(res,403,{error:'Local authorized practice frames only.'});return;}
 const session=sessionOf(req);if(!session){reply(res,400,{error:'Invalid frame session'});return;}
 const seqText=req.headers['x-frame-sequence'];const sequence=typeof seqText==='string'&&/^[1-9][0-9]*$/.test(seqText)?Number(seqText):null;
 if(!Number.isSafeInteger(sequence)){reply(res,400,{error:'Invalid frame sequence'});return;}
 if(session!==preparedSession){reply(res,409,{error:'Recognition session not prepared. Start recognition again.'});return;}
 if(owner){reply(res,409,{error:'Overlapping request in prepared session'});return;}
 if(sequence!==lastSequence+1){reply(res,409,{error:'Unexpected frame sequence'});return;}
 const length=Number(req.headers['content-length']);if(!Number.isSafeInteger(length)||length<24||length>maxBytes){reply(res,413,{error:'Frame exceeds 8 MB limit'});return;}
 const token=claim(req,res,session);
 try{
  let count=0;const parts=[];for await(const part of req){count+=part.length;if(count>length||count>maxBytes)throw Error('Frame exceeds limit');parts.push(part);}
  if(owner!==token)return;
  const png=Buffer.concat(parts);if(count!==length||!png.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))||png.toString('ascii',12,16)!=='IHDR')throw Error('Invalid PNG');
  const w=png.readUInt32BE(16),h=png.readUInt32BE(20);if(!w||!h||w>4096||h>4096||w*h>12000000)throw Error('Frame dimensions exceed limit');
  const result=await recognize(png,session,req.headers['x-frame-ocr']==='yes');
  if(owner!==token)return;
  lastSequence=sequence;reply(res,200,{...result,sequence});
 }catch(e){if(owner===token)reply(res,400,{error:String(e.message||e).slice(-1800)});}
 finally{release(token);}
}
