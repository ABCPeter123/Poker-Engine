const seats=['hero','left','upper_left','upper_right','right'];
const streets=['Preflop','Flop','Turn','River'];
const normalize=text=>String(text??'').trim().toUpperCase().replace(/10/g,'T').replace(/♠/g,'S').replace(/♥/g,'H').replace(/♦/g,'D').replace(/♣/g,'C');
function card(text){
 const s=normalize(text);
 if(!s||s==='?')return {state:'unknown',card:null};
 if(s==='-')return {state:'empty',card:null};
 if(!/^[2-9TJQKA][CDHS]$/.test(s))throw Error('Use card shorthand, e.g. As, ? for unknown or - for empty.');
 return {state:'known',card:s[0]+s[1].toLowerCase()};
}
function parseGroup(text,count,counts){
 const s=normalize(text).replace(/[\s,]+/g,'');
 if(!s)return [];
 if(!/^(?:[2-9TJQKA][CDHS])+$/.test(s))throw Error('Use card shorthand, e.g. As Kd.');
 const cards=s.match(/../g).map(c=>card(c).card);
 if(cards.length>count||!counts.includes(cards.length))throw Error('Enter two hole cards and zero, three, four or five board cards, or leave unknown fields blank.');
 return cards;
}
export function parseReviewAmount(value){
 const display=String(value??'').trim(),text=display.toUpperCase().replace(/[\u00a0\u202f]/g,' ');
 if(!text)return null;
 const compact=text.match(/^(\d+)(?:[.,](\d+))?\s*([KM])\.?$/);
 let amount;
 if(compact){
  if(text.includes(',')&&compact[2]?.length===3)throw Error('Ambiguous abbreviated amount.');
  const scale=compact[3]==='K'?3:6,frac=compact[2]||'';
  if(frac.length>scale&&/[1-9]/.test(frac.slice(scale)))throw Error('Enter whole chips.');
  const digits=(compact[1]+frac.slice(0,scale).padEnd(scale,'0')).replace(/^0+(?=\d)/,'');
  if(digits.length>16)throw Error('Chip amount is too large.');
  amount=Number(digits);
 }else{
  if(!/^(?:\d+|\d{1,3}(?: \d{3})+|\d{1,3}(?:,\d{3})+)$/.test(text))throw Error('Enter whole chips or a displayed amount such as 2.2K.');
  amount=Number(text.replace(/[ ,]/g,''));
 }
 if(!Number.isSafeInteger(amount)||amount<0)throw Error('Chip amount is too large.');
 return {display,value:amount,approximate:!!compact};
}
export function reviewSlotDefaults(result){
 const values={};
 for(const [group,count] of [['hole',2],['board',5]])for(let i=0;i<count;i++){
  const slot=result?.[group+'_slots']?.[i];
  values[group+'.'+i]=slot===null?'-':slot?.candidate||'?';
 }
 return values;
}
export function validateReview(values){
 const slotsMode=Array.from({length:2},(_,i)=>'hole.'+i).concat(Array.from({length:5},(_,i)=>'board.'+i)).some(k=>Object.hasOwn(values,k));
 const street=String(values.street??'').trim();
 if(street&&!streets.includes(street))throw Error('Select a valid street or leave it unknown.');
 let hole,board,slotData;
 if(slotsMode){
  const h=Array.from({length:2},(_,i)=>card(values['hole.'+i])),b=Array.from({length:5},(_,i)=>card(values['board.'+i]));
  const all=[...h,...b].filter(s=>s.state==='known').map(s=>s.card);
  if(new Set(all).size!==all.length)throw Error('Duplicate card in corrected readings.');
  hole=h.every(s=>s.state==='known')?h.map(s=>s.card):null;
  const n=b.findIndex(s=>s.state!=='known'),count=n===-1?5:n;
  const complete=b.slice(0,count).every(s=>s.state==='known')&&b.slice(count).every(s=>s.state==='empty');
  board=complete&&[0,3,4,5].includes(count)?b.slice(0,count).map(s=>s.card):null;
  slotData={hole_slots:h,board_slots:b};
 }else{
  hole=parseGroup(values.hole,2,[0,2]);board=parseGroup(values.board,5,[0,3,4,5]);
  if(new Set([...hole,...board]).size!==hole.length+board.length)throw Error('Duplicate card in corrected readings.');
  if(!hole.length)hole=null;
  if(!board.length&&street!=='Preflop')board=null;
 }
 const inferred=board?({0:'Preflop',3:'Flop',4:'Turn',5:'River'})[board.length]:null;
 if(street&&inferred&&street!==inferred)throw Error('Street conflicts with the confirmed board.');
 if(slotsMode&&street){
  const count=({Preflop:0,Flop:3,Turn:4,River:5})[street];
  if(slotData.board_slots.some((s,i)=>i<count?s.state==='empty':s.state==='known'))throw Error('Card slots conflict with the selected street.');
 }
 const stacks={},bets={};
 for(const seat of seats){stacks[seat]=parseReviewAmount(values[seat]);bets[seat]=parseReviewAmount(values['bet.'+seat]);}
 const seatChoice=value=>{const s=String(value??'').trim();if(!s)return null;if(!seats.includes(s))throw Error('Invalid seat.');return s;};
 return {hole,board,...slotData,pot:parseReviewAmount(values.pot),stacks,bets,dealer:seatChoice(values.dealer),turn:seatChoice(values.turn),street:inferred||street||null,verified_by_user:true};
}
