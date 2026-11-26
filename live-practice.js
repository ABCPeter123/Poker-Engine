import {parseCards} from './quick-input.js';
// Null is an explicitly empty slot. Missing, sparse and malformed slots are not empty.
export function validSlots(slots,length){
 return Array.isArray(slots)&&slots.length===length&&Array.from({length},(_,i)=>{
  if(!Object.hasOwn(slots,i))return false;
  const s=slots[i];
  return s===null||!!(s&&typeof s==='object'&&!Array.isArray(s)&&Object.hasOwn(s,'candidate')&&(s.candidate===null||typeof s.candidate==='string'&&/^[2-9TJQKA][cdhs]$/.test(s.candidate)));
 }).every(Boolean);
}
export function freshBetValue(state,seat,street,now){
 const b=state?.seats?.[seat];
 return b?.observed&&state.street===street&&!state.boundary&&!state.uncertain&&observationAge(b.lastSeen,now,5000).fresh?b.value:undefined;
}
export function currentNumericSample(previous,result,state,priorState,{capturedAt,now,sampled=false}={}){
 if(!observationAge(capturedAt,now,5000).fresh)return null;
 // A street or hand transition invalidates all earlier OCR, even if recent.
 if(!state?.street||state.boundary||state.uncertain||state.street!==result?.street_candidate)return null;
 const changed=state.generation!==priorState?.generation;
 if(sampled)return {at:capturedAt,table:{...result.table_observation,pot:result.number_candidates?.pot?.candidate}};
 return changed?null:previous&&observationAge(previous.at,now,5000).fresh?previous:null;
}

export function candidateCards(result){
 const holes=result?.hole_slots,board=result?.board_slots;
 if(!validSlots(holes,2)||!validSlots(board,5)||!result?.street_candidate||result.quality?.duplicate_card_candidates||result.quality?.noncontiguous_board||result.quality?.unrecognized_visible_cards)return null;
 const h=holes.map(x=>x?.candidate),b=board.filter(Boolean).map(x=>x?.candidate);
 if(h.some(x=>!x)||b.some(x=>!x)||![0,3,4,5].includes(b.length))return null;
 if(board.slice(0,b.length).some(x=>!x)||board.slice(b.length).some(Boolean))return null;
 if(({0:'Preflop',3:'Flop',4:'Turn',5:'River'})[b.length]!==result.street_candidate)return null;
 try{const hole=parseCards(h.join(' ')),cards=b.length?parseCards(b.join(' ')):[];if(hole.length!==2||new Set([...hole,...cards]).size!==hole.length+cards.length)return null;return {hole,board:cards,labels:{hole:h,board:b},key:JSON.stringify([hole,cards])};}catch{return null;}
}
export function stableReading(prev,candidate,now){
 if(!Number.isFinite(now)||now<0)return {key:null,count:0,stable:null,last:null};
 if(prev&&Number.isFinite(prev.last)&&now<=prev.last)return prev;
 if(!candidate)return {key:null,count:0,stable:null,last:now};
 const count=prev?.key===candidate.key&&now-prev.last<=6000?prev.count+1:1;
 return {key:candidate.key,count,stable:count>=2?candidate:null,last:now};
}
export function practiceInput(candidate,opponents){
 if(!candidate||!Number.isInteger(opponents)||opponents<1||opponents>8)throw Error('Stable cards and known opponent count required.');
 return {hole:candidate.hole,board:candidate.board,opponents,styles:Array(opponents).fill('random'),iterations:5000,seed:42};
}

