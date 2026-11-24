import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
const routes={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/engine.js':'engine.js','/styles.css':'styles.css','/worker.js':'worker.js'};
const types={html:'text/html; charset=utf-8',js:'text/javascript; charset=utf-8',css:'text/css; charset=utf-8'};
const port=Number(process.env.PORT||8000);
createServer(async(req,res)=>{
  const path=new URL(req.url,'http://localhost').pathname, file=routes[path];
  if(!file||req.method!=='GET'){res.writeHead(404);res.end('Not found');return;}
  try{const data=await readFile(new URL(file,import.meta.url));res.writeHead(200,{'Content-Type':types[file.split('.').pop()],'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'});res.end(data);}
  catch{res.writeHead(500);res.end('Cannot read file');}
}).listen(port,'127.0.0.1',()=>console.log('Poker Engine: http://127.0.0.1:'+port));
