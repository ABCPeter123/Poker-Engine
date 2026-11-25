// User-entered observations are authoritative until explicitly released.
// This layer stores no image data and never accepts OCR as a manual edit.
export const SEATS=Object.freeze({hero:'You',left:'Left',upper_left:'Upper left',upper_right:'Upper right',right:'Right'});
export const CARD_KEYS=Object.freeze([...Array.from({length:2},(_,i)=>'hole.'+i),...Array.from({length:5},(_,i)=>'board.'+i)]);
const choices=(...values)=>values;
const seatChoices=choices('None',...Object.keys(SEATS));
export const FIELDS=Object.freeze([
 ...CARD_KEYS.map((key,i)=>({key,label:i<2?'Hole '+(i+1):'Board '+(i-1),type:'card'})),
 {key:'street',label:'Street',type:'choice',choices:choices('Unknown','Preflop','Flop','Turn','River')},
 {key:'pot',label:'Pot',type:'amount'},
 {key:'dealer',label:'Dealer',type:'choice',choices:seatChoices},
 {key:'turn',label:'Current player',type:'choice',choices:seatChoices},
 ...Object.keys(SEATS).flatMap(id=>[
  {key:id+'.stack',label:'Stack',type:'amount'},
  {key:id+'.bet',label:'Round bet',type:'amount'},
  {key:id+'.status',label:'Status',type:'choice',choices:choices('Unknown','Check','Call','Raise','Bet','Fold','All-in','Sat out','Small blind','Big blind','Playing','Left table')},
  {key:id+'.cards',label:'Cards',type:'choice',choices:choices('Unknown','Visible','Not visible')},
  {key:id+'.participation',label:'Participation',type:'choice',choices:choices('Unknown','Playing','Folded','Sat out','Empty seat')}
 ])
]);
const fields=new Map(FIELDS.map(f=>[f.key,f]));
const has=(obj,key)=>Object.prototype.hasOwnProperty.call(obj,key);
export const STORAGE_KEY='pokerist.manual-observations.v1';
export function parseManual(key,raw){
 const f=fields.get(key);
 if(!f)throw Error('Unknown observation field');
 const value=String(raw??'').trim();
 if(f.type==='amount'){
  if(!/^(?:\d+|\d{1,3}(?:[ ,]\d{3})+)$/.test(value))throw Error('Enter a whole nonnegative chip amount.');
  const n=Number(value.replace(/[ ,]/g,''));
  if(!Number.isSafeInteger(n))throw Error('Amount exceeds the safe integer range.');
  return n;
 }
 if(f.type==='card'){
  if(value==='-'||value.toLowerCase()==='none')return null;
  const m=value.toUpperCase().replace(/♠/g,'S').replace(/♥/g,'H').replace(/♦/g,'D').replace(/♣/g,'C').match(/^(10|[2-9TJQKA])([CDHS])$/);
  if(!m)throw Error('Enter a card such as As, 10h, or - for an empty slot.');
  return (m[1]==='10'?'T':m[1])+m[2].toLowerCase();
 }
 if(!f.choices.includes(value))throw Error('Select a valid value.');
 return value;
}
export function isLocked(locks,key){return has(locks,key);}
export function setManual(locks,key,raw){
 const value=parseManual(key,raw);
 const next={...locks,[key]:value};
 if(CARD_KEYS.includes(key)&&value!==null&&CARD_KEYS.some(k=>k!==key&&has(next,k)&&next[k]===value))throw Error('That card is already manually locked in another slot.');
 return next;
}
export function releaseManual(locks,key){const next={...locks};delete next[key];return next;}
export function resolveManual(auto,locks){return {...auto,...locks};}
export function decodeManual(serialized){
 let data;try{data=JSON.parse(serialized||'{}');}catch{return {};}
 if(!data||typeof data!=='object'||Array.isArray(data))return {};
 let out={};
 for(const f of FIELDS){
  if(!has(data,f.key))continue;
  try{out=setManual(out,f.key,data[f.key]===null?'-':data[f.key]);}catch{}
 }
 return out;
}
export function loadManual(storage){try{return decodeManual(storage.getItem(STORAGE_KEY));}catch{return {};}}
export function saveManual(storage,locks){try{storage.setItem(STORAGE_KEY,JSON.stringify(locks));return true;}catch{return false;}}
export function displayValue(key,value){
 if(value===undefined)return '?';
 if(value===null)return CARD_KEYS.includes(key)?'Empty':'None';
 if(typeof value==='number')return value.toLocaleString('en-CA');
 if((key==='dealer'||key==='turn')&&SEATS[value])return SEATS[value];
 return String(value);
}
// Build effective card slots while preserving manual identity even when a
// raw slot falsely reads the same card. An unresolved automatic conflict
// stays unknown, and existing practice validation rejects incomplete decks.
export function effectiveCards(result,locks){
 const slotsOf=(group,length)=>Array.from({length},(_,i)=>{
  const slots=result?.[group];
  if(!Array.isArray(slots)||slots.length!==length||!Object.hasOwn(slots,i))return {candidate:null,unknown:true};
  const slot=slots[i];
  if(slot===null)return null;
  if(!slot||typeof slot!=='object'||!Object.hasOwn(slot,'candidate'))return {candidate:null,unknown:true};
  if(slot.candidate!==null&&(typeof slot.candidate!=='string'||!/^[2-9TJQKA][cdhs]$/.test(slot.candidate)))return {candidate:null,unknown:true};
  return slot;
 });
 const hole=slotsOf('hole_slots',2),board=slotsOf('board_slots',5);
 const lockedCards=new Set(CARD_KEYS.filter(k=>isLocked(locks,k)&&locks[k]!==null).map(k=>locks[k]));
 const slots=[...hole,...board].map((slot,i)=>{
  const key=CARD_KEYS[i];
  if(isLocked(locks,key))return locks[key]===null?null:{candidate:locks[key],manual:true,verified:true};
  if(slot?.candidate&&lockedCards.has(slot.candidate))return {...slot,candidate:null,manual_conflict:true};
  return slot;
 });
 const b=slots.slice(2),h=slots.slice(0,2),n=b.filter(Boolean).length;
 const contiguous=b.slice(0,n).every(Boolean)&&!b.slice(n).some(Boolean);
 const street=contiguous&&!b.some(s=>s?.unknown)?({0:'Preflop',3:'Flop',4:'Turn',5:'River'})[n]||null:null;
 const known=slots.filter(s=>s?.candidate).map(s=>s.candidate);
 const lockedStreet=isLocked(locks,'street')?locks.street:null;
 return {...result,hole_slots:h,board_slots:b,street_candidate:isLocked(locks,'street')?(lockedStreet==='Unknown'?null:lockedStreet):street,
  quality:{...result?.quality,duplicate_card_candidates:known.length!==new Set(known).size,noncontiguous_board:!contiguous,
   unrecognized_visible_cards:slots.filter(s=>s&&!s.candidate).length}};
}
