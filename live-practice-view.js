import {CurrentStateQueue} from './frame-queue.js';
import {updateHeroWagerEvidence,pauseHandPresence,scenarioProgress,withRetainedRoundWagers,updateHeroAllIn,updateTurnMemory,conditionalDeck,handContributionDisplay,observedCallHypothesis,heroCardPresence,updateActionEvidence,observationScenarioCounts,observationSummary,updateHandPresence,updateDisplayEvidence,displayEvidenceValues,observedOpponentRange,retainedRoundBet,observedHandCommitment,directNumericSnapshot,snapshotCoverage,reconcileSnapshots,freshBetValue,currentNumericSample,candidateCards,stableReading,practiceInput,updateCardMemory,observationAge,createBetMemory,updateBetMemory,trackedBetLabel,interruptBetMemory} from './live-practice.js';
import {simplePracticeAction,simplePriceDetail,displayCallObservation,observedPotAccounting,practiceRaiseSizing,sizedPracticeHeadline,roundedPracticeScenario,practicePriceHeadline,roundedCallObservation,observedCallPrice,conservativeRaiseBounds,observePracticeBlind,conditionalRaiseComparison,practiceHeadline,practicePanelModel,conditionalCallModel,practiceOpponentCount,SEAT_ANCHORS,overlayPosition,decisionInputs,decisionFromEquity,inputValue} from './practice-decision.js';
import {SEATS,FIELDS,CARD_KEYS,isLocked,setManual,releaseManual,resolveManual,loadManual,saveManual,displayValue,effectiveCards} from './manual-observations.js';

