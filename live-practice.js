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
