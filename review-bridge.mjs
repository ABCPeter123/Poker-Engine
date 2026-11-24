import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
const run=promisify(execFile), maxBytes=8*1024*1024;
let busy=false;
function reply(res,code,body){res.writeHead(code,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(JSON.stringify(body));}
export async function reviewFrame(req,res,port){
 const allowed=new Set(['http://127.0.0.1:'+port,'http://localhost:'+port]);
 if(req.method!=='POST'||!allowed.has(req.headers.origin)||!allowed.has('http://'+req.headers.host)||req.headers['content-type']!=='image/png'){reply(res,403,{error:'Local saved-frame review only.'});return;}
 if(busy){reply(res,429,{error:'Another review is running.'});return;}
 const length=Number(req.headers['content-length']);
 if(!Number.isSafeInteger(length)||length<24||length>maxBytes){reply(res,413,{error:'Image must be between 24 bytes and 8 MB.'});return;}
 busy=true;let dir;
 try{
  let count=0;const parts=[];
  for await(const part of req){count+=part.length;if(count>maxBytes||count>length)throw Error('Image exceeds limit');parts.push(part);}
  const data=Buffer.concat(parts);
  if(count!==length||!data.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]))||data.toString('ascii',12,16)!=='IHDR')throw Error('Invalid PNG.');
  const w=data.readUInt32BE(16),h=data.readUInt32BE(20);
  if(!w||!h||w>4096||h>4096||w*h>12000000)throw Error('Image dimensions exceed limit.');
  dir=await mkdtemp(join(tmpdir(),'poker-review-'));
  const input=join(dir,'frame.png'),output=join(dir,'result.json');
  await writeFile(input,data);
  const script=fileURLToPath(new URL('./pokerist/review.py',import.meta.url));
  const python=process.env.POKER_PYTHON||(process.platform==='win32'?'py':'python3');
  await run(python,[script,input,'--output',output],{timeout:180000,maxBuffer:512*1024,windowsHide:true});
  const result=JSON.parse(await readFile(output,'utf8'));reply(res,200,result);
 }catch(e){reply(res,400,{error:'Review failed: '+String(e.stderr||e.message||e).slice(-900)});}
 finally{if(dir)await rm(dir,{recursive:true,force:true}).catch(()=>{});busy=false;}
}