export const CARD_MEMORY_MS=5000;
const validCard=x=>typeof x==='string'&&/^[2-9TJQKA][cdhs]$/i.test(x)?x[0].toUpperCase()+x[1].toLowerCase():null;
const freshSlot=()=>({value:null,count:0,confirmed:false,lastSeen:null,misses:0});
// Display-only memory: only repeated raw readings can seed it. A carried
// card never becomes a fresh reading or refreshes its own expiration.
export function updateCardMemory(previous,result,now){
 if(!Number.isFinite(now)||now<0)return null;
 if(previous&&now<=previous.last)return previous;
 const groups=[result?.hole_slots,result?.board_slots];
 if(!validSlots(groups[0],2)||!validSlots(groups[1],5))return null;
 const raw=groups.flat(),values=raw.map(x=>validCard(x?.candidate));
 const observed=values.filter(Boolean);
 const duplicate=new Set(observed).size!==observed.length||!!result.quality?.duplicate_card_candidates;
 let old=previous&&now>=previous.last&&now-previous.last<=CARD_MEMORY_MS?previous:null;
 const boardVisible=groups[1].some(Boolean);
 const holeVisible=groups[0].some(Boolean);
 // Clear on a board reset, a conflicting recognized identity or invalid deck.
 // Even one contradictory card can indicate a new hand or alignment change.
 if(old&&((old.boardVisible&&!boardVisible)||duplicate||values.some((v,i)=>v&&old.slots[i]?.confirmed&&old.slots[i].value!==v)))old=null;
 const slots=values.map((v,i)=>{
  const prior=old?.slots[i]||freshSlot();
  const groupVisible=i<2?holeVisible:boardVisible;
  if(duplicate||!groupVisible)return freshSlot();
  if(v){
   const same=prior.value===v&&now-prior.lastSeen<=CARD_MEMORY_MS;
   const count=same?prior.count+1:1;
   return {value:v,count,confirmed:count>=2,lastSeen:now,misses:0};
  }
  if(prior.confirmed&&now-prior.lastSeen<=CARD_MEMORY_MS&&prior.misses<3)return {...prior,misses:prior.misses+1};
  return freshSlot();
 });
 const carried=[];
 // Only recover an isolated loss with a matching directly read peer in the
 // same card group. Do not resurrect both hero cards or an entire board.
 for(const [start,end] of [[0,2],[2,7]]){
  const missing=[];
  for(let i=start;i<end;i++)if(!values[i]&&slots[i].confirmed)missing.push(i);
  const anchor=values.slice(start,end).some((v,j)=>v&&old?.slots[start+j]?.confirmed&&old.slots[start+j].value===v);
  if(!duplicate&&anchor&&missing.length===1){
   const i=missing[0],v=slots[i].value;
   if(!observed.includes(v)&&!carried.some(j=>slots[j].value===v))carried.push(i);
  }
 }
 const display=raw.map((x,i)=>carried.includes(i)?{candidate:slots[i].value,cached:true,ageMs:now-slots[i].lastSeen}:x);
 const board=display.slice(2),count=board.filter(Boolean).length;
 const street=board.slice(0,count).every(Boolean)&&board.slice(count).every(x=>!x)?({0:'Preflop',3:'Flop',4:'Turn',5:'River'})[count]||null:null;
 return {slots,last:now,boardVisible,holeVisible,carried,displayHole:display.slice(0,2),displayBoard:board,displayStreet:street};
}

// The capture clock, not response arrival, determines the age of an observation.
export function observationAge(capturedAt,now,maxAge=10000){
 if(!Number.isFinite(capturedAt)||!Number.isFinite(now)||capturedAt<0||now<capturedAt)return {ageMs:null,fresh:false};
 const ageMs=now-capturedAt;return {ageMs,fresh:ageMs<=maxAge};
}


