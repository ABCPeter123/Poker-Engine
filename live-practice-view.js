import {CurrentStateQueue} from './frame-queue.js';
import {retainedRoundBet,observedHandCommitment,directNumericSnapshot,snapshotCoverage,reconcileSnapshots,freshBetValue,currentNumericSample,candidateCards,stableReading,practiceInput,updateCardMemory,observationAge,createBetMemory,updateBetMemory,trackedBetLabel,interruptBetMemory} from './live-practice.js';
import {SEAT_ANCHORS,overlayPosition,decisionInputs,decisionFromEquity,inputValue} from './practice-decision.js';
import {SEATS,FIELDS,CARD_KEYS,isLocked,setManual,releaseManual,resolveManual,loadManual,saveManual,displayValue,effectiveCards} from './manual-observations.js';

export function attachPractice({video,screen,canRun,rotation}){
 const $=id=>document.getElementById(id),panel=$('live-panel'),canvas=document.createElement('canvas');
 let locks=loadManual({getItem:key=>localStorage.getItem(key)}),lastOcrAt=null,lastTable=null,cardMemory=null,betMemory=createBetMemory();
 let active=false,session='',epoch=0,timer=null,controller=null,equityWorker=null,reading=null,requestedKey='',lastFrame=null,resetAt=-1,lastResult=null;
 const editors=new Map(),inlineEditors=new Map(),popupEditors=new Map(),seatNodes=new Map();
 let equityResult=null,decisionTimer=null,ocrBackend='unknown',lastTimings=null,lastOcrState=null,previousSnapshot=null,conservation=null,frameQueue=null,frameCallback=null,draining=false,lastPaintAt=-Infinity;
 const status=msg=>$('live-status').textContent=msg, metric=msg=>{$('live-equity').textContent=msg;$('simulation-observation-status').textContent='Practice simulation: '+msg;};
 function clearEquity(){equityResult=null;if(equityWorker){equityWorker.terminate();equityWorker=null;}requestedKey='';metric('—');}
 function clearAuto(){lastOcrState=null;lastTimings=null;previousSnapshot=null;conservation=null;lastResult=null;lastOcrAt=null;lastTable=null;cardMemory=null;reading=null;lastFrame=null;clearEquity();}
 function save(){const ok=saveManual({setItem:(key,value)=>localStorage.setItem(key,value)},locks);$('manual-lock-count').textContent=Object.keys(locks).length+' locked'+(ok?' · saved locally':' · browser storage unavailable');}
 function stop(){closePopup();clearInterval(decisionTimer);decisionTimer=null;betMemory=createBetMemory();clearAuto();active=false;epoch++;clearTimeout(timer);timer=null;if(frameCallback!==null)video.cancelVideoFrameCallback?.(frameCallback);frameCallback=null;frameQueue=null;draining=false;controller?.abort();controller=null;$('live-overlay').hidden=true;$('live-start').disabled=!canRun()||!$('practice-consent').checked;$('live-stop').disabled=true;status('Recognition stopped. Manual locks retained.');paint();}
 function refresh(){panel.hidden=false;if(!canRun()&&active)stop();$('live-start').disabled=active||!canRun()||!$('practice-consent').checked;$('screen-seat-layer').hidden=!canRun();$('screen-decision').hidden=!canRun();if(!canRun())closePopup();paintDecision();}
 function snapshot(){const w=video.videoWidth,h=video.videoHeight,deg=rotation(),swap=Math.abs(deg%180)===90;if(!w||!h)throw Error('Waiting for video dimensions');const scale=Math.min(1,1920/Math.max(w,h)),cw=Math.round((swap?h:w)*scale),ch=Math.round((swap?w:h)*scale);if(canvas.width!==cw||canvas.height!==ch){canvas.width=cw;canvas.height=ch;}const c=canvas.getContext('2d',{alpha:false});c.setTransform(1,0,0,1,0,0);c.translate(cw/2,ch/2);c.rotate(deg*Math.PI/180);c.drawImage(video,-w*scale/2,-h*scale/2,w*scale,h*scale);return new Promise(resolve=>canvas.toBlob(resolve,'image/png'));}
 function evaluate(candidate){const opponents=Number($('live-opponents').value);if(!active||!canRun()||!$('practice-consent').checked||!candidate||!Number.isInteger(opponents)||opponents<1||opponents>4){clearEquity();metric(candidate?'Select 1–4 opponents for simulation':'Waiting for recognized cards');return;}const key=candidate.key+'|'+opponents;if(key===requestedKey)return;clearEquity();requestedKey=key;const current=epoch,worker=new Worker('./worker.js',{type:'module'});equityWorker=worker;metric('Calculating…');worker.onmessage=({data})=>{if(epoch===current&&equityWorker===worker&&requestedKey===key){metric(data.error?'Unavailable':(data.result.equity*100).toFixed(1)+'%');equityResult=data.error?null:data.result.equity;equityWorker=null;if(data.error)requestedKey='';paintDecision();}worker.terminate();};worker.onerror=()=>{if(equityWorker===worker){metric('Unavailable');equityWorker=null;requestedKey='';paintDecision();}worker.terminate();};worker.postMessage({id:current,input:practiceInput(candidate,opponents)});}

 function changed(key){
  save();
  if(CARD_KEYS.includes(key)||key==='street'){reading=null;clearEquity();refreshCandidate(false);}
  paint();
 }
 function editor(f,parent,map=editors,compact=false){
  const box=document.createElement('div');box.className=compact?'screen-amount':'manual-field';
  const label=document.createElement('label');label.textContent=compact?(f.label==='Stack'?'S':'B'):f.label;
  const input=document.createElement(f.type==='choice'?'select':'input');input.setAttribute('aria-label',f.label+' '+f.key);
  if(f.type==='choice'){for(const value of ['',...f.choices]){const option=document.createElement('option');option.value=value;option.textContent=value===''?'Unknown / choose':displayValue(f.key,value);input.append(option);}}
  else{input.type='text';input.autocomplete='off';input.spellcheck=false;input.inputMode=f.type==='amount'?'numeric':'text';input.placeholder='?';}
  const buttons=document.createElement('div');buttons.className='manual-buttons';
  const lock=document.createElement('button'),auto=document.createElement('button');lock.type=auto.type='button';lock.textContent='Lock';auto.textContent=compact?'A':'Auto';auto.title='Return '+f.label+' to automatic recognition';auto.setAttribute('aria-label','Automatic '+f.key);
  const note=document.createElement('small');note.className='hint';
  const e={box,input,lock,auto,note,field:f,dirty:false,compact};
  function commit(force=false){if(!e.dirty&&!force)return;try{locks=setManual(locks,f.key,input.value);e.dirty=false;input.setCustomValidity('');changed(f.key);}catch(err){input.setCustomValidity(err.message);input.reportValidity();}}
  lock.onclick=()=>commit(true);
  auto.onclick=()=>{locks=releaseManual(locks,f.key);e.dirty=false;input.setCustomValidity('');changed(f.key);};
  input.oninput=()=>{e.dirty=true;input.setCustomValidity('');};
  input.onchange=()=>commit();
  input.onfocus=()=>{if(input.tagName==='INPUT')input.select();};
  input.onkeydown=ev=>{if(ev.key==='Enter'){ev.preventDefault();commit();if(!e.dirty)input.blur();}else if(ev.key==='Escape'){e.dirty=false;input.setCustomValidity('');input.blur();paint();}};
  label.append(input);
  if(compact){box.append(label,auto);note.hidden=true;}
  else{buttons.append(lock,auto);box.append(label,buttons,note);}
  parent.append(box);map.set(f.key,e);
 }
 for(const f of FIELDS.filter(f=>!f.key.includes('.')||CARD_KEYS.includes(f.key)))editor(f,$('manual-global'));
 for(const [id,name] of Object.entries(SEATS)){
  const group=document.createElement('div');group.className='manual-seat';const title=document.createElement('h4');title.textContent=name;const grid=document.createElement('div');grid.className='manual-grid';group.append(title,grid);
  for(const f of FIELDS.filter(f=>f.key.startsWith(id+'.')))editor(f,grid);$('manual-seats').append(group);
  const tile=document.createElement('div');tile.className='screen-seat';
  const header=document.createElement('button');header.type='button';header.className='screen-seat-title';header.setAttribute('aria-label','Edit '+name);header.textContent=name;header.onclick=()=>openPopup(id);
  const note=document.createElement('small');note.className='screen-seat-note';tile.append(header);
  for(const f of FIELDS.filter(f=>f.key===id+'.stack'||f.key===id+'.bet'))editor(f,tile,inlineEditors,true);
  tile.append(note);$('screen-seat-layer').append(tile);seatNodes.set(id,{tile,header,note});
 }
 function closePopup(){popupEditors.clear();$('screen-edit-fields').replaceChildren();$('screen-edit').hidden=true;}
 function openPopup(id){
  closePopup();$('screen-edit-title').textContent=id==='table'?'Cards and table':SEATS[id];
  for(const f of FIELDS.filter(f=>id==='table'?CARD_KEYS.includes(f.key)||!f.key.includes('.'):f.key.startsWith(id+'.')))editor(f,$('screen-edit-fields'),popupEditors);
  $('screen-edit').hidden=false;paint();
 }
 $('screen-edit-close').onclick=closePopup;
 $('screen-edit-table').onclick=()=>openPopup('table');
 $('screen-new-hand').onclick=()=>$('manual-new-hand').click();
 $('practice-action-confirm').onchange=()=>paintDecision();
 function refreshCandidate(sample){
  if(!active)return;
  const now=performance.now(),complete=CARD_KEYS.every(key=>isLocked(locks,key));
  const fresh=observationAge(lastFrame,now,1000).fresh;
  const candidate=complete||fresh?candidateCards(effectiveCards(lastResult,locks)):null;
  if(complete&&candidate)reading={key:candidate.key,count:2,stable:candidate,last:now};
  else if(sample)reading=stableReading(reading,candidate,lastFrame??now);
  else if(!candidate||reading?.key!==candidate.key)reading=null;
  if(!reading?.stable){clearEquity();metric('Waiting for confirmed cards');}else evaluate(reading.stable);
  $('live-confidence').textContent=complete?'Manually locked deck':reading?.stable?'Repeated effective reading':cardMemory?.carried.length?'Cached cards are display only':'Waiting for confirmed cards';
 }
 function paintDecision(){
  const show=(message,description='')=>{for(const id of ['live-action','decision-status-text']){const el=$(id);if(el.textContent!==message)el.textContent=message;}for(const id of ['live-action-detail','decision-status-detail']){const el=$(id);if(el.textContent!==description)el.textContent=description;}};
  if(!canRun()){show('Waiting for authorized practice window','Select a supported shared window.');return;}
  if(!$('practice-consent').checked){show('Practice permission required','Only enable recognition where real-time analysis is explicitly permitted.');return;}
  if(!active){show('Recognition stopped','Use Start recognition to begin.');return;}
  const now=performance.now(),fresh=observationAge(lastFrame,now,1000).fresh;
  if(!fresh){show('Waiting for fresh screen data','No successful recognition snapshot within one second. Check the recognition status.');return;}
  const a=resolveManual(autoValues(),locks),exact=new Set(Object.keys(locks));
  if(observationAge(lastOcrAt,now,1000).fresh){
   if(lastTable?.pot&&!lastTable.pot.approximate)exact.add('pot');
   if(lastTable?.seats?.hero?.stack&&!lastTable.seats.hero.stack.approximate)exact.add('hero.stack');
  }
  if(betMemory.street===a.street&&!betMemory.boundary&&!betMemory.uncertain){
   for(const id of Object.keys(SEATS)){const b=betMemory.seats[id];if(b.observed&&!b.approximate&&!b.warning&&observationAge(b.lastSeen,now,1000).fresh)exact.add(id+'.bet');}
  }
  const input=decisionInputs(a,exact,{confirmed:$('practice-action-confirm').checked,opponents:Number($('live-opponents').value)});
  const rec=decisionFromEquity(input,equityResult);
  show(rec.action||rec.reason,rec.action?'Check/call/fold model · equity '+(rec.equity*100).toFixed(1)+'% · pot odds '+(rec.potOdds*100).toFixed(1)+'%':rec.reason==='Waiting for card equity'?'Check card recognition and simulation status.':'Review the required practice inputs.');
 }
 function autoValues(){
  const now=performance.now(),result=observationAge(lastFrame,now,1000).fresh?lastResult:null,obs=result?.table_observation,age=observationAge(lastOcrAt,now,1000),num=age.fresh?lastTable:null;
  const a={street:result?.street_candidate??(result?cardMemory?.displayStreet:undefined),pot:num?.pot?.value,dealer:obs?.dealer?.candidate??undefined,turn:obs?.turn_candidate??undefined};
  const groups=[result&&(cardMemory?.displayHole||result.hole_slots),result&&(cardMemory?.displayBoard||result.board_slots)];
  CARD_KEYS.forEach((key,i)=>{const slot=i<2?groups[0]?.[i]:groups[1]?.[i-2];a[key]=slot===null?null:slot?.candidate??undefined;});
  for(const id of Object.keys(SEATS)){
   const s=obs?.seats?.[id],n=num?.seats?.[id];
   a[id+'.stack']=n?.stack?.value;
   const tracked=betMemory.seats[id];
   const direct=n?.bet;
   a[id+'.bet']=result&&direct&&tracked?.observed&&tracked.value===direct.value&&!tracked.warning&&observationAge(tracked.lastSeen,now,1000).fresh?freshBetValue(betMemory,id,a.street,now):undefined;
   a[id+'.status']=n?.status_candidate??s?.participation_candidate??undefined;
   a[id+'.cards']=s?.card_visible_candidate?'Visible':undefined;
   a[id+'.participation']=s?.participation_candidate??undefined;
  }
  return a;
 }
 function paint(){
  const now=performance.now(),a=autoValues(),effective=resolveManual(a,locks),age=observationAge(lastOcrAt,now,1000),direct=directNumericSnapshot(lastResult,lastOcrState?.state,lastFrame,now);
  for(const map of [editors,inlineEditors,popupEditors])for(const [key,e] of map){
   const locked=isLocked(locks,key),v=effective[key];
   e.box.classList.toggle('manual-locked',locked);e.auto.disabled=!locked;e.lock.textContent=locked?'Update':'Lock';
   if(document.activeElement!==e.input&&!e.dirty)e.input.value=inputValue(v,e.field);
   e.note.textContent=(locked?'LOCKED · ':'Auto · ')+displayValue(key,v);
   e.input.title=(locked?'Locked':'Auto')+' · '+displayValue(key,v);
  }
  const coverage=snapshotCoverage(lastResult,locks,observationAge(lastFrame,now,1000).fresh,!!direct);
  $('snapshot-coverage').textContent='Field availability: '+(coverage.total-coverage.counts.unknown)+' / '+coverage.total+' · '+coverage.counts.manual+' manual · '+coverage.counts.candidate+' candidates · '+coverage.counts.approximate+' approximate · '+coverage.counts.unknown+' unknown. Not an accuracy score.';
  $('snapshot-reconciliation').textContent=!observationAge(lastFrame,now,1000).fresh?'Stack/pot reconciliation: no fresh snapshot':conservation?.status==='unavailable'||!conservation?'Stack/pot reconciliation: '+(conservation?.reason||'waiting for adjacent snapshots'):'Stack/pot reconciliation: '+conservation.status+' · '+Object.entries(conservation.seats).filter(([,s])=>s.status==='conflict'||s.status==='hypothesis').map(([id,s])=>SEATS[id]+': '+s.status+' '+s.implied).join(' · ');
  const show=key=>displayValue(key,effective[key])+(isLocked(locks,key)?' [locked]':'');
  $('live-dealer').textContent=show('dealer');$('live-turn').textContent=show('turn');$('live-pot').textContent=show('pot');
  $('live-stacks').textContent=Object.keys(SEATS).map(id=>SEATS[id]+': '+show(id+'.stack')).join(' · ');
  $('live-bet-state').textContent=betMemory.status;$('live-ocr-age').textContent=lastOcrState?.state==='failed'||lastOcrState?.state==='unavailable'?'OCR '+lastOcrState.state+': '+(lastOcrState.detail||'No reading'):direct?'Latest capture '+((now-lastFrame)/1000).toFixed(1)+' s ago'+(!age.fresh?' · awaiting round confirmation':''):'No fresh OCR sample';
  const body=$('live-table-body');body.replaceChildren();
  for(const [id,label] of Object.entries(SEATS)){
   const n=direct?.seats?.[id]||{},row=document.createElement('tr'),held=retainedRoundBet(betMemory,id,betMemory.street),total=observedHandCommitment(betMemory,id);if(effective.turn===id)row.className='active-observation';
   const values=[label,effective.dealer===id?'D':'—',effective.turn===id?'Turn cue':'—',show(id+'.stack'),n.stack?.display??'?',n.bet?.display??'?',isLocked(locks,id+'.bet')?show(id+'.bet'):held?trackedBetLabel(held)+(effective[id+'.bet']===undefined?' (retained)':''):'? (unobserved)',total?(total.approximate?'≈':'')+total.value.toLocaleString('en-CA')+' ('+total.observedRounds+'/'+total.rounds+' rounds observed)':'?',show(id+'.status'),show(id+'.cards'),show(id+'.participation'),[n.stack_raw,n.bet_raw,n.status_raw].filter(Boolean).join(' / ')||'—'];
   values.forEach((value,i)=>{const td=document.createElement('td');td.textContent=value;if(i===6)td.title=isLocked(locks,id+'.bet')?'Manual lock':betMemory.seats[id].warning||betMemory.seats[id].source;row.append(td);});body.append(row);
  }
  const cardLabel=key=>{const v=effective[key];return (v===null?'·':v??'?')+(isLocked(locks,key)?' [L]':'');};
  $('manual-effective-cards').textContent=CARD_KEYS.slice(0,2).map(cardLabel).join(' ')+' | '+CARD_KEYS.slice(2).map(cardLabel).join(' ');
  $('live-cards').textContent=$('manual-effective-cards').textContent;
  $('live-street').textContent=show('street');
  for(const [id,n] of seatNodes){const [x,y]=overlayPosition(SEAT_ANCHORS[id],lastResult?.capture_crop);n.tile.style.left=x+'%';n.tile.style.top=y+'%';n.tile.classList.toggle('screen-seat-active',effective.turn===id);n.note.textContent=(effective.dealer===id?'D · ':'')+(effective.turn===id?'TURN · ':'')+displayValue(id+'.status',effective[id+'.status']);}
  paintDecision();
 }
 function render(result,ocr,ocrStatus,capturedAt){
  if(capturedAt<resetAt||(lastFrame!==null&&capturedAt<=lastFrame))return;
  const now=performance.now();
  if(!observationAge(capturedAt,now,1000).fresh){clearAuto();betMemory=interruptBetMemory(betMemory);paint();return;}
  lastResult=result;
  lastTimings=result.timings_ms||null;
  lastOcrState=$('live-ocr').checked?ocrStatus:{state:'disabled'};
  ocrBackend=ocrStatus?.backend||ocrBackend;
  const prior=betMemory,sampled=ocr&&ocrStatus?.state==='sampled'&&$('live-ocr').checked;
  const currentSnapshot=sampled?{at:capturedAt,result}:null;
  conservation=reconcileSnapshots(previousSnapshot,currentSnapshot,{potIncludesBets:$('practice-action-confirm').checked});
  previousSnapshot=currentSnapshot;
  betMemory=updateBetMemory(betMemory,result,{capturedAt,now,ocr:sampled});
  const numeric=sampled?currentNumericSample(null,result,betMemory,prior,{capturedAt,now,sampled}):null;
  lastTable=numeric?.table??null;lastOcrAt=numeric?.at??null;
  cardMemory=updateCardMemory(cardMemory,result,capturedAt);lastFrame=capturedAt;refreshCandidate(true);if(now-lastPaintAt>=125){lastPaintAt=now;paint();}
  $('live-overlay').hidden=false;
 }
 function reportQueue(q){const r=q.report(performance.now()),age=r.lastSnapshotAgeMs;$('frame-telemetry').textContent='Snapshots '+r.processed+'/'+r.captured+' · deliberately sampled out '+r.intentionalSkips+' · source gaps '+r.sourceMissed+' · presented '+(r.sourceFps===null?'—':r.sourceFps.toFixed(1))+' FPS · callbacks '+(r.callbackFps===null?'—':r.callbackFps.toFixed(1))+' FPS · snapshots '+r.processingFps.toFixed(1)+'/s · snapshot age '+(age===null?'—':(age/1000).toFixed(2)+' s')+' · in flight '+(r.oldestAgeMs/1000).toFixed(2)+' s · OCR '+ocrBackend+(lastTimings?' · recognition '+lastTimings.total.toFixed(1)+' ms':'');if(age===null)status('Acquiring first table snapshot.');else if(age>1000)status('Snapshot stale: full table refresh exceeded one second.');else status('Current-state recognition running · snapshot age '+(age/1000).toFixed(2)+' s · automatic values remain candidates.');}
 function failQueue(q,error){reportQueue(q);stop();status('Frame coverage failed: '+String(error.message||error)+'. Restart after resolving the bottleneck.');}
 async function drain(current,q){
  if(draining||!active||epoch!==current||q!==frameQueue)return;
  draining=true;
  try{
   while(active&&epoch===current&&q===frameQueue&&q.front()){
    const item=q.front(),encoded=await item.encoded;
    if(!active||epoch!==current||q!==frameQueue)return;
    if(encoded.error||!encoded.blob)throw Error('Frame '+item.id+' encoding failed');
    controller=new AbortController();
    const response=await fetch('/api/practice-frame',{method:'POST',headers:{'Content-Type':'image/png','X-Practice-Consent':'yes','X-Frame-Session':session,'X-Frame-OCR':$('live-ocr').checked?'yes':'no','X-Frame-Sequence':String(item.id)},body:encoded.blob,signal:controller.signal});
    const data=await response.json();if(!active||epoch!==current||q!==frameQueue)return;
    if(!response.ok)throw Error(data.error||'Recognition failed');
    if(data.sequence!==item.id)throw Error('Backend sequence mismatch');
    q.complete(item.id);
    if(item.capturedAt>=resetAt){
     render(data.result,data.ocr_sampled,data.ocr_status,item.capturedAt);
    }
   }
  }catch(e){if(active&&epoch===current&&q===frameQueue)failQueue(q,e);}
  finally{if(epoch===current){draining=false;controller=null;}}
 }
 function captureNext(current,q){
  if(!active||epoch!==current||!canRun()||q!==frameQueue)return;
  frameCallback=video.requestVideoFrameCallback((now,meta)=>{
   frameCallback=null;
   if(!active||epoch!==current||q!==frameQueue||!canRun())return;
   try{
    q.enqueue({presentedFrames:meta.presentedFrames,capturedAt:now},snapshot);
    captureNext(current,q);void drain(current,q);
   }catch(e){failQueue(q,e);}
  });
 }
 $('practice-consent').onchange=()=>{if(!$('practice-consent').checked)stop();refresh();};
 $('live-start').onclick=async()=>{if(!canRun()||!$('practice-consent').checked)return;if(!video.requestVideoFrameCallback){status('Frame accounting requires a browser with video frame callbacks.');return;}stop();active=true;epoch++;session=crypto.randomUUID();$('live-start').disabled=true;$('live-stop').disabled=false;status('Preparing Python recognizer before capture…');$('frame-telemetry').textContent='Preparing backend. Frame counting starts when ready.';const current=epoch;controller=new AbortController();try{const response=await fetch('/api/practice-ready',{method:'POST',headers:{'X-Practice-Consent':'yes','X-Frame-Session':session},signal:controller.signal});const data=await response.json();if(!active||epoch!==current)return;if(!response.ok||!data.ready)throw Error(data.error||'Backend not ready');if($('live-ocr').checked&&!data.ocr)throw Error(data.ocr_error||'OCR unavailable');controller=null;ocrBackend=data.ocr_backend||'unknown';status('Backend ready. Tracking source frames.');frameQueue=new CurrentStateQueue(100);const q=frameQueue;decisionTimer=setInterval(()=>{paint();if(frameQueue===q)reportQueue(q);},125);captureNext(current,q);}catch(e){if(active&&epoch===current){stop();status('Recognition startup failed: '+e.message);}}};
 $('live-stop').onclick=stop;
 $('live-reset-bets').onclick=()=>{betMemory={...createBetMemory(),last:performance.now()};paint();};
 $('manual-new-hand').onclick=()=>{if(!confirm('Clear all manual locks and automatic observations for a new hand?'))return;closePopup();locks={};resetAt=performance.now();betMemory=createBetMemory();clearAuto();for(const map of [editors,inlineEditors])for(const e of map.values()){e.dirty=false;e.input.value='';e.input.setCustomValidity('');}save();paint();};
 $('live-opponents').onchange=()=>{clearEquity();if(active&&reading?.stable&&observationAge(lastFrame,performance.now(),1000).fresh)evaluate(reading.stable);paintDecision();};
 $('live-ocr').onchange=()=>{lastOcrState=null;previousSnapshot=null;conservation=null;lastOcrAt=null;lastTable=null;betMemory=createBetMemory();paint();};
 save();paint();refresh();
 return {stop,refresh,reset:()=>{if(active){stop();refresh();status('Source geometry changed. Restart recognition when aligned. Manual locks retained.');}}};
}
