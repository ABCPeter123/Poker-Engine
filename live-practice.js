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