export const BET_SEATS=Object.freeze(['hero','left','upper_left','upper_right','right']);
const streets=['Preflop','Flop','Turn','River'];
const blank=()=>({value:0,observed:false,approximate:false,pending:null,warning:null,lastSeen:null,stack:null,source:'initial'});
const seats=()=>Object.fromEntries(BET_SEATS.map(s=>[s,blank()]));
export function createBetMemory(){return {street:null,hole:null,dealer:null,boundary:null,last:null,generation:0,uncertain:true,closedRounds:[],seats:seats(),status:'Waiting for round confirmation'};}
function streetOf(r){
 const b=r?.board_slots;
 if(!validSlots(b,5)||r.quality?.duplicate_card_candidates||r.quality?.noncontiguous_board)return null;
 const n=b.filter(Boolean).length,s=({0:'Preflop',3:'Flop',4:'Turn',5:'River'})[n];
 return s===r.street_candidate&&b.slice(0,n).every(Boolean)&&!b.slice(n).some(Boolean)?s:null;
}
function holeOf(r){
 const h=r?.hole_slots;
 if(!validSlots(h,2))return null;
 const a=h.map(c=>c?.candidate);
 return a.every(x=>typeof x==='string'&&/^[2-9TJQKA][cdhs]$/.test(x))&&a[0]!==a[1]?a.sort().join(' '):null;
}
const fresh=(t,now)=>Number.isFinite(t)&&Number.isFinite(now)&&t>=0&&now>=t&&now-t<=5000;
function amount(c,confidence,minimum=75){
 return c&&Number.isSafeInteger(c.value)&&c.value>=0&&Number.isFinite(confidence)&&confidence>=minimum?c:null;
}
function accept(e,b,stack,t,source){
 return {...e,value:b.value,observed:true,approximate:!!b.approximate,stack:stack&&!stack.approximate?stack.value:null,lastSeen:t,pending:null,warning:source==='correction'?'Corrected from repeated lower readings':null,source};
}
// A missing rank is not a missing card. End the observed hero hand only
// after sustained explicit absence of both physical slots. Keep its ledger
// until a subsequent visible hand is established.
export function updateHandPresence(previous,result,at){
 const old=previous||{phase:'waiting',last:null,absentSince:null,absentCount:0,pair:null,street:null,started:false};
 if(!Number.isFinite(at)||at<0||(old.last!==null&&at<=old.last))return old;
 let s={...old,last:at,started:false};
 const slots=result?.hole_slots;
 if(!validSlots(slots,2))return {...s,absentSince:null,absentCount:0};
 const visible=slots.some(Boolean),pair=holeOf(result),street=streetOf(result);
 if(visible){
  const newHand=old.phase==='waiting'||(old.phase==='ended'&&(
    street==='Preflop'||(pair&&old.pair&&pair!==old.pair)));
  // A relocated or temporarily hidden showdown pair may return. That is
  // not evidence of a new deal unless a fresh preflop or changed pair appears.
  return {...s,phase:'active',started:newHand,absentSince:null,absentCount:0,
    pair:newHand?pair:old.pair||pair,street:street||old.street};
 }
 if(old.phase!=='active')return s;
 const continued=old.absentSince!==null&&at-old.last<=1500;
 const absentSince=continued?old.absentSince:at,absentCount=continued?old.absentCount+1:1;
 return {...s,absentSince,absentCount,phase:absentCount>=3&&at-absentSince>=1000?'ended':'active'};
}

