import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {reviewFrame} from './review-bridge.mjs';
import {practiceFrame} from './practice-frame-bridge.mjs';
const routes={'/console.css':'console.css','/review-provenance.js':'review-provenance.js','/':'index.html','/screen-review.html':'screen-review.html','/screen-review.js':'screen-review.js','/live-practice.js':'live-practice.js','/manual-observations.js':'manual-observations.js','/practice-decision.js':'practice-decision.js','/live-practice-view.js':'live-practice-view.js','/capture-view.js':'capture-view.js','/review-validation.js':'review-validation.js','/review-equity.js':'review-equity.js','/overlay.css':'overlay.css','/analysis.html':'analysis.html','/table-engine.js':'table-engine.js','/table-app.js':'table-app.js','/table.css':'table.css','/quick-input.js':'quick-input.js','/index.html':'index.html','/app.js':'app.js','/engine.js':'engine.js','/styles.css':'styles.css','/worker.js':'worker.js'};
const types={html:'text/html; charset=utf-8',js:'text/javascript; charset=utf-8',css:'text/css; charset=utf-8'};
const port=Number(process.env.PORT||8000);
createServer(async(req,res)=>{
  const path=new URL(req.url,'http://localhost').pathname;
  if(path==='/api/practice-frame'){await practiceFrame(req,res,port);return;}
  if(path==='/api/review-frame'){await reviewFrame(req,res,port);return;}
  const file=routes[path];
  if(!file||req.method!=='GET'){res.writeHead(404);res.end('Not found');return;}
  try{const data=await readFile(new URL(file,import.meta.url));res.writeHead(200,{'Content-Type':types[file.split('.').pop()],'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'});res.end(data);}
  catch{res.writeHead(500);res.end('Cannot read file');}
}).listen(port,'127.0.0.1',()=>console.log('Poker Engine: http://127.0.0.1:'+port));
