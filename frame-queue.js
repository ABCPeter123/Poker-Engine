// Preserve every admitted frame in order. Missing source callbacks and
// overload are explicit coverage losses, not reasons to stop future capture.
export class FrameQueue{
 constructor(limit=120){
  if(!Number.isSafeInteger(limit)||limit<1)throw Error('Invalid queue capacity');
  this.limit=limit;this.items=[];this.captured=0;this.processed=0;this.sourceMissed=0;this.queueMissed=0;this.observed=0;this.lastPresented=null;this.lastAccepted=null;this.peak=0;this.failed=null;this.firstAt=null;this.lastAt=null;this.recovering=false;
 }
 enqueue(meta,encode){
  if(this.failed)throw Error(this.failed);
  const n=meta.presentedFrames,at=meta.capturedAt;
  if(!Number.isSafeInteger(n)||n<0||!Number.isFinite(at)||at<0)throw Error('Invalid frame metadata');
  if(this.lastPresented!==null&&(n<=this.lastPresented||at<this.lastAt)){this.failed='Duplicate or out-of-order source frame';throw Error(this.failed);}
  if(this.lastPresented!==null)this.sourceMissed+=n-this.lastPresented-1;
  this.lastPresented=n;this.firstAt??=at;this.lastAt=at;this.observed++;
  // Drain admitted work before accepting more when saturated. Do not
  // silently replace existing frames or accumulate an unbounded backlog.
  if(this.items.length>=this.limit)this.recovering=true;
  if(this.recovering&&this.items.length<=Math.floor(this.limit/10))this.recovering=false;
  if(this.recovering){this.queueMissed++;return null;}
  const gapBefore=this.lastAccepted===null?0:n-this.lastAccepted-1;
  this.lastAccepted=n;
  const item={id:++this.captured,capturedAt:at,presentedFrames:n,gapBefore,encoded:null};
  try{item.encoded=Promise.resolve(encode()).then(blob=>({blob}),error=>({error}));}catch(error){item.encoded=Promise.resolve({error});}
  this.items.push(item);this.peak=Math.max(this.peak,this.items.length);
  return item;
 }
 front(){return this.items[0]||null;}
 complete(id){if(!this.front()||this.front().id!==id){this.failed='Frame response order mismatch';throw Error(this.failed);}this.items.shift();this.processed++;}
 report(now){
  const sourceFps=this.observed>1&&this.lastAt>this.firstAt?(this.observed-1+this.sourceMissed)*1000/(this.lastAt-this.firstAt):null;
  const callbackFps=this.observed>1&&this.lastAt>this.firstAt?(this.observed-1)*1000/(this.lastAt-this.firstAt):null;
  const processingFps=this.firstAt!==null&&now>this.firstAt?this.processed*1000/(now-this.firstAt):0;
  return {captured:this.captured,processed:this.processed,queued:this.items.length,peak:this.peak,sourceMissed:this.sourceMissed,queueMissed:this.queueMissed,observed:this.observed,sourceFps,callbackFps,processingFps,failed:this.failed,recovering:this.recovering,coverageIntact:!this.failed&&!this.sourceMissed&&!this.queueMissed,oldestAgeMs:this.front()?now-this.front().capturedAt:0};
 }
}

// Current-state mode: count source callbacks, admit the next fresh snapshot
// only when the worker is free. No historical backlog and no claim of full
// frame reconstruction. Deliberate sampling is distinct from source losses.
export class CurrentStateQueue{
 constructor(minIntervalMs=100){
  if(!Number.isFinite(minIntervalMs)||minIntervalMs<0)throw Error('Invalid snapshot interval');
  this.minIntervalMs=minIntervalMs;this.captured=0;this.processed=0;this.observed=0;this.sourceMissed=0;this.intentionalSkips=0;this.failed=null;this.lastPresented=null;this.lastAt=null;this.firstAt=null;this.lastAcceptedAt=null;this.lastCompletedAt=null;this.item=null;
 }
 enqueue(meta,encode){
  if(this.failed)throw Error(this.failed);
  const n=meta.presentedFrames,at=meta.capturedAt;
  if(!Number.isSafeInteger(n)||n<0||!Number.isFinite(at)||at<0)throw Error('Invalid frame metadata');
  if(this.lastPresented!==null&&(n<=this.lastPresented||at<this.lastAt)){this.failed='Duplicate or out-of-order source frame';throw Error(this.failed);}
  if(this.lastPresented!==null)this.sourceMissed+=n-this.lastPresented-1;
  this.lastPresented=n;this.lastAt=at;this.firstAt??=at;this.observed++;
  if(this.item||(this.lastAcceptedAt!==null&&at-this.lastAcceptedAt<this.minIntervalMs)){this.intentionalSkips++;return null;}
  this.lastAcceptedAt=at;
  const item={id:++this.captured,capturedAt:at,presentedFrames:n,encoded:null};
  try{item.encoded=Promise.resolve(encode()).then(blob=>({blob}),error=>({error}));}catch(error){item.encoded=Promise.resolve({error});}
  this.item=item;return item;
 }
 front(){return this.item;}
 complete(id){if(!this.item||this.item.id!==id){this.failed='Frame response order mismatch';throw Error(this.failed);}this.lastCompletedAt=this.item.capturedAt;this.item=null;this.processed++;}
 report(now){
  const span=this.lastAt-this.firstAt;
  const callbackFps=this.observed>1&&span>0?(this.observed-1)*1000/span:null;
  return {captured:this.captured,processed:this.processed,sourceMissed:this.sourceMissed,intentionalSkips:this.intentionalSkips,queued:Number(!!this.item),callbackFps,sourceFps:callbackFps===null?null:(this.observed-1+this.sourceMissed)*1000/span,processingFps:this.firstAt!==null&&now>this.firstAt?this.processed*1000/(now-this.firstAt):0,oldestAgeMs:this.item?now-this.item.capturedAt:0,lastSnapshotAgeMs:this.lastCompletedAt===null?null:now-this.lastCompletedAt,failed:this.failed};
 }
}
