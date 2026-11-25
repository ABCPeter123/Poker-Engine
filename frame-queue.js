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