export function updateBetMemory(previous,r,{capturedAt:t,now,ocr=false,hand=null}={}){
 let old=previous||createBetMemory();
 if(!fresh(t,now)||(old.last!==null&&t<=old.last))return old;
 if(hand&&hand.phase!=='active')return {...old,last:t,uncertain:true,status:hand.phase==='ended'?'Hero cards absent; previous hand contributions retained':'Waiting for visible hero cards'};
 if(hand?.started)old={...createBetMemory(),generation:old.generation+1};
 let state={...old,last:t,seats:Object.fromEntries(BET_SEATS.map(s=>[s,{...old.seats[s]}]))};
 const street=streetOf(r),hole=holeOf(r),d=r?.table_observation?.dealer?.candidate,dealer=BET_SEATS.includes(d)?d:null;
 if(!street||(state.street&&(street!=='Preflop'||hand)&&streets.indexOf(street)<streets.indexOf(state.street))){
  state.boundary=null;state.uncertain=true;state.status='Round uncertain; holding prior values';
  for(const e of Object.values(state.seats))e.pending=null;
  return state;
 }
 const newHole=!hand&&street==='Preflop'&&state.street==='Preflop'&&hole&&state.hole&&hole!==state.hole;
 const newDealer=!hand&&street==='Preflop'&&state.street==='Preflop'&&dealer&&state.dealer&&dealer!==state.dealer;
 if(street!==state.street||newHole||newDealer){
  const key=[street,newHole?hole:null,newDealer?dealer:null].join('|'),p=state.boundary;
  state.uncertain=true;
  state.boundary={key,count:p?.key===key&&t-p.last<=6000?p.count+1:1,last:t};
  if(state.boundary.count<2){state.status='Checking round change';for(const e of Object.values(state.seats))e.pending=null;return state;}
  const forward=state.street&&streets.indexOf(street)>streets.indexOf(state.street)&&!newHole&&!newDealer;
  const closedRounds=forward?[...(state.closedRounds||[]),{street:state.street,seats:Object.fromEntries(BET_SEATS.map(id=>[id,{...state.seats[id]}]))},...streets.slice(streets.indexOf(state.street)+1,streets.indexOf(street)).map(skipped=>({street:skipped,seats:seats(),skipped:true}))]:[];
  state={...state,street,hole,dealer,boundary:null,generation:state.generation+1,closedRounds,seats:seats()};
 }else{
  state.boundary=null;state.hole=state.hole||hole;state.dealer=state.dealer||dealer;
 }
 state.uncertain=false;
 state.status=state.street+' · tracked candidates';
 if(!ocr)return state;
 for(const id of BET_SEATS){
  const e=state.seats[id],s=r?.table_observation?.seats?.[id],b=amount(s?.bet,s?.bet?.ocr_confidence??s?.bet_confidence);
  const stack=amount(s?.stack,s?.stack?.ocr_confidence??s?.stack_confidence,85);
  if(!b){if(!hand||!e.pending||t-e.pending.last>2000)e.pending=null;e.warning=e.observed?'Missing sample; holding last value':null;continue;}
  const v=b.value;
  if(v===e.value&&e.observed){e.pending=null;e.warning=null;e.lastSeen=t;if(!b.approximate)e.approximate=false;if(stack&&!stack.approximate)e.stack=stack.value;continue;}
  const p=e.pending,approximate=!!b.approximate;
  const count=p?.value===v&&p.approximate===approximate&&t-p.last<=15000?p.count+1:1;
  const sameStack=stack&&!stack.approximate&&p?.stack===stack.value;
  const stackCount=sameStack?p.stackCount+1:stack&&!stack.approximate?1:0;
  e.pending={value:v,approximate,count,last:t,stack:stack&&!stack.approximate?stack.value:null,stackCount};
  // Exact stack/bet conservation supports an increase, but OCR stack values
  // are themselves candidates. Never use them as an absolute hard limit.
  const supported=e.stack!==null&&stackCount>=2&&!approximate&&!e.approximate&&e.stack+e.value===stack.value+v;
  if(v>e.value||!e.observed){
   const large=v>Math.max(1000,e.value*4),need=large&&!supported?3:2;
   e.warning='Provisional '+v+' ('+count+'/'+need+')';
   if(count>=need)state.seats[id]=accept(e,b,stack,t,'ocr');
  }else{
   // A lower observation is not a negative bet. It is a possible correction
   // or refund. Require stronger repeated evidence, never treat absence as zero.
   const need=supported?3:4;
   e.warning='Disputed: lower reading '+v+' ('+count+'/'+need+')';
   if(count>=need&&!approximate)state.seats[id]=accept(e,b,stack,t,'correction');
  }
 }
 return state;
}
export function interruptBetMemory(state){
 const s=state||createBetMemory();
 return {...s,boundary:null,uncertain:true,status:'Capture interrupted; prior bets retained',
  seats:Object.fromEntries(BET_SEATS.map(id=>[id,{...s.seats[id],pending:null,warning:s.seats[id].observed?'Capture interrupted':null}]))};
}
export function correctTrackedBet(state,seat,value,now){
 if(!BET_SEATS.includes(seat)||!Number.isSafeInteger(value)||value<0||!Number.isFinite(now))throw Error('Enter a nonnegative whole chip amount.');
 const s=state||createBetMemory();
 return {...s,last:Math.max(s.last??0,now),seats:{...s.seats,[seat]:{...blank(),value,observed:true,lastSeen:now,source:'manual',warning:'Manually corrected'}}};
}
export function trackedBetLabel(e){
 if(!e?.observed)return '? (unobserved)';
 return (e.approximate?'≈':'')+e.value.toLocaleString('en-CA')+(e.warning?' *':'');
}

