// Saved-frame provenance: bind exported observations to the exact PNG sent
// for review and to the frozen source timestamp, not response arrival time.
export function frameProvenance({sha256,bytes,width,height,format}={}){
 if(typeof sha256!=='string'||!/^[a-f0-9]{64}$/.test(sha256)||!Number.isSafeInteger(bytes)||bytes<24||!Number.isSafeInteger(width)||width<1||!Number.isSafeInteger(height)||height<1||format!=='image/png')throw Error('Invalid review image provenance.');
 return {sha256,bytes,width,height,format};
}
export function assertFrameProvenance(actual,expected){
 const a=frameProvenance(actual),e=frameProvenance(expected);
 for(const key of Object.keys(e))if(a[key]!==e[key])throw Error('Recognition result does not match the frozen frame.');
 return a;
}
export async function digestFrame(blob,width,height){
 const hash=await crypto.subtle.digest('SHA-256',await blob.arrayBuffer());
 return frameProvenance({sha256:Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join(''),bytes:blob.size,width,height,format:blob.type});
}
export function savedFrameTime(source,currentTime){
 return source==='recording'&&Number.isFinite(currentTime)&&currentTime>=0?currentTime:null;
}
