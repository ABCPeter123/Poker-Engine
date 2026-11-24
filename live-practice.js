import {parseCards} from './quick-input.js';
export function candidateCards(result){
 const holes=result?.hole_slots,board=result?.board_slots;
 if(!Array.isArray(holes)||holes.length!==2||!Array.isArray(board)||board.length!==5||!result?.street_candidate||result.quality?.duplicate_card_candidates||result.quality?.noncontiguous_board||result.quality?.unrecognized_visible_cards)return null;
 const h=holes.map(x=>x?.candidate),b=board.filter(Boolean).map(x=>x?.candidate);
 if(h.some(x=>!x)||b.some(x=>!x)||![0,3,4,5].includes(b.length))return null;
 if(board.slice(0,b.length).some(x=>!x)||board.slice(b.length).some(Boolean))return null;
 if(({0:'Preflop',3:'Flop',4:'Turn',5:'River'})[b.length]!==result.street_candidate)return null;
 try{const hole=parseCards(h.join(' ')),cards=b.length?parseCards(b.join(' ')):[];if(hole.length!==2||new Set([...hole,...cards]).size!==hole.length+cards.length)return null;return {hole,board:cards,labels:{hole:h,board:b},key:JSON.stringify([hole,cards])};}catch{return null;}
}
export function stableReading(prev,candidate,now){
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
 const groups=[result?.hole_slots,result?.board_slots];
 if(!Array.isArray(groups[0])||groups[0].length!==2||!Array.isArray(groups[1])||groups[1].length!==5)return null;
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
export function createBetMemory(){return {street:null,hole:null,dealer:null,boundary:null,last:null,seats:seats(),status:'Waiting for round confirmation'};}
function streetOf(r){
 const b=r?.board_slots;
 if(!Array.isArray(b)||b.length!==5||r.quality?.duplicate_card_candidates||r.quality?.noncontiguous_board)return null;
 const n=b.filter(Boolean).length,s=({0:'Preflop',3:'Flop',4:'Turn',5:'River'})[n];
 return s===r.street_candidate&&b.slice(0,n).every(Boolean)&&!b.slice(n).some(Boolean)?s:null;
}
function holeOf(r){
 const h=r?.hole_slots;
 if(!Array.isArray(h)||h.length!==2)return null;
 const a=h.map(c=>c?.candidate);
 return a.every(x=>typeof x==='string'&&/^[2-9TJQKA][cdhs]$/.test(x))&&a[0]!==a[1]?a.sort().join(' '):null;
}
const fresh=(t,now)=>Number.isFinite(t)&&Number.isFinite(now)&&t>=0&&now>=t&&now-t<=5000;
function amount(c,confidence,minimum=75){
 return c&&Number.isSafeInteger(c.value)&&c.value>=0&&Number.isFinite(confidence)&&confidence>=minimum?c:null;
}
function accept(e,b,stack,t,source){
 return {...e,value:b.value,observed:true,approximate:!!b.approximate,stack:stack?.value??null,lastSeen:t,pending:null,warning:source==='correction'?'Corrected from repeated lower readings':null,source};
}
export function updateBetMemory(previous,r,{capturedAt:t,now,ocr=false}={}){
 const old=previous||createBetMemory();
 if(!fresh(t,now)||(old.last!==null&&t<=old.last))return old;
 let state={...old,last:t,seats:Object.fromEntries(BET_SEATS.map(s=>[s,{...old.seats[s]}]))};
 const street=streetOf(r),hole=holeOf(r),d=r?.table_observation?.dealer?.candidate,dealer=BET_SEATS.includes(d)?d:null;
 if(!street||(state.street&&street!=='Preflop'&&streets.indexOf(street)<streets.indexOf(state.street))){
  state.boundary=null;state.status='Round uncertain; holding prior values';
  for(const e of Object.values(state.seats))e.pending=null;
  return state;
 }
 const newHole=street==='Preflop'&&state.street==='Preflop'&&hole&&state.hole&&hole!==state.hole;
 const newDealer=street==='Preflop'&&state.street==='Preflop'&&dealer&&state.dealer&&dealer!==state.dealer;
 if(street!==state.street||newHole||newDealer){
  const key=[street,newHole?hole:null,newDealer?dealer:null].join('|'),p=state.boundary;
  state.boundary={key,count:p?.key===key&&t-p.last<=6000?p.count+1:1,last:t};
  if(state.boundary.count<2){state.status='Checking round change';for(const e of Object.values(state.seats))e.pending=null;return state;}
  state={...state,street,hole,dealer,boundary:null,seats:seats()};
 }else{
  state.boundary=null;state.hole=state.hole||hole;state.dealer=state.dealer||dealer;
 }
 state.status=state.street+' · tracked candidates';
 if(!ocr)return state;
 for(const id of BET_SEATS){
  const e=state.seats[id],s=r?.table_observation?.seats?.[id],b=amount(s?.bet,s?.bet?.ocr_confidence??s?.bet_confidence);
  const stack=amount(s?.stack,s?.stack?.ocr_confidence??s?.stack_confidence,85);
  if(!b){e.pending=null;e.warning=e.observed?'Missing sample; holding last value':null;continue;}
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
export function correctTrackedBet(state,seat,value,now){
 if(!BET_SEATS.includes(seat)||!Number.isSafeInteger(value)||value<0||!Number.isFinite(now))throw Error('Enter a nonnegative whole chip amount.');
 const s=state||createBetMemory();
 return {...s,last:Math.max(s.last??0,now),seats:{...s.seats,[seat]:{...blank(),value,observed:true,lastSeen:now,source:'manual',warning:'Manually corrected'}}};
}
export function trackedBetLabel(e){
 if(!e)return '0 (initial)';
 return (e.approximate?'≈':'')+e.value.toLocaleString('en-CA')+(e.observed?'':' (initial)')+(e.warning?' *':'');
}
