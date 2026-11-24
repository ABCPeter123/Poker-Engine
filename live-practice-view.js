import {candidateCards,stableReading,practiceInput,updateCardMemory,observationAge,createBetMemory,updateBetMemory,trackedBetLabel,interruptBetMemory} from './live-practice.js';
import {SEATS,FIELDS,CARD_KEYS,isLocked,setManual,releaseManual,resolveManual,loadManual,saveManual,displayValue,effectiveCards} from './manual-observations.js';

export function attachPractice({video,screen,canRun,rotation}){
 const $=id=>document.getElementById(id),panel=$('live-panel'),canvas=document.createElement('canvas');
 let locks=loadManual({getItem:key=>localStorage.getItem(key)}),lastOcrAt=null,lastTable=null,cardMemory=null,betMemory=createBetMemory();
 let active=false,session='',epoch=0,timer=null,controller=null,equityWorker=null,reading=null,requestedKey='',lastFrame=0,resetAt=-1,lastResult=null;
 const editors=new Map();
 const status=msg=>$('live-status').textContent=msg, metric=msg=>$('live-equity').textContent=msg;
 function clearEquity(){if(equityWorker){equityWorker.terminate();equityWorker=null;}requestedKey='';metric('—');}
 function clearAuto(){lastResult=null;lastOcrAt=null;lastTable=null;cardMemory=null;reading=null;lastFrame=0;clearEquity();}
 function save(){const ok=saveManual({setItem:(key,value)=>localStorage.setItem(key,value)},locks);$('manual-lock-count').textContent=Object.keys(locks).length+' locked'+(ok?' · saved locally':' · browser storage unavailable');}
 function stop(){betMemory=createBetMemory();clearAuto();active=false;epoch++;clearTimeout(timer);timer=null;controller?.abort();controller=null;$('live-overlay').hidden=true;$('live-start').disabled=!canRun()||!$('practice-consent').checked;$('live-stop').disabled=true;status('Recognition stopped. Manual locks retained.');paint();}
 function refresh(){panel.hidden=false;if(!canRun()&&active)stop();$('live-start').disabled=active||!canRun()||!$('practice-consent').checked;}
 function snapshot(){const w=video.videoWidth,h=video.videoHeight,deg=rotation(),swap=Math.abs(deg%180)===90;if(!w||!h)throw Error('Waiting for video dimensions');const scale=Math.min(1,1920/Math.max(w,h));canvas.width=Math.round((swap?h:w)*scale);canvas.height=Math.round((swap?w:h)*scale);const c=canvas.getContext('2d');c.translate(canvas.width/2,canvas.height/2);c.rotate(deg*Math.PI/180);c.drawImage(video,-w*scale/2,-h*scale/2,w*scale,h*scale);return new Promise(resolve=>canvas.toBlob(resolve,'image/png'));}
 function evaluate(candidate){const opponents=Number($('live-opponents').value);if(!active||!canRun()||!$('practice-consent').checked||!candidate||!opponents){clearEquity();return;}const key=candidate.key+'|'+opponents;if(key===requestedKey)return;clearEquity();requestedKey=key;const current=epoch,worker=new Worker('./worker.js',{type:'module'});equityWorker=worker;metric('Calculating…');worker.onmessage=({data})=>{if(epoch===current&&equityWorker===worker&&requestedKey===key){metric(data.error?'Unavailable':(data.result.equity*100).toFixed(1)+'%');equityWorker=null;}worker.terminate();};worker.onerror=()=>{if(equityWorker===worker){metric('Unavailable');equityWorker=null;requestedKey='';}worker.terminate();};worker.postMessage({id:current,input:practiceInput(candidate,opponents)});}
 function editor(f,parent){
  const box=document.createElement('div');box.className='manual-field';
  const label=document.createElement('label');label.textContent=f.label;
  const input=document.createElement(f.type==='choice'?'select':'input');input.setAttribute('aria-label',f.label+' '+f.key);
  if(f.type==='choice'){for(const value of ['',...f.choices]){const option=document.createElement('option');option.value=value;option.textContent=value===''?'Choose…':displayValue(f.key,value);input.append(option);}}
  else{input.type='text';input.autocomplete='off';input.spellcheck=false;input.inputMode=f.type==='amount'?'numeric':'text';}
  const buttons=document.createElement('div');buttons.className='manual-buttons';
  const lock=document.createElement('button'),auto=document.createElement('button');lock.type=auto.type='button';lock.textContent='Lock';auto.textContent='Auto';
  const note=document.createElement('small');note.className='hint';
  function commit(){try{locks=setManual(locks,f.key,input.value);input.setCustomValidity('');save();reading=null;clearEquity();paint();}catch(e){input.setCustomValidity(e.message);input.reportValidity();}}
  lock.onclick=commit;auto.onclick=()=>{locks=releaseManual(locks,f.key);input.value='';input.setCustomValidity('');save();reading=null;clearEquity();paint();};
  input.oninput=()=>input.setCustomValidity('');
  input.onchange=()=>{if(input.value!=='')commit();};
  input.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();commit();}};
  label.append(input);buttons.append(lock,auto);box.append(label,buttons,note);parent.append(box);
  editors.set(f.key,{box,input,lock,auto,note});
 }
 for(const f of FIELDS.filter(f=>!f.key.includes('.')||CARD_KEYS.includes(f.key)))editor(f,$('manual-global'));
 for(const [id,name] of Object.entries(SEATS)){const group=document.createElement('div');group.className='manual-seat';const title=document.createElement('h4');title.textContent=name;const grid=document.createElement('div');grid.className='manual-grid';group.append(title,grid);for(const f of FIELDS.filter(f=>f.key.startsWith(id+'.')))editor(f,grid);$('manual-seats').append(group);}
 function autoValues(){
  const result=lastResult,obs=result?.table_observation,age=observationAge(lastOcrAt,performance.now()),num=age.fresh?lastTable:null;
  const a={street:result?.street_candidate??cardMemory?.displayStreet??undefined,pot:age.fresh?lastTable?.pot?.value:undefined,dealer:obs?.dealer?.candidate??undefined,turn:obs?.turn_candidate??undefined};
  const groups=[cardMemory?.displayHole||result?.hole_slots,cardMemory?.displayBoard||result?.board_slots];
  CARD_KEYS.forEach((key,i)=>{const slot=i<2?groups[0]?.[i]:groups[1]?.[i-2];a[key]=slot===null?null:slot?.candidate??undefined;});
  for(const id of Object.keys(SEATS)){
   const s=obs?.seats?.[id],n=num?.seats?.[id];
   a[id+'.stack']=n?.stack?.value;
   a[id+'.bet']=betMemory.seats[id].value;
   a[id+'.status']=n?.status_candidate??s?.participation_candidate??undefined;
   a[id+'.cards']=s?.card_visible_candidate?'Visible':undefined;
   a[id+'.participation']=s?.participation_candidate??undefined;
  }
  return a;
 }
 function paint(){
  const a=autoValues(),effective=resolveManual(a,locks),obs=lastResult?.table_observation,age=observationAge(lastOcrAt,performance.now()),num=age.fresh?lastTable:null;
  for(const [key,e] of editors){
   const locked=isLocked(locks,key),v=effective[key];
   e.box.classList.toggle('manual-locked',locked);e.auto.disabled=!locked;e.lock.textContent=locked?'Update':'Lock';
   // Never replace an input while the user is typing. Autofill only when it
   // is not focused, and keep an unlocked input's current draft intact.
   if(locked&&document.activeElement!==e.input)e.input.value=locks[key]===null?'-':String(locks[key]);
   if(!locked&&e.input.tagName==='INPUT')e.input.placeholder=displayValue(key,a[key]);
   e.note.textContent=(locked?'LOCKED · ':'Auto · ')+displayValue(key,v);
  }
  const show=key=>displayValue(key,effective[key])+(isLocked(locks,key)?' [locked]':'');
  $('live-dealer').textContent=show('dealer');$('live-turn').textContent=show('turn');$('live-pot').textContent=show('pot');
  $('live-stacks').textContent=Object.keys(SEATS).map(id=>SEATS[id]+': '+show(id+'.stack')).join(' · ');
  $('live-bet-state').textContent=betMemory.status;$('live-ocr-age').textContent=age.fresh?'Captured '+(age.ageMs/1000).toFixed(1)+' s ago':age.ageMs===null?'Not sampled':'Stale ('+(age.ageMs/1000).toFixed(1)+' s old)';
  const body=$('live-table-body');body.replaceChildren();
  for(const [id,label] of Object.entries(SEATS)){
   const n=num?.seats?.[id]||{},row=document.createElement('tr');if(effective.turn===id)row.className='active-observation';
   const values=[label,effective.dealer===id?'D':'—',effective.turn===id?'Turn cue':'—',show(id+'.stack'),n.bet?.display??'?',isLocked(locks,id+'.bet')?show(id+'.bet'):trackedBetLabel(betMemory.seats[id]),show(id+'.status'),show(id+'.cards'),show(id+'.participation'),[n.stack_raw,n.bet_raw,n.status_raw].filter(Boolean).join(' / ')||'—'];
   values.forEach((value,i)=>{const td=document.createElement('td');td.textContent=value;if(i===5)td.title=isLocked(locks,id+'.bet')?'Manual lock':betMemory.seats[id].warning||betMemory.seats[id].source;row.append(td);});body.append(row);
  }
  const cardLabel=key=>{const v=effective[key];return (v===null?'·':v??'?')+(isLocked(locks,key)?' [L]':'');};
  $('manual-effective-cards').textContent=CARD_KEYS.slice(0,2).map(cardLabel).join(' ')+' | '+CARD_KEYS.slice(2).map(cardLabel).join(' ');
  $('live-cards').textContent=$('manual-effective-cards').textContent;
  $('live-street').textContent=show('street');
 }
 function render(result,ocr,ocrStatus,capturedAt){
  if(capturedAt<resetAt)return;
  lastResult=result;
  if(ocr&&$('live-ocr').checked&&ocrStatus?.state!=='failed'){lastTable={...result.table_observation,pot:result.number_candidates?.pot?.candidate};lastOcrAt=capturedAt;}
  betMemory=updateBetMemory(betMemory,result,{capturedAt,now:performance.now(),ocr:ocr&&ocrStatus?.state!=='failed'&&$('live-ocr').checked});
  const now=performance.now();cardMemory=updateCardMemory(cardMemory,result,now);
  const cardLocks=CARD_KEYS.some(k=>isLocked(locks,k))||isLocked(locks,'street');
  // Manual review observations are authoritative for display. Do not
  // calculate against a raw deck that disagrees with a manual correction.
  const candidate=cardLocks?null:candidateCards(result);
  reading=stableReading(reading,candidate,now);lastFrame=now;paint();
  if(ocrStatus?.state==='unavailable'||ocrStatus?.state==='failed')$('live-ocr-age').textContent='OCR '+ocrStatus.state+': '+(ocrStatus.detail||'Scan failed');
  $('live-confidence').textContent=cardLocks?'Manual card/street locks · raw equity paused':cardMemory?.carried.length?'Cached card, waiting for fresh recognition':reading.stable?'Repeated candidate (not verified)':candidate?'Waiting for second matching frame':'Uncertain / incomplete';
  if(!reading.stable)clearEquity();else evaluate(reading.stable);$('live-overlay').hidden=false;
 }
 async function tick(current){if(!active||epoch!==current||!canRun())return;try{const capturedAt=performance.now();const blob=await snapshot();if(!active||epoch!==current)return;if(!blob)throw Error('Cannot encode frame');controller=new AbortController();const response=await fetch('/api/practice-frame',{method:'POST',headers:{'Content-Type':'image/png','X-Practice-Consent':'yes','X-Frame-Session':session,'X-Frame-OCR':$('live-ocr').checked?'yes':'no'},body:blob,signal:controller.signal});const data=await response.json();if(!active||epoch!==current)return;if(!response.ok)throw Error(data.error||'Recognition failed');if(capturedAt>=resetAt){render(data.result,data.ocr_sampled,data.ocr_status,capturedAt);const crop=data.result?.capture_crop;status('Frame processed in '+((performance.now()-capturedAt)/1000).toFixed(1)+' s · candidates from captured frame'+(crop?' · game area '+crop.visible_size.join(' × '):''));}}catch(e){if(!active||epoch!==current)return;clearAuto();betMemory=interruptBetMemory(betMemory);paint();$('live-overlay').hidden=true;status(e.message);}finally{if(active&&epoch===current){controller=null;timer=setTimeout(()=>tick(current),800);}}}
 $('practice-consent').onchange=()=>{if(!$('practice-consent').checked)stop();refresh();};
 $('live-start').onclick=()=>{if(!canRun()||!$('practice-consent').checked)return;stop();active=true;epoch++;session=crypto.randomUUID();$('live-start').disabled=true;$('live-stop').disabled=false;status('Starting Python recognizer…');tick(epoch);};
 $('live-stop').onclick=stop;
 $('live-reset-bets').onclick=()=>{betMemory={...createBetMemory(),last:performance.now()};paint();};
 $('manual-new-hand').onclick=()=>{if(!confirm('Clear all manual locks and automatic observations for a new hand?'))return;locks={};resetAt=performance.now();betMemory=createBetMemory();clearAuto();for(const e of editors.values())e.input.value='';save();paint();};
 $('live-opponents').onchange=()=>{clearEquity();if(active&&reading?.stable&&performance.now()-lastFrame<6000)evaluate(reading.stable);};
 $('live-ocr').onchange=()=>{lastOcrAt=null;lastTable=null;betMemory=createBetMemory();paint();};
 save();paint();refresh();
 return {stop,refresh,reset:()=>{if(active){stop();refresh();status('Source geometry changed. Restart recognition when aligned. Manual locks retained.');}}};
}