// Snapshot coverage is an inventory of available observations, never a claim
// that the OCR readings are correct. A manual value is explicitly distinguished.
export const SNAPSHOT_FIELDS=Object.freeze([
 ...Array.from({length:2},(_,i)=>'hole.'+i),
 ...Array.from({length:5},(_,i)=>'board.'+i),
 'dealer','turn','pot',...BET_SEATS.flatMap(id=>[id+'.stack',id+'.bet'])
]);
export function snapshotCoverage(result,locks={},fresh=false,numericFresh=false){
 const fields={};
 for(const key of SNAPSHOT_FIELDS){
  if(Object.hasOwn(locks,key)){fields[key]='manual';continue;}
  if(!fresh||!result){fields[key]='unknown';continue;}
  if(key.startsWith('hole.')||key.startsWith('board.')){
   const [group,index]=key.split('.'),slots=result[group+'_slots'];
   const length=group==='hole'?2:5;
   fields[key]=validSlots(slots,length)&&!result.quality?.duplicate_card_candidates&&!result.quality?.noncontiguous_board&&(slots[index]===null||validCard(slots[index]?.candidate))?'candidate':'unknown';
   continue;
  }
  if(key==='dealer'||key==='turn'){
   const v=key==='dealer'?result.table_observation?.dealer?.candidate:result.table_observation?.turn_candidate;
   fields[key]=BET_SEATS.includes(v)?'candidate':'unknown';continue;
  }
  const [seat,kind]=key.split('.');
  const c=key==='pot'?result.number_candidates?.pot?.candidate:result.table_observation?.seats?.[seat]?.[kind];
  fields[key]=numericFresh&&c&&Number.isSafeInteger(c.value)&&c.value>=0?(c.approximate?'approximate':'candidate'):'unknown';
 }
 const counts={manual:0,candidate:0,approximate:0,unknown:0};
 for(const s of Object.values(fields))counts[s]++;
 return {fields,counts,total:SNAPSHOT_FIELDS.length,allPresent:counts.unknown===0,automaticAccuracyVerified:false};
}

