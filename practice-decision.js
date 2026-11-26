// Geometry for the calibrated five-seat layout; approximate anchors, not
// an input injection mechanism. This is a private-practice model only.
import {analyze} from './engine.js';
export const SEAT_ANCHORS=Object.freeze({upper_left:[36,13],upper_right:[64,13],left:[16,48],right:[84,48],hero:[50,82]});
export function overlayPosition(anchor,crop){
 const [x,y]=anchor,b=crop?.bounds,s=crop?.input_size;
 if(!Array.isArray(b)||b.length!==4||!Array.isArray(s)||s.length!==2||![...b,...s].every(Number.isFinite)||s[0]<=0||s[1]<=0||b[0]<0||b[1]<0||b[2]>s[0]||b[3]>s[1]||b[2]<=b[0]||b[3]<=b[1])return [x,y];
 return [100*(b[0]+(b[2]-b[0])*x/100)/s[0],100*(b[1]+(b[3]-b[1])*y/100)/s[1]];
}
const whole=v=>Number.isSafeInteger(v)&&v>=0;
export const inactive=(a,id)=>['Fold','Sat out','Left table'].includes(a[id+'.status'])||['Folded','Sat out','Empty seat'].includes(a[id+'.participation']);
export function decisionInputs(a,exact,{confirmed=false,opponents=0}={}){
 if(!confirmed)return {reason:'Confirm pot format and no side pots'};
 if(a.turn!=='hero')return {reason:a.turn===undefined?'Current player unknown':'Waiting for your turn'};
 if(!Number.isInteger(opponents)||opponents<1||opponents>4)return {reason:'Select the number of opponents in the practice controls'};
 if(inactive(a,'hero'))return {reason:'You are not participating'};
 if(!exact.has('pot')||!whole(a.pot)||!exact.has('hero.stack')||!whole(a['hero.stack'])||!exact.has('hero.bet')||!whole(a['hero.bet']))return {reason:'Confirm pot, your stack and bet'};
 if(a['hero.stack']===0)return {reason:'No chips available to act'};
 const ids=Object.keys(SEAT_ANCHORS).filter(id=>id!=='hero'&&!inactive(a,id));
 if(ids.length!==opponents)return {reason:'Confirm which seats are participating'};
 if(ids.some(id=>!exact.has(id+'.bet')||!whole(a[id+'.bet'])))return {reason:'Confirm opponents’ round bets'};
 const highest=Math.max(a['hero.bet'],...ids.map(id=>a[id+'.bet'])),call=highest-a['hero.bet'];
 if(call>a['hero.stack'])return {reason:'All-in/side-pot eligibility is not supported'};
 if(a.pot<a['hero.bet']+ids.reduce((n,id)=>n+a[id+'.bet'],0))return {reason:'Pot is smaller than visible wagers'};
 return {pot:a.pot,stack:a['hero.stack'],call};
}
export function decisionFromEquity(input,equity){
 if(input.reason)return input;
 if(!Number.isFinite(equity)||equity<0||equity>1)return {reason:'Waiting for card equity'};
 const result=analyze({...input,equity,raiseTo:0,raiseAllowed:false});
 const best=result.actions[0];
 return {action:best.action+(best.action==='Call'?' '+result.callCost.toLocaleString('en-CA'):''),equity,potOdds:result.potOdds,ev:best.ev};
}
// A focused or changed input owns its draft until commit/release.
// Rendering an automatic value never creates a manual lock.
export function inputValue(value,field){
 if(value===undefined)return '';
 if(value===null)return field.type==='card'?'-':'';
 if(field.type==='choice'&&!field.choices.includes(value))return '';
 return String(value);
}

// A manual count is authoritative. Otherwise, derive only from explicitly
// classified manual seats, never from missing cards or absent OCR.
export function practiceOpponentCount(selected,locks={}){
 const n=Number(selected);
 if(Number.isInteger(n)&&n>=1&&n<=4)return {count:n,source:'selected'};
 const active=new Set(['Playing','Check','Call','Raise','Bet','All-in','Big blind','Small blind']);
 const dead=new Set(['Fold','Folded','Sat out','Left table','Empty seat']);
 let count=0;
 for(const id of Object.keys(SEAT_ANCHORS).filter(x=>x!=='hero')){
  const values=[locks[id+'.status'],locks[id+'.participation']];
  const yes=values.some(v=>active.has(v)),no=values.some(v=>dead.has(v));
  if(yes===no)return {count:null,source:'unknown'};
  if(yes)count++;
 }
 return {count:count||null,source:'manual seats'};
}

// Conditional educational calculation using an explicitly observed call price.
 // The displayed pot is a hypothetical eligible pot, not verified accounting.
export function conditionalCallModel({pot,call,equities}){
 if(!whole(pot)||!whole(call)||!Number.isSafeInteger(pot+call)||pot+call<=0||!Array.isArray(equities)||!equities.length||equities.some(e=>!Number.isFinite(e)||e<0||e>1))return null;
 const odds=call/(pot+call);
 const outcomes=equities.map(e=>call===0?'Check':e>odds?'Call':e<odds?'Fold':'Indifferent');
 return {odds,outcomes,unanimous:outcomes.every(x=>x===outcomes[0])?outcomes[0]:null,conditional:true};
}

// Conditional private-practice calculation, with explicit evidence sources.
export function practicePanelModel({street,pot,prompt,seats,equities}){
 const exact=c=>c&&!c.approximate&&whole(c.value)?c.value:null;
 const ids=Object.keys(SEAT_ANCHORS);
 const wagers=ids.map(id=>exact(seats?.[id]?.bet));
 const readable=wagers.filter(v=>v!==null);
 const complete=readable.length===ids.length;
 const hero=exact(seats?.hero?.bet),stack=exact(seats?.hero?.stack);
 const visibleMax=readable.length?Math.max(...readable):null;
 const inferredCall=complete&&hero!==null?visibleMax-hero:null;
 const explicitCall=exact(prompt);
 if(explicitCall!==null&&hero!==null&&visibleMax!==null&&explicitCall<visibleMax-hero)return {reason:'Call price and wagers disagree'};
 if(explicitCall!==null&&inferredCall!==null&&explicitCall!==inferredCall)return {reason:'Call price and wagers disagree'};
 const call=explicitCall??inferredCall;
 if(call===null)return {reason:'Call price unreadable'};
 if(stack===0||stack!==null&&call>stack)return {reason:'All-in eligibility unresolved'};
 let amount=exact(pot),source='displayed pot',partial=false;
 if(amount===null&&street==='Preflop'&&readable.length&&(complete||explicitCall!==null)){
  amount=readable.reduce((a,b)=>a+b,0);
  source=complete?'visible preflop wagers':'partial visible preflop wagers';
  partial=!complete;
 }
 if(!whole(amount))return {reason:'Pot unavailable'};
 const model=conditionalCallModel({pot:amount,call,equities});
 if(!model)return {reason:'Equity unavailable'};
 return {...model,pot:amount,call,source,partial,wagerCount:readable.length,priceSource:explicitCall!==null?'call prompt':'visible wagers'};
}
