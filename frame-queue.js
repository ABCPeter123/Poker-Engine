// Ordered frame queue. Never replace a queued observation with a newer one.
// Backpressure is an explicit failure, not a successful 60 FPS claim.
export class FrameQueue{
 constructor(limit=120){if(!Number.isSafeInteger(limit)||limit<1)throw Error('Invalid queue capacity');this.limit=limit;this.items=[];this.captured=0;this.processed=0;this.sourceMissed=0;this.lastPresented=null;this.peak=0;this.failed=null;this.firstAt=null;this.lastAt=null;}
 enqueue(meta,encode){
  if(this.failed)throw Error(this.failed);
  const n=meta.presentedFrames,at=meta.capturedAt;
  if(!Number.isSafeInteger(n)||n<0||!Number.isFinite(at)||at<0)throw Error('Invalid frame metadata');
  if(this.lastPresented!==null&&n<=this.lastPresented){this.failed='Duplicate or out-of-order source frame';throw Error(this.failed);}
  if(this.lastPresented!==null&&n!==this.lastPresented+1){this.sourceMissed+=n-this.lastPresented-1;this.failed='Source frame gap: '+this.sourceMissed+' frame(s) missed';throw Error(this.failed);}
  if(this.items.length>=this.limit){this.failed='Recognition cannot keep up: queue capacity '+this.limit+' reached';throw Error(this.failed);}
  this.lastPresented=n;this.firstAt??=at;this.lastAt=at;
  const item={id:++this.captured,capturedAt:at,presentedFrames:n,encoded:null};
  // Reserve the sequence position before async PNG encoding completes.
  try{item.encoded=Promise.resolve(encode()).then(blob=>({blob}),error=>({error}));}catch(error){item.encoded=Promise.resolve({error});}
  this.items.push(item);this.peak=Math.max(this.peak,this.items.length);
  return item;
 }
 front(){return this.items[0]||null;}
 complete(id){if(!this.front()||this.front().id!==id){this.failed='Frame response order mismatch';throw Error(this.failed);}this.items.shift();this.processed++;}
 report(now){const sourceFps=this.captured>1&&this.lastAt>this.firstAt?(this.captured-1)*1000/(this.lastAt-this.firstAt):null;const processingFps=this.firstAt!==null&&now>this.firstAt?this.processed*1000/(now-this.firstAt):0;return {captured:this.captured,processed:this.processed,queued:this.items.length,peak:this.peak,sourceMissed:this.sourceMissed,sourceFps,processingFps,failed:this.failed,oldestAgeMs:this.front()?now-this.front().capturedAt:0};}
}