// Compare adjacent independently observed snapshots only. A difference can
// corroborate a direct reading or yield a hypothesis, never an exact value.
// No carry across a hand/street change, ambiguous cards, missing exact
// baselines, stack increases, or a nonconserving pot.
export function reconcileSnapshots(previous,current,{potIncludesBets=false,maxAgeMs=1000}={}){
 const unknown=reason=>({status:'unavailable',reason,seats:{}});
 if(!potIncludesBets||!previous||!current)return unknown('No confirmed pot convention or adjacent sample');
 if(!Number.isFinite(previous.at)||!Number.isFinite(current.at)||current.at<=previous.at||current.at-previous.at>maxAgeMs)return unknown('Snapshots not adjacent and fresh');
 const a=previous.result,b=current.result,ca=candidateCards(a),cb=candidateCards(b);
 const da=a?.table_observation?.dealer?.candidate,db=b?.table_observation?.dealer?.candidate;
 if(!ca||!cb||ca.key!==cb.key||a.street_candidate!==b.street_candidate||!BET_SEATS.includes(da)||da!==db)return unknown('Hand or street identity uncertain');
 const exact=c=>c&&Number.isSafeInteger(c.value)&&c.value>=0&&!c.approximate?c.value:null;
 const pa=exact(a.number_candidates?.pot?.candidate),pb=exact(b.number_candidates?.pot?.candidate);
 if(pa===null||pb===null||pb<pa)return unknown('Pot missing, approximate or decreased');
 const seats={};let sum=0;
 for(const id of BET_SEATS){
  const x=a.table_observation?.seats?.[id],y=b.table_observation?.seats?.[id];
  const sa=exact(x?.stack),sb=exact(y?.stack),ba=exact(x?.bet),bb=exact(y?.bet);
  if(sa===null||sb===null||sa<sb)return unknown('Stack missing, approximate or increased');
  const delta=sa-sb;sum+=delta;
  if(!Number.isSafeInteger(sum))return unknown('Chip total outside safe range');
  if(ba===null){seats[id]={status:'unknown',delta};continue;}
  const implied=ba+delta;
  if(!Number.isSafeInteger(implied))return unknown('Chip total outside safe range');
  seats[id]={status:bb===null?'hypothesis':bb===implied?'consistent':'conflict',delta,implied,direct:bb};
 }
 if(sum!==pb-pa)return unknown('Pot change does not equal observed stack decreases');
 return {status:Object.values(seats).some(s=>s.status==='conflict')?'conflict':'consistent',seats,automaticAccuracyVerified:false};
}

// Diagnostic observations belong to exactly one capture. A failed or stale
// OCR result must not make older readings look current.
export function directNumericSnapshot(result,status,capturedAt,now){
 if(status!=='sampled'||!observationAge(capturedAt,now,1000).fresh||!result?.table_observation?.seats)return null;
 return {...result.table_observation,pot:result.number_candidates?.pot?.candidate};
}

// Retained history is display evidence, not a newly observed exact wager.
export function retainedRoundBet(state,id,street){
 const e=state?.seats?.[id];
 return e?.observed&&state.street===street&&!state.boundary&&!state.uncertain?e:undefined;
}
export function observedHandCommitment(state,id){
 if(!BET_SEATS.includes(id)||!state?.street)return null;
 const rounds=[...(state.closedRounds||[]).map(r=>r.seats[id]),state.seats[id]];
 const observed=rounds.filter(e=>e?.observed);
 if(!observed.length)return null;
 const value=observed.reduce((sum,e)=>sum+e.value,0);
 if(!Number.isSafeInteger(value))return null;
 return {value,observedRounds:observed.length,rounds:rounds.length,approximate:observed.some(e=>e.approximate),complete:false};
}