export function attachPractice({video,screen,canRun,rotation}){
 const $=id=>document.getElementById(id),panel=$('live-panel'),canvas=document.createElement('canvas');
 let locks=loadManual({getItem:key=>localStorage.getItem(key)}),lastOcrAt=null,lastTable=null,cardMemory=null,betMemory=createBetMemory();
 let active=false,session='',epoch=0,timer=null,controller=null,equityWorker=null,reading=null,requestedKey='',lastFrame=null,resetAt=-1,lastResult=null;
 const editors=new Map(),inlineEditors=new Map(),popupEditors=new Map(),seatNodes=new Map();
 let simulationDeck='',simulationCache=new Map(),simulationPending=new Set(),simulationState='idle',scenarioResults=null,equityResult=null,decisionTimer=null,ocrBackend='unknown',lastTimings=null,lastOcrState=null,previousSnapshot=null,conservation=null,frameQueue=null,frameCallback=null,draining=false,lastPaintAt=-Infinity,displayMemory=null,handPresence=null,actionEvidence=null,callHypotheses={},turnMemory=null,blindEvidence=null,heroAllIn=null,heroWagerEvidence=null,autoPaused=false;
 const preferenceKey='pokerist.practice-auto-start.v1';
 try{$('practice-consent').checked=localStorage.getItem(preferenceKey)!=='off';}catch{$('practice-consent').checked=true;}
 const status=msg=>$('live-status').textContent=msg, metric=msg=>{$('live-equity').textContent=msg;$('simulation-observation-status').textContent='Practice simulation: '+msg;};
 function clearEquity(){simulationDeck='';simulationCache.clear();simulationPending.clear();simulationState='idle';scenarioResults=null;equityResult=null;if(equityWorker){equityWorker.terminate();equityWorker=null;}requestedKey='';metric('—');}
 function clearAuto(){heroWagerEvidence=null;heroAllIn=null;blindEvidence=null;turnMemory=null;callHypotheses={};actionEvidence=null;handPresence=null;displayMemory=null;lastOcrState=null;lastTimings=null;previousSnapshot=null;conservation=null;lastResult=null;lastOcrAt=null;lastTable=null;cardMemory=null;reading=null;lastFrame=null;clearEquity();}
 function save(){const ok=saveManual({setItem:(key,value)=>localStorage.setItem(key,value)},locks);$('manual-lock-count').textContent=Object.keys(locks).length+' locked'+(ok?' · saved locally':' · browser storage unavailable');}
 function stop({preserve=false}={}){closePopup();clearInterval(decisionTimer);decisionTimer=null;if(preserve){betMemory=interruptBetMemory(betMemory);handPresence=pauseHandPresence(handPresence);lastFrame=null;lastOcrAt=null;lastTable=null;lastOcrState=null;previousSnapshot=null;conservation=null;cardMemory=null;reading=null;clearEquity();}else{betMemory=createBetMemory();clearAuto();}active=false;epoch++;clearTimeout(timer);timer=null;if(frameCallback!==null)video.cancelVideoFrameCallback?.(frameCallback);frameCallback=null;frameQueue=null;draining=false;controller?.abort();controller=null;$('live-overlay').hidden=true;$('live-start').disabled=!canRun()||!$('practice-consent').checked;$('live-stop').disabled=true;status(preserve?'Recognition paused. Hand observations retained.':'Recognition stopped. Manual locks retained.');paint();}
 function refresh(){panel.hidden=false;if(!canRun()&&active)stop({preserve:true});$('live-start').disabled=active||!canRun()||!$('practice-consent').checked;$('screen-seat-layer').hidden=!canRun();$('screen-decision').hidden=!canRun();if(!canRun())closePopup();paintDecision();if(canRun()&&!active&&!autoPaused&&$('practice-consent').checked)void startRecognition();}
 function snapshot(){const w=video.videoWidth,h=video.videoHeight,deg=rotation(),swap=Math.abs(deg%180)===90;if(!w||!h)throw Error('Waiting for video dimensions');const scale=Math.min(1,1920/Math.max(w,h)),cw=Math.round((swap?h:w)*scale),ch=Math.round((swap?w:h)*scale);if(canvas.width!==cw||canvas.height!==ch){canvas.width=cw;canvas.height=ch;}const c=canvas.getContext('2d',{alpha:false});c.setTransform(1,0,0,1,0,0);c.translate(cw/2,ch/2);c.rotate(deg*Math.PI/180);c.drawImage(video,-w*scale/2,-h*scale/2,w*scale,h*scale);return new Promise(resolve=>canvas.toBlob(resolve,'image/png'));}
 function evaluate(candidate){
  if(!active||!canRun()||!$('practice-consent').checked||!candidate){clearEquity();metric('Cards incomplete');return;}
  const {count:selected}=practiceOpponentCount($('live-opponents').value,locks);
  const range=observedOpponentRange(observationAge(lastFrame,performance.now(),1000).fresh?lastResult:null,locks,actionEvidence);
  const counts=observationScenarioCounts(selected,range);
  if(simulationDeck!==candidate.key){clearEquity();simulationDeck=candidate.key;}
  if(!counts.length){requestedKey='';scenarioResults=null;equityResult=null;simulationState='no opponents';metric('No opposing seats in observation');return;}
  const key=candidate.key+'|'+counts.join(',')+'|'+(selected??'observed');
  requestedKey=key;
  const report=()=>{
   if(requestedKey!==key)return;
   const progress=scenarioProgress(candidate.key,counts,simulationCache);
   simulationState=progress.state;
   scenarioResults=progress.state==='ready'?{key,cardKey:candidate.key,counts:[...counts],equities:progress.equities}:null;
   equityResult=selected&&progress.state==='ready'?simulationCache.get(selected):null;
   const values=counts.filter(n=>simulationCache.has(n)).map(n=>{const e=simulationCache.get(n);return n+' opp: '+(e===null?'unavailable':(100*e).toFixed(1)+'%');});
   metric((selected?'Selected count · ':'Conditional random hands · ')+values.join(' | ')+(progress.state==='pending'?' · calculating…':progress.state==='failed'?' · simulation failed':''));
  };
  report();
  const missing=counts.filter(n=>!simulationCache.has(n)&&!simulationPending.has(n));
  if(!missing.length)return;
  if(!equityWorker){
   const current=epoch,deck=candidate.key,worker=new Worker('./worker.js',{type:'module'});
   equityWorker=worker;
   worker.onmessage=({data})=>{
    if(epoch!==current||equityWorker!==worker||simulationDeck!==deck||!simulationPending.has(data.id))return;
    simulationPending.delete(data.id);
    const value=data.result?.equity;
    simulationCache.set(data.id,!data.error&&Number.isFinite(value)&&value>=0&&value<=1?value:null);
    if(!simulationPending.size){equityWorker=null;worker.terminate();}
    if(reading?.stable?.key===deck){evaluate(reading.stable);paintDecision();}
   };
   worker.onerror=()=>{
    if(equityWorker===worker){
     for(const n of simulationPending)simulationCache.set(n,null);
     simulationPending.clear();equityWorker=null;simulationState='failed';
     if(reading?.stable?.key===deck){evaluate(reading.stable);paintDecision();}
    }
    worker.terminate();
   };
  }
  for(const n of missing){simulationPending.add(n);equityWorker.postMessage({id:n,input:practiceInput(candidate,n)});}
 }


 function changed(key){
  save();
  if(CARD_KEYS.includes(key)||key==='street'){reading=null;clearEquity();refreshCandidate(false);}else if(key.endsWith('.status')||key.endsWith('.participation')){clearEquity();refreshCandidate(false);}
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
  for(const f of FIELDS.filter(f=>f.key===id+'.stack'))editor(f,tile,inlineEditors,true);
  const contribution=document.createElement('div');contribution.className='screen-amount';
  const contributionLabel=document.createElement('label');contributionLabel.textContent='B total';
  const contributionValue=document.createElement('input');contributionValue.readOnly=true;contributionValue.setAttribute('aria-label',name+' cumulative observed hand contribution');contributionValue.value='0';
  contributionLabel.append(contributionValue);contribution.append(contributionLabel);tile.append(contribution);
  const total=document.createElement('small');total.className='screen-seat-note';tile.append(note,total);$('screen-seat-layer').append(tile);seatNodes.set(id,{tile,header,note,total,contributionValue});
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
 $('practice-big-blind').oninput=()=>paintDecision();
 $('practice-pot-convention').onchange=()=>paintDecision();
 function currentDeck(now){return conditionalDeck(effectiveCards(lastResult,locks),cardMemory,handPresence,betMemory.street,now,reading?.stable);}
 function refreshCandidate(sample){
  if(!active)return;
  if(heroCardPresence(lastResult)==='absent'){reading=null;clearEquity();metric('Not playing · no hole cards visible');return;}
  const now=performance.now(),complete=CARD_KEYS.every(key=>isLocked(locks,key));
  const fresh=observationAge(lastFrame,now,1000).fresh;
  const candidate=complete||fresh?currentDeck(now):null;
  if(complete&&candidate)reading={key:candidate.key,count:2,stable:candidate,last:now};
  else if(sample)reading=stableReading(reading,candidate,lastFrame??now);
  else if(!candidate||reading?.key!==candidate.key)reading=null;
  if(!reading?.stable){clearEquity();metric('Cards incomplete');}else evaluate(reading.stable);
  $('live-confidence').textContent=complete?'Manually locked deck':reading?.stable?(candidate?.retained?.length?'Conditional equity · retained card evidence':'Repeated effective reading'):'Cards incomplete';
 }
 function paintDecision(){
  const show=(message,description='')=>{for(const id of ['live-action','decision-status-text']){const el=$(id);if(el.textContent!==message)el.textContent=message;}for(const id of ['live-action-detail','decision-status-detail']){const el=$(id);if(el.textContent!==description)el.textContent=description;}};
  $('conditional-model-result').textContent='';$('optional-model-result').textContent='';
  if(!$('practice-consent').checked){show('Practice permission required','Recognition disabled.');return;}
  if(!canRun()){show('No source connected');return;}
  if(!active){show('Recognition stopped');return;}
  const now=performance.now(),fresh=observationAge(lastFrame,now,1000).fresh;
  const direct=directNumericSnapshot(lastResult,lastOcrState?.state,lastFrame,now);
  const numeric=withRetainedRoundWagers(direct,betMemory,handPresence,lastResult?.street_candidate);
  const summary=observationSummary(lastResult,locks,displayMemory,now,fresh,!!numeric,actionEvidence);
  const r=summary.range,opponents=r.min===r.max?String(r.min):r.min+'–'+r.max;
  const pot=summary.pot?summary.pot.value.toLocaleString('en-CA')+' ('+summary.pot.source+')':'unknown';
  const turn=lastResult?.table_observation?.turn_candidate;
  const displayedTurn=turn??turnMemory?.seat??displayMemory?.fields?.turn?.value;
  if(fresh&&heroCardPresence(lastResult)==='absent'){show(handPresence?.phase==='ended'?'Hand ended · awaiting next deal':'Hero cards temporarily unavailable','Previous hand observations retained.');$('optional-model-result').textContent='';return;}
  const wager=summary.visibleWagers;
  const wagerText=wager?(wager.approximate?'≈':'')+wager.value.toLocaleString('en-CA')+' ('+wager.count+'/5 seats)':'unavailable';
  const primary=summary.pot?'Pot '+pot:wager?'Visible wagers '+wagerText:'Pot label unavailable';
  const extra=summary.pot?' · Visible wagers '+wagerText:wager?' · Collected pot label unavailable':'';
  show(fresh&&turn&&turn!=='hero'?'NOT YOUR TURN':'NO SUGGESTION','Opponents '+opponents+' · '+primary+' · Stacks '+summary.stackCount+'/5 · Wagers '+summary.betCount+'/5 · '+(fresh&&turn?'Turn cue: '+SEATS[turn]:displayedTurn?'Last turn: '+SEATS[displayedTurn]:'No unique turn cue')+extra);
  const prompt=fresh&&lastResult?.table_observation?.hero_call_prompt?.candidate;
  const currentCards=fresh?currentDeck(now):null;
  const scenario=reading?.stable&&currentCards&&scenarioResults?.cardKey===currentCards.key&&scenarioResults.key===requestedKey?scenarioResults:null;
  const label=$('conditional-model-result');
  const stack=numeric?.seats?.hero?.stack;
  const exactStack=stack&&!stack.approximate&&Number.isSafeInteger(stack.value)&&stack.value>=0?stack.value:null;
  if(fresh&&heroCardPresence(lastResult)==='visible'&&(exactStack===0||heroAllIn?.confirmed)){
   show('ALL-IN','No further action required');
   label.textContent='Tracking the remainder of the hand; no further betting action.';
   return;
  }
  if(fresh&&turn==='hero'&&heroCardPresence(lastResult)==='visible'){
   const context='Opponents '+opponents+' · '+primary;
   show('NO SUGGESTION','Your turn · awaiting model inputs');
   if(prompt?.value===0&&!prompt.approximate){
    show('NO SUGGESTION','Check available (cost 0)');
    label.textContent='Explicit CHECK or RAISE prompt detected.';
   }
   const price=numeric?observedCallPrice(numeric.seats,prompt,r.excluded):null;
   const rounded=numeric&&(!price||price.reason)?roundedCallObservation(numeric.seats,prompt):null;
   const observedNumeric=withRetainedRoundWagers(fresh&&lastResult?.table_observation,betMemory,handPresence,lastResult?.street_candidate);
   const observed=displayCallObservation(observedNumeric?.seats,prompt,{sameStreet:betMemory.street===lastResult?.street_candidate&&!betMemory.boundary&&!betMemory.uncertain,trackedHero:betMemory.seats.hero});
   const fallback=(!price||price.reason)&&!rounded?observed:null;
   show('NO SUGGESTION',fallback?.upperObserved?'Observed wager '+fallback.value.toLocaleString('en-CA')+' · your bet unknown':simplePriceDetail(price,rounded||fallback,exactStack));
   if(price&&!price.reason)label.textContent=(price.partial?'At least ':'Call price: ')+price.value.toLocaleString('en-CA')+' · '+price.source;
   else if(rounded)label.textContent='Call price ≈'+rounded.value.toLocaleString('en-CA')+' · '+rounded.source;
   else if(fallback)label.textContent=fallback.source+' · '+(fallback.upperObserved?'observed wager ':'observed call price ≈')+fallback.value.toLocaleString('en-CA');
   if(scenario&&numeric){
    const args={street:currentCards.street??lastResult.street_candidate,pot:observedPotAccounting(numeric.pot,numeric.seats,$('practice-pot-convention').value),prompt,seats:numeric.seats,equities:scenario.equities,excluded:r.excluded};
    const exactModel=practicePanelModel(args);
    const model=exactModel.reason?roundedPracticeScenario(args)||exactModel:exactModel;
    if(!model.reason){
     const recommendation=practiceHeadline(model);
     const raise=model.estimated?null:conditionalRaiseComparison({model,counts:scenario.counts,equities:scenario.equities,stack:numeric.seats?.hero?.stack?.approximate?null:numeric.seats?.hero?.stack?.value,raiseVisible:!!prompt&&/\bOR\s+RAISE\b/i.test(lastResult?.table_observation?.hero_call_prompt?.raw||'')});
     const hero=numeric.seats?.hero;
     const street=currentCards.street??lastResult.street_candidate;
     const configured=Number($('practice-big-blind').value);
     const bb=Number.isSafeInteger(configured)&&configured>0?configured:blindEvidence?.confirmed?blindEvidence.value:null;
     const sameStreet=betMemory.street===street&&!betMemory.boundary&&!betMemory.uncertain;
     const trackedHero=betMemory.seats.hero;
     const zeroEvidence=sameStreet&&prompt?.value===0&&!prompt.approximate&&(!trackedHero.observed||trackedHero.value===0)&&!trackedHero.pending&&!hero?.bet_reader_conflict;
     const sizing=raise?.action?practiceRaiseSizing({street,hero,call:model.call,bigBlind:bb,raiseVisible:true,zeroWagerEvidence:zeroEvidence}):null;
     const bounds=sizing?.bounds;
     const headline=sizedPracticeHeadline(model,raise,sizing).text;
     show(simplePracticeAction(headline),model.estimated||model.partial||model.pricePartial||currentCards.retained?.length?'Conditional estimate · incomplete or retained inputs':'Conditional practice model');
     label.textContent='Practice model · '+recommendation.policy+' · '+model.source+(model.partial?' ('+model.wagerCount+'/5 read; missing wagers can change result)':'')+' · '+model.priceSource+(model.estimated?' (rounded point estimate, not an exact price or legal raise size)':model.pricePartial?' (retained or incomplete wagers; price may change)':'')+' · assumes eligible pot, no side pots and random opponent hands.'+(currentCards.retained?.length?' Retained card evidence.':'')+(raise?' Raise scenario: '+raise.assumption+'. '+(raise.action?(bounds?'Add '+bounds.additional.toLocaleString('en-CA')+' chips; conservative full-raise bound, not exact room minimum.'+(sizing.assumedZero?' Assumes zero commitment from the absent chip label and check prompt.':''):'Raise size not established: '+(sizing?.reason||'missing evidence')+'. Showing the baseline instead.'):'Raise not favored across all scenarios.'):'');
    }else label.textContent+=(label.textContent?' · ':'')+model.reason;
   }else{
    const blocker=!currentCards?'Card recognition incomplete':!reading?.stable?'Waiting for repeated card reading':simulationState==='failed'?'Equity calculation failed':simulationState==='no opponents'?'No opponent scenario available':!scenario?'Calculating current card equity':!numeric?'Numeric snapshot unavailable ('+(lastOcrState?.state||'waiting')+')':'Model inputs unavailable';
    label.textContent+=(label.textContent?' · ':'')+blocker;
    if(!currentCards||!reading?.stable)show('NO SUGGESTION',blocker+(prompt?.value===0&&!prompt.approximate?' · Check available (cost 0)':''));
   }
  }
  // The optional explicitly configured practice model never hides the
  // independent observation summary or asks for missing data.
  const action=$('optional-model-result');
  action.textContent='';
  if(!$('practice-action-confirm').checked||!fresh||turn!=='hero')return;
  const a=resolveManual(autoValues(),locks),exact=new Set(Object.keys(locks));
  if(observationAge(lastOcrAt,now,1000).fresh){
   if(lastTable?.pot&&!lastTable.pot.approximate)exact.add('pot');
   if(lastTable?.seats?.hero?.stack&&!lastTable.seats.hero.stack.approximate)exact.add('hero.stack');
  }
  if(betMemory.street===a.street&&!betMemory.boundary&&!betMemory.uncertain){
   for(const id of Object.keys(SEATS)){const b=betMemory.seats[id];if(b.observed&&!b.approximate&&!b.warning&&observationAge(b.lastSeen,now,1000).fresh)exact.add(id+'.bet');}
  }
  const input=decisionInputs(a,exact,{confirmed:true,opponents:practiceOpponentCount($('live-opponents').value,locks).count});
  const rec=decisionFromEquity(input,equityResult);
  if(rec.action){action.textContent='Optional practice model: '+rec.action+' · equity '+(rec.equity*100).toFixed(1)+'% · pot odds '+(rec.potOdds*100).toFixed(1)+'%';show(simplePracticeAction(rec.action),'Conditional practice model');}
 }
 function autoValues(){
  const now=performance.now(),result=observationAge(lastFrame,now,1000).fresh?lastResult:null,obs=result?.table_observation,age=observationAge(lastOcrAt,now,1000),num=age.fresh?lastTable:null;
  const a={street:result?.street_candidate??(result?cardMemory?.displayStreet:undefined),pot:num?.pot?.value,dealer:obs?.dealer?.candidate??undefined,turn:obs?.turn_candidate??turnMemory?.seat??undefined};
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
  const now=performance.now(),a=autoValues(),history=displayEvidenceValues(displayMemory,now),effective=resolveManual({...a,...history.values},locks),age=observationAge(lastOcrAt,now,1000),direct=directNumericSnapshot(lastResult,lastOcrState?.state,lastFrame,now);
  // A visible wager is useful even before hand/round confirmation. It is
  // display-only; never substitute it into the accepted hand ledger.
  for(const id of Object.keys(SEATS)){
   const raw=direct?.seats?.[id]?.bet;
   if(raw&&Number.isSafeInteger(raw.value)&&raw.value>=0&&!isLocked(locks,id+'.bet')&&effective[id+'.bet']===undefined){
    effective[id+'.bet']=raw.value;
    history.details[id+'.bet']={state:'visible candidate',approximate:!!raw.approximate,ageMs:now-lastFrame};
   }
  }
  // Zero is the display baseline for an unobserved current round, not
  // an exact recognized bet or a substitute for a missing numeric input.
  if(betMemory.street&&handPresence?.phase==='active'){
   for(const id of Object.keys(SEATS)){
    const key=id+'.bet';
    if(effective[key]===undefined&&!isLocked(locks,key)){
     const held=betMemory.seats[id];
     effective[key]=held.value;
     history.details[key]={state:held.observed?'last observed':'initial baseline',approximate:!!held.approximate,ageMs:held.lastSeen===null?null:now-held.lastSeen};
    }
   }
  }
  for(const map of [editors,inlineEditors,popupEditors])for(const [key,e] of map){
   const locked=isLocked(locks,key),v=effective[key];
   e.box.classList.toggle('manual-locked',locked);e.auto.disabled=!locked;e.lock.textContent=locked?'Update':'Lock';
   if(document.activeElement!==e.input&&!e.dirty)e.input.value=inputValue(v,e.field);
   const evidence=locked?null:history.details[key],label=evidence?.state||'Auto';
   e.note.textContent=(locked?'LOCKED · ':label+' · ')+displayValue(key,v)+(evidence?.approximate?' (approx.)':'');
   e.input.title=(locked?'Locked':label)+' · '+displayValue(key,v)+(evidence?.ageMs!==null&&evidence?.ageMs!==undefined?' · last read '+(evidence.ageMs/1000).toFixed(1)+' s ago':'')+(evidence?.pending?' · conflicting candidate '+evidence.pending.value:'');
   e.box.classList.toggle('observation-retained',!locked&&!!evidence&&evidence.state!=='repeated');
  }
  const coverage=snapshotCoverage(lastResult,locks,observationAge(lastFrame,now,1000).fresh,!!direct);
  $('snapshot-coverage').textContent='Field availability: '+(coverage.total-coverage.counts.unknown)+' / '+coverage.total+' · '+coverage.counts.manual+' manual · '+coverage.counts.candidate+' candidates · '+coverage.counts.approximate+' approximate · '+coverage.counts.unknown+' unknown. Not an accuracy score.';
  $('snapshot-reconciliation').textContent=!observationAge(lastFrame,now,1000).fresh?'Stack/pot reconciliation: no fresh snapshot':conservation?.status==='unavailable'||!conservation?'Stack/pot reconciliation: '+(conservation?.reason||'waiting for adjacent snapshots'):'Stack/pot reconciliation: '+conservation.status+' · '+Object.entries(conservation.seats).filter(([,s])=>s.status==='conflict'||s.status==='hypothesis').map(([id,s])=>SEATS[id]+': '+s.status+' '+s.implied).join(' · ');
  const show=key=>displayValue(key,effective[key])+(isLocked(locks,key)?' [locked]':history.details[key]&&history.details[key].state!=='repeated'?' ['+history.details[key].state+']':'');
  const range=observedOpponentRange(observationAge(lastFrame,now,1000).fresh?lastResult:null,locks,actionEvidence);
  $('observed-opponents').textContent='Observed opponents: '+(range.min===range.max?range.min:range.min+'–'+range.max)+' · '+range.unknown.length+' unresolved seats. Blue-grey profiles and empty chairs are excluded unless other evidence conflicts; blue default avatars remain unresolved without card or action evidence.';
  $('live-dealer').textContent=show('dealer');$('live-turn').textContent=show('turn');$('live-pot').textContent=show('pot');
  $('live-stacks').textContent=Object.keys(SEATS).map(id=>SEATS[id]+': '+show(id+'.stack')).join(' · ');
  const heroBand=lastResult?.seat_evidence?.seats?.hero?.bar;
  $('hero-ring-status').textContent='Hero light: '+(!observationAge(lastFrame,now,1000).fresh?'no fresh image':heroBand?.multicolor_band_candidate?'colored ring detected':heroBand?'not detected':'unknown')+(heroBand?' · green '+heroBand.bright_pixels.green+' px · warm '+(heroBand.bright_pixels.amber+heroBand.bright_pixels.red)+' px':'')+' · turn source '+(lastResult?.table_observation?.turn_source||'none')+' · hand '+(handPresence?.phase||'waiting');
  $('live-bet-state').textContent=betMemory.status;$('live-ocr-age').textContent=lastOcrState?.state==='failed'||lastOcrState?.state==='unavailable'?'OCR '+lastOcrState.state+': '+(lastOcrState.detail||'No reading'):direct?'Latest capture '+((now-lastFrame)/1000).toFixed(1)+' s ago'+(!age.fresh?' · awaiting round confirmation':''):'No fresh OCR sample';
  const body=$('live-table-body');body.replaceChildren();
  for(const [id,label] of Object.entries(SEATS)){
   const n=direct?.seats?.[id]||{},row=document.createElement('tr'),held=betMemory.seats[id]?.observed?betMemory.seats[id]:null,total=handContributionDisplay(betMemory,id,handPresence);if(effective.turn===id)row.className='active-observation';
   const values=[label,effective.dealer===id?'D':'—',effective.turn===id?'Turn cue':'—',show(id+'.stack'),n.stack_reader_conflict?'Conflict: font '+(n.stack_font_candidate?.display??'?')+' / OCR '+(n.stack_raw||'?'):n.stack?.display??'?',n.bet_reader_conflict?'Conflict: font '+(n.bet_font_candidate?.display??'?')+' / OCR '+(n.bet_raw||'?'):n.bet?.display??'?',isLocked(locks,id+'.bet')?show(id+'.bet'):held?trackedBetLabel(held)+(a[id+'.bet']===undefined||betMemory.uncertain?' (last seen)':''):callHypotheses[id]?'≈'+callHypotheses[id].value.toLocaleString('en-CA')+' (call hypothesis)':betMemory.street?'0 (initial, unobserved)':'? (unobserved)',total?(total.approximate?'≈':'')+total.value.toLocaleString('en-CA')+' ('+total.observedRounds+'/'+total.rounds+' rounds observed)':'?',(n.status_candidate||actionEvidence?.seats?.[id]?.action||show(id+'.status'))+(n.status_candidate?'':actionEvidence?.seats?.[id]?' [last observed]':''),show(id+'.cards'),show(id+'.participation')+' · profile '+(observationAge(lastFrame,now,1000).fresh?lastResult?.seat_evidence?.seats?.[id]?.avatar_appearance?.candidate??'unknown':'unknown'),[n.stack_raw,n.bet_raw,n.status_raw,n.status_alternate_raw,n.status_reader_conflict?'Action readers disagree':''].filter(Boolean).join(' / ')||'—'];
   values.forEach((value,i)=>{const td=document.createElement('td');td.textContent=value;if(i===6)td.title=isLocked(locks,id+'.bet')?'Manual lock':betMemory.seats[id].warning||betMemory.seats[id].source;row.append(td);});body.append(row);
  }
  const cardLabel=key=>{const v=effective[key];return (v===null?'·':v??'?')+(isLocked(locks,key)?' [L]':history.details[key]&&history.details[key].state!=='repeated'?'*':'');};
  $('manual-effective-cards').textContent=CARD_KEYS.slice(0,2).map(cardLabel).join(' ')+' | '+CARD_KEYS.slice(2).map(cardLabel).join(' ');
  $('live-cards').textContent=$('manual-effective-cards').textContent;
  $('live-street').textContent=show('street');
  for(const [id,n] of seatNodes){const [x,y]=overlayPosition(SEAT_ANCHORS[id],lastResult?.capture_crop);n.tile.style.left=x+'%';n.tile.style.top=y+'%';n.tile.classList.toggle('screen-seat-active',effective.turn===id);const retained=betMemory.seats[id]?.observed?betMemory.seats[id]:null,total=handContributionDisplay(betMemory,id,handPresence);n.note.textContent=(effective.dealer===id?'D · ':'')+(effective.turn===id?(observationAge(lastFrame,now,1000).fresh&&lastResult?.table_observation?.turn_candidate===id?'TURN · ':'LAST TURN · '):'')+(lastResult?.table_observation?.seats?.[id]?.status_candidate|| (actionEvidence?.seats?.[id]?.action?actionEvidence.seats[id].action+' (last)':'')||displayValue(id+'.status',effective[id+'.status']))+(retained&&(a[id+'.bet']===undefined||betMemory.uncertain)?' · last B '+trackedBetLabel(retained):'');const raw=direct?.seats?.[id]?.bet;const conflict=direct?.seats?.[id]?.bet_reader_conflict;if(conflict)n.note.textContent+=' · wager readers disagree';else if(raw&&(!retained||raw.value!==retained.value))n.note.textContent+=' · visible B '+raw.display;else if(callHypotheses[id]&&!raw)n.note.textContent+=' · inferred call ~'+callHypotheses[id].value.toLocaleString('en-CA');if(id==='hero'&&heroWagerEvidence)n.note.title='Last observed wager increase: +'+heroWagerEvidence.added.toLocaleString('en-CA')+' · '+heroWagerEvidence.street;else n.note.title='';n.contributionValue.value=total?(total.approximate?'≈':'')+total.value.toLocaleString('en-CA'):'0';
   n.contributionValue.title=total?.initialized?'Initial zero; unobserved wagers may be missing':'Cumulative observed hand contribution; incomplete if any wagers were missed';
   n.total.textContent='Round wager: '+(retained?trackedBetLabel(retained):raw?raw.display+' (candidate)':'0 (unobserved)')+(id==='hero'&&heroWagerEvidence?.street===betMemory.street?' · Last increase +'+heroWagerEvidence.added.toLocaleString('en-CA'):'');}
  paintDecision();
 }
 function render(result,ocr,ocrStatus,capturedAt){
  if(capturedAt<resetAt||(lastFrame!==null&&capturedAt<=lastFrame))return;
  const now=performance.now();
  if(!observationAge(capturedAt,now,1000).fresh){paint();return;}
  const priorFrame=lastResult,priorAt=lastFrame;
  lastResult=result;
  lastTimings=result.timings_ms||null;
  lastOcrState=$('live-ocr').checked?ocrStatus:{state:'disabled'};
  ocrBackend=ocrStatus?.backend||ocrBackend;
  const prior=betMemory,sampled=ocr&&ocrStatus?.state==='sampled'&&$('live-ocr').checked;
  const currentSnapshot=sampled?{at:capturedAt,result}:null;
  conservation=reconcileSnapshots(previousSnapshot,currentSnapshot,{potIncludesBets:$('practice-action-confirm').checked});
  previousSnapshot=currentSnapshot;
  handPresence=updateHandPresence(handPresence,result,capturedAt);
  heroAllIn=updateHeroAllIn(heroAllIn,result,handPresence,capturedAt,sampled);
  blindEvidence=observePracticeBlind(blindEvidence,result,handPresence,capturedAt);
  if(handPresence?.started){callHypotheses={};displayMemory=null;cardMemory=null;reading=null;clearEquity();}
  betMemory=updateBetMemory(betMemory,result,{capturedAt,now,ocr:sampled,hand:handPresence});
  heroWagerEvidence=updateHeroWagerEvidence(heroWagerEvidence,prior,betMemory,handPresence,capturedAt);
  if(prior.generation!==betMemory.generation||handPresence?.phase!=='active')callHypotheses={};
  if(sampled&&handPresence?.phase==='active'){
   const h=observedCallHypothesis(priorFrame,result,priorAt,capturedAt);
   if(h)callHypotheses[h.seat]=h;
   for(const id of Object.keys(callHypotheses))if(result.table_observation?.seats?.[id]?.bet||['Raise','Fold','All-in'].includes(result.table_observation?.seats?.[id]?.status_candidate))delete callHypotheses[id];
  }
  turnMemory=updateTurnMemory(turnMemory,result,handPresence,result.street_candidate,capturedAt);
  actionEvidence=updateActionEvidence(actionEvidence,result,handPresence,betMemory.street,capturedAt);
  displayMemory=updateDisplayEvidence(displayMemory,result,betMemory,prior,{at:capturedAt,sampled,hand:handPresence});
  const numeric=sampled?currentNumericSample(null,result,betMemory,prior,{capturedAt,now,sampled}):null;
  lastTable=numeric?.table??null;lastOcrAt=numeric?.at??null;
  cardMemory=updateCardMemory(cardMemory,result,capturedAt);lastFrame=capturedAt;refreshCandidate(true);if(now-lastPaintAt>=125){lastPaintAt=now;paint();}
  $('live-overlay').hidden=false;
 }
 function reportQueue(q){const r=q.report(performance.now()),age=r.lastSnapshotAgeMs;$('frame-telemetry').textContent='Snapshots '+r.processed+'/'+r.captured+' · deliberately sampled out '+r.intentionalSkips+' · source gaps '+r.sourceMissed+' · presented '+(r.sourceFps===null?'—':r.sourceFps.toFixed(1))+' FPS · callbacks '+(r.callbackFps===null?'—':r.callbackFps.toFixed(1))+' FPS · snapshots '+r.processingFps.toFixed(1)+'/s · snapshot age '+(age===null?'—':(age/1000).toFixed(2)+' s')+' · in flight '+(r.oldestAgeMs/1000).toFixed(2)+' s · OCR '+ocrBackend+(lastTimings?' · recognition '+lastTimings.total.toFixed(1)+' ms':'');if(age===null)status('Acquiring first table snapshot.');else if(age>1000)status('Snapshot stale: full table refresh exceeded one second.');else status('Current-state recognition running · snapshot age '+(age/1000).toFixed(2)+' s · automatic values remain candidates.');}
 function failQueue(q,error){reportQueue(q);autoPaused=true;stop({preserve:true});status('Frame coverage failed: '+String(error.message||error)+'. Restart after resolving the bottleneck.');}
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
 $('practice-consent').onchange=()=>{try{localStorage.setItem(preferenceKey,$('practice-consent').checked?'on':'off');}catch{}autoPaused=false;if(!$('practice-consent').checked)stop();refresh();};
 async function startRecognition(){if(active)return;if(!canRun()||!$('practice-consent').checked)return;if(!video.requestVideoFrameCallback){status('Frame accounting requires a browser with video frame callbacks.');return;}stop({preserve:true});active=true;epoch++;session=crypto.randomUUID();$('live-start').disabled=true;$('live-stop').disabled=false;status('Preparing Python recognizer before capture…');$('frame-telemetry').textContent='Preparing backend. Frame counting starts when ready.';const current=epoch;controller=new AbortController();try{const response=await fetch('/api/practice-ready',{method:'POST',headers:{'X-Practice-Consent':'yes','X-Frame-Session':session},signal:controller.signal});const data=await response.json();if(!active||epoch!==current)return;if(!response.ok||!data.ready)throw Error(data.error||'Backend not ready');if($('live-ocr').checked&&!data.ocr)throw Error(data.ocr_error||'OCR unavailable');controller=null;ocrBackend=data.ocr_backend||'unknown';status('Backend ready. Tracking source frames.');frameQueue=new CurrentStateQueue(100);const q=frameQueue;decisionTimer=setInterval(()=>{paint();if(frameQueue===q)reportQueue(q);},125);captureNext(current,q);}catch(e){if(active&&epoch===current){autoPaused=true;stop({preserve:true});status('Recognition startup failed: '+e.message);}}}
 $('live-start').onclick=()=>{autoPaused=false;void startRecognition();};
 $('live-stop').onclick=()=>{autoPaused=true;stop({preserve:true});};
 $('live-reset-bets').onclick=()=>{betMemory={...createBetMemory(),last:performance.now()};if(displayMemory)for(const key of Object.keys(displayMemory.fields))if(key.endsWith('.bet'))delete displayMemory.fields[key];paint();};
 $('manual-new-hand').onclick=()=>{if(!confirm('Clear all manual locks and automatic observations for a new hand?'))return;closePopup();locks={};resetAt=performance.now();betMemory=createBetMemory();clearAuto();for(const map of [editors,inlineEditors])for(const e of map.values()){e.dirty=false;e.input.value='';e.input.setCustomValidity('');}save();paint();};
 $('live-opponents').onchange=()=>{clearEquity();if(active&&reading?.stable&&observationAge(lastFrame,performance.now(),1000).fresh)evaluate(reading.stable);paintDecision();};
 $('live-ocr').onchange=()=>{lastOcrState=null;previousSnapshot=null;conservation=null;lastOcrAt=null;lastTable=null;betMemory=interruptBetMemory(betMemory);paint();};
 save();paint();refresh();
 return {stop,pause:()=>stop({preserve:true}),refresh,reset:()=>{if(active){stop({preserve:true});refresh();status('Source geometry changed. Hand observations retained.');}}};
}
