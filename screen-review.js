const $=id=>document.getElementById(id),video=$('video'),frame=$('frame'),ink=$('ink'),ctx=ink.getContext('2d');
let stream=null,url=null,source='none',frozen=false,drawing=false,point=null,revision=0,reviewPending=false,frameVersion=0;
function resetReview(){frameVersion++;$('review-overlay').hidden=true;$('review-result').hidden=true;}
function status(msg){$('status').textContent=msg;}
function controls(){$('recognize').disabled=!frozen||!['image','recording'].includes(source)||reviewPending;$('stop').disabled=source==='none';$('freeze').disabled=frozen||source==='none'||!video.videoWidth;$('resume').disabled=!frozen||source==='image';$('clear').disabled=!frozen;video.hidden=source==='none'||frozen;frame.hidden=!frozen;ink.hidden=!frozen;$('empty').hidden=source!=='none';}
function stop(){revision++;resetReview();if(stream)stream.getTracks().forEach(t=>t.stop());stream=null;video.pause();video.srcObject=null;video.removeAttribute('src');video.load();if(url)URL.revokeObjectURL(url);url=null;source='none';frozen=false;drawing=false;point=null;controls();}
function size(w,h){resetReview();frame.width=ink.width=w;frame.height=ink.height=h;$('screen').style.aspectRatio=w+'/'+h;ctx.clearRect(0,0,w,h);}
$('share').onclick=async()=>{stop();const id=revision;try{if(!navigator.mediaDevices?.getDisplayMedia)throw Error('Screen capture is unavailable. Use Chrome or Edge on localhost.');const candidate=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:{ideal:15,max:30}},audio:false});if(id!==revision){candidate.getTracks().forEach(t=>t.stop());return;}stream=candidate;source='share';video.srcObject=stream;const track=stream.getVideoTracks()[0];track.addEventListener('ended',()=>{if(stream===candidate){stop();status('Screen sharing ended.');}});await video.play();status('Local screen preview. Freeze to annotate.');controls();}catch(e){if(id===revision){stop();status(e.message);}}};
$('stop').onclick=()=>{stop();status('Preview stopped.');};
video.onloadedmetadata=()=>{if(source==='none')return;if(video.videoWidth)size(video.videoWidth,video.videoHeight);controls();};
$('file').onchange=async()=>{const file=$('file').files[0];if(!file)return;stop();const id=revision;url=URL.createObjectURL(file);try{if(file.type.startsWith('image/')){const image=new Image();image.src=url;await image.decode();if(id!==revision)return;source='image';size(image.naturalWidth,image.naturalHeight);frame.getContext('2d').drawImage(image,0,0);frozen=true;status('Saved image ready for annotation.');}else{source='recording';video.src=url;await video.play();if(id!==revision)return;status('Saved recording playing locally.');}controls();}catch(e){if(id===revision){stop();status(e.message);}}finally{$('file').value='';}};
$('freeze').onclick=()=>{if(!video.videoWidth||source==='none')return;size(video.videoWidth,video.videoHeight);frame.getContext('2d').drawImage(video,0,0);if(source==='recording')video.pause();frozen=true;status('Frozen frame. Draw using the mouse or touch.');controls();};
$('resume').onclick=()=>{if(source==='image')return;resetReview();frozen=false;drawing=false;point=null;video.play().catch(e=>status(e.message));status('Preview resumed.');controls();};
$('clear').onclick=()=>ctx.clearRect(0,0,ink.width,ink.height);
function xy(e){const b=ink.getBoundingClientRect();return [(e.clientX-b.left)*ink.width/b.width,(e.clientY-b.top)*ink.height/b.height];}
ink.onpointerdown=e=>{if(!frozen)return;ink.setPointerCapture(e.pointerId);drawing=true;point=xy(e);};
ink.onpointermove=e=>{if(!drawing||!point)return;const p=xy(e);ctx.strokeStyle='#ffd24a';ctx.lineWidth=Math.max(3,ink.width/300);ctx.lineCap='round';ctx.lineJoin='round';ctx.beginPath();ctx.moveTo(...point);ctx.lineTo(...p);ctx.stroke();point=p;};
ink.onpointerup=ink.onpointercancel=ink.onlostpointercapture=()=>{drawing=false;point=null;};
window.addEventListener('pagehide',stop);controls();
$('recognize').onclick=async()=>{
 if(!frozen||!['image','recording'].includes(source)||reviewPending)return;
 const version=frameVersion;reviewPending=true;controls();status('Running local screenshot recognition. First launch may install dependencies.');
 try{
  const blob=await new Promise(resolve=>frame.toBlob(resolve,'image/png'));
  if(!blob)throw Error('Could not encode saved frame.');
  if(version!==frameVersion)return;
  const response=await fetch('/api/review-frame',{method:'POST',headers:{'Content-Type':'image/png'},body:blob});
  const result=await response.json();if(version!==frameVersion)return;
  if(!response.ok)throw Error(result.error||'Review failed.');
  const text=slots=>slots.map(c=>c?.candidate??(c?'?':'–')).join(' ');
  const overlay=$('review-overlay');overlay.replaceChildren();
  for(const value of ['UNVERIFIED REVIEW', 'Hand: '+text(result.hole_slots), 'Board: '+text(result.board_slots),'Street: '+(result.street_candidate||'?'),'Pot: '+(result.number_candidates?.pot?.candidate?.display||'?')]){
   const line=document.createElement('div');line.textContent=value;overlay.append(line);
  }
  overlay.hidden=false;$('review-result').textContent=JSON.stringify(result,null,2);$('review-result').hidden=false;
  status('Candidate recognition complete. Confirm all readings manually.');
 }catch(e){if(version===frameVersion)status(e.message);}
 finally{reviewPending=false;controls();}
};