// Display-only observations. A missing or contradictory frame never overwrites
// the last reading. Nothing here upgrades evidence for decision calculations.
export function updateDisplayEvidence(previous,result,state,prior,{at,sampled=false}={}){
 if(!Number.isFinite(at)||at<0||(previous&&at<=previous.at))return previous;
 let fields={...(previous?.fields||{})};
 const changed=state?.generation!==prior?.generation;
 if(changed&&prior?.street){
  if(state.street==='Preflop'||!state.closedRounds?.length)fields={};
  else for(const k of Object.keys(fields))if(k==='pot'||k.endsWith('.bet')||k.endsWith('.status'))delete fields[k];
 }
 const incoming={};
 const obs=result?.table_observation;
 if(validSlots(result?.hole_slots,2)&&validSlots(result?.board_slots,5)&&!result.quality?.duplicate_card_candidates){
  [...result.hole_slots,...result.board_slots].forEach((slot,i)=>{
   const key=i<2?'hole.'+i:'board.'+(i-2);
   // Nulls can be temporary presence misses. Confirmed hand reset clears old slots.
   if(slot?.candidate&&validCard(slot.candidate))incoming[key]=slot.candidate;
   else if(slot===null&&!fields[key])incoming[key]=null;
  });
 }
 if(result?.street_candidate&&!state?.uncertain)incoming.street=result.street_candidate;
 if(BET_SEATS.includes(obs?.dealer?.candidate))incoming.dealer=obs.dealer.candidate;
 if(sampled){
  const put=(key,c)=>{if(c&&Number.isSafeInteger(c.value)&&c.value>=0)incoming[key]={value:c.value,approximate:!!c.approximate};};
  put('pot',result?.number_candidates?.pot?.candidate);
  for(const id of BET_SEATS)put(id+'.stack',obs?.seats?.[id]?.stack);
 }
 for(const id of BET_SEATS){
  const e=state?.seats?.[id];
  if(e?.observed)incoming[id+'.bet']={value:e.value,approximate:!!e.approximate,retainedAt:e.lastSeen};
 }
 for(const [key,value] of Object.entries(incoming)){
  const old=fields[key],numeric=value!==null&&typeof value==='object';
  const v=numeric?value.value:value,approximate=numeric&&value.approximate;
  const seen=numeric&&Number.isFinite(value.retainedAt)?value.retainedAt:at;
  if(!old||old.value===null||key.endsWith('.bet')){
   fields[key]={value:v,approximate,seen,votes:key.endsWith('.bet')?2:old?.value===v?old.votes+1:1,pending:null};
  }else if(old.value===v&&old.approximate===approximate){
   fields[key]={...old,seen,votes:old.votes+1,pending:null};
  }else{
   const pending=old.pending?.value===v&&old.pending?.approximate===approximate&&at-old.pending.at<=3000?old.pending.votes+1:1;
   fields[key]=pending>=2?{value:v,approximate,seen,votes:pending,pending:null}:{...old,pending:{value:v,approximate,votes:pending,at}};
  }
 }
 return {at,fields};
}
export function displayEvidenceValues(memory,now){
 const values={},details={};
 for(const [key,e] of Object.entries(memory?.fields||{})){
  values[key]=e.value;
  const age=observationAge(e.seen,now,1000);
  details[key]={...e,ageMs:age.ageMs,state:e.pending?'disputed':!age.fresh?'last seen':e.votes<2?'provisional':'repeated'};
 }
 return {values,details};
}
// Count only positive/explicit negative participation evidence. Unknown seats
// are reported as a range; absence of a red card back is not proof of a fold.
export function observedOpponentRange(result,locks={}){
 const active=new Set(['Playing','Check','Call','Raise','Bet','All-in','Big blind','Small blind','Participation evidence']);
 const inactive=new Set(['Fold','Folded','Sat out','Left table','Empty seat']);
 const participants=[],excluded=[],unknown=[];
 for(const id of BET_SEATS.filter(id=>id!=='hero')){
  const s=result?.table_observation?.seats?.[id];
  const manual=[locks[id+'.status'],locks[id+'.participation']].filter(v=>active.has(v)||inactive.has(v));
  const evidence=manual.length?manual:[s?.status_candidate,s?.participation_candidate,s?.card_visible_candidate===true?'Participation evidence':null,s?.turn_candidate===true?'Participation evidence':null];
  let yes=evidence.some(v=>active.has(v)),no=evidence.some(v=>inactive.has(v));
  if(!manual.length){
   const appearance=result?.seat_evidence?.seats?.[id]?.avatar_appearance?.candidate;
   // A colored avatar alone is not proof of participation: a newly joined
   // player may be waiting for the next deal. Card backs/status/turn support it.
   // A blue default avatar is not the same as a dimmed player.
   if(appearance==='dimmed'||appearance==='empty')no=true;
  }
  (yes&&!no?participants:no&&!yes?excluded:unknown).push(id);
 }
 return {min:participants.length,max:participants.length+unknown.length,participants,excluded,unknown};
}
