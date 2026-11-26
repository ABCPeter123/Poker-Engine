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

// Calculate from the current betting street only. Missing wagers cannot
// establish a zero call; a positive partial difference is a lower bound.
// Rounded labels are useful display evidence, but not exact prices.
export function roundedCallObservation(seats,prompt){
 const valid=c=>c&&whole(c.value);
 if(valid(prompt)&&prompt.approximate)return {value:prompt.value,source:'rounded call prompt'};
 const hero=seats?.hero?.bet;
 if(!valid(hero))return null;
 const amounts=Object.values(seats||{}).map(s=>s?.bet).filter(valid);
 if(!amounts.length)return null;
 const highest=amounts.reduce((a,b)=>a.value>=b.value?a:b);
 if(!(highest.approximate||hero.approximate)||highest.value<=hero.value)return null;
 return {value:highest.value-hero.value,source:'rounded current-round wager difference'};
}
export function observedCallPrice(seats,prompt,excluded=[]){
 const exact=c=>c&&!c.approximate&&whole(c.value)?c.value:null;
 const ids=Object.keys(SEAT_ANCHORS),hero=exact(seats?.hero?.bet);
 const wagers=ids.map(id=>exact(seats?.[id]?.bet));
 const readable=wagers.filter(v=>v!==null);
 const highest=readable.length?Math.max(...readable):null;
 const difference=hero!==null&&highest!==null?highest-hero:null;
 const complete=ids.every((id,i)=>wagers[i]!==null||(id!=='hero'&&excluded.includes(id)));
 const retained=ids.some((id,i)=>wagers[i]!==null&&seats?.[id]?.bet?.retained===true);
 const explicit=exact(prompt);
 if(explicit!==null){
  if(difference!==null&&(explicit<difference||(complete&&explicit!==difference)))return {reason:'Call price and wagers disagree'};
  return {value:explicit,source:'call prompt',partial:false};
 }
 if(roundedCallObservation(seats,prompt))return {reason:'Rounded call price; exact amount unavailable'};
 if(difference!==null&&(complete||difference>0))return {value:difference,source:retained?'retained round wager difference':complete?'visible round wagers':'partial round wager difference',partial:retained||!complete};
 return {reason:'Call price unreadable'};
}
// Conditional private-practice calculation, with explicit evidence sources.
export function practicePanelModel({street,pot,prompt,seats,equities,excluded=[]}){
 const exact=c=>c&&!c.approximate&&whole(c.value)?c.value:null;
 const ids=Object.keys(SEAT_ANCHORS);
 const wagers=ids.map(id=>exact(seats?.[id]?.bet));
 const readable=wagers.filter(v=>v!==null);
 const complete=readable.length===ids.length;
 const retained=ids.some(id=>seats?.[id]?.bet?.retained===true);
 const stack=exact(seats?.hero?.stack);
 if(stack===0)return {reason:'All-in · no action required'};
 const price=observedCallPrice(seats,prompt,excluded);
 if(price.reason)return price;
 const call=price.value;
 if(stack===0||stack!==null&&call>stack)return {reason:'All-in eligibility unresolved'};
 let amount=exact(pot),source='displayed pot',partial=false;
 if(amount===null&&street==='Preflop'&&readable.length){
  amount=readable.reduce((a,b)=>a+b,0);
  source=complete?'visible preflop wagers':'partial visible preflop wagers';
  partial=!complete||retained;
 }
 if(!whole(amount))return {reason:'Pot unavailable'};
 const model=conditionalCallModel({pot:amount,call,equities});
 if(!model)return {reason:'Equity unavailable'};
 return {...model,pot:amount,call,source,partial,pricePartial:price.partial,wagerCount:readable.length,priceSource:price.source};
}

// A deterministic conservative practice baseline is a conditional result,
// not a claim that the incomplete pot or random-hand equities are exact.
export function practiceHeadline(model){
 if(!model||model.reason||!Array.isArray(model.outcomes)||!model.outcomes.length)return null;
 const outcome=model.unanimous??(model.outcomes.includes('Fold')?'Fold':model.outcomes.includes('Indifferent')?'Indifferent':model.outcomes[0]);
 return {action:outcome==='Indifferent'?'Fold':outcome,sensitive:!!model.partial||!!model.pricePartial||!model.unanimous||outcome==='Indifferent',policy:model.unanimous?'all scenarios agree':'conservative scenario'};
}

// Compare a hypothetical extra unit invested beyond the call. Each scenario
// assumes every opponent matches that unit, unchanged showdown equity, no
// further action, no side pots. No legal minimum raise or size is inferred.
export function conditionalRaiseComparison({model,counts,equities,stack,raiseVisible}){
 if(!raiseVisible||!model||model.reason||!whole(model.call)||!whole(stack)||stack<=model.call||
    !Array.isArray(counts)||!Array.isArray(equities)||!counts.length||counts.length!==equities.length||
    !counts.every(n=>Number.isInteger(n)&&n>=1&&n<=4)||!equities.every(e=>Number.isFinite(e)&&e>=0&&e<=1))return null;
 const edges=equities.map((e,i)=>e*(counts[i]+1)-1);
 const allPositive=edges.every(e=>e>0);
 const baseline=practiceHeadline(model);
 const raise=allPositive&&!model.partial&&!model.pricePartial&&baseline&&['Check','Call'].includes(baseline.action);
 return {action:raise?'Raise':null,edges,assumption:'All opponents match extra chips; unchanged showdown equity; no side pots',sizeVerified:false};
}

// A screen snapshot cannot establish the last full raise increment. For
// authorized practice only, compute a conservative upper bound on the
// minimum full raise, conditional on the exact observed values and the
// standard no-limit rules. The actual room may impose other chip steps.
export function conservativeRaiseBounds({street,heroBet,stack,call,bigBlind,raiseVisible}){
 if(!raiseVisible||!whole(heroBet)||!whole(stack)||!whole(call)||!Number.isSafeInteger(heroBet+call)||!Number.isSafeInteger(heroBet+stack)||stack<=call)return null;
 const highest=heroBet+call,maxTo=heroBet+stack;
 // A full preflop price includes at least the nominal big blind.
 // Postflop a small all-in may be below the blind; do not guess it.
 const bb=whole(bigBlind)&&bigBlind>0?bigBlind:street==='Preflop'&&highest>0?highest:null;
 if(bb===null)return null;
 const increment=Math.max(bb,highest);
 const safeTo=highest+increment;
 if(!Number.isSafeInteger(safeTo)||safeTo>maxTo)return null;
 return {safeTo,maxTo,additional:safeTo-heroBet,highest,increment,
         exactMinimum:false,conditional:true};
}
// Use only explicit, exact, non-all-in big-blind observations. Two
// matching snapshots are required and the evidence never crosses hands.
export function observePracticeBlind(previous,result,hand,at){
 if(!Number.isFinite(at)||at<0||(previous&&at<=previous.at))return previous;
 const old=hand?.started?null:previous;
 if(hand?.phase!=='active')return null;
 if(result?.street_candidate!=='Preflop')return old;
 const candidates=Object.values(result?.table_observation?.seats||{}).filter(s=>s.status_candidate==='Big blind'&&s.bet_chip_present===true&&s.bet&&!s.bet.approximate&&whole(s.bet.value)&&s.bet.value>0&&s.stack&&whole(s.stack.value)&&s.stack.value>0);
 if(candidates.length!==1)return old;
 const value=candidates[0].bet.value;
 if(old?.confirmed&&old.value!==value)return {value:null,count:0,confirmed:false,conflict:true,at};
 if(old?.conflict)return old;
 const count=old?.value===value?old.count+1:1;
 return {value,count,confirmed:count>=2,at};
}

// Point-estimate scenario for a rounded display, never an exact wager or
// verified legal size. Do not use this fallback to override conflicts.
export function roundedPracticeScenario(args){
 const first=practicePanelModel(args);
 if(!['Rounded call price; exact amount unavailable','Pot unavailable'].includes(first.reason))return null;
 const hasRounded=[args.pot,args.prompt,...Object.values(args.seats||{}).map(s=>s?.bet)].some(c=>c?.approximate&&whole(c.value));
 if(!hasRounded)return null;
 const point=c=>c?.approximate&&whole(c.value)?{...c,approximate:false}:c;
 const seats=Object.fromEntries(Object.entries(args.seats||{}).map(([id,s])=>[id,{...s,bet:point(s?.bet)}]));
 const model=practicePanelModel({...args,seats,pot:point(args.pot),prompt:point(args.prompt)});
 if(model.reason)return null;
 return {...model,estimated:true,pricePartial:true,source:model.source+' (rounded point estimate)'};
}
// Visible price must not disappear while cards or equity are unresolved.
export function practicePriceHeadline(price,rounded,stack=null){
 if(stack===0)return 'All-in · no action required';
 if(whole(stack)&&stack>0&&price&&!price.reason&&whole(price.value)&&price.value>stack)return 'Your turn · All-in call cost '+stack.toLocaleString('en-CA');
 if(whole(stack)&&stack>0&&rounded&&whole(rounded.value)&&rounded.value>stack)return 'Your turn · Call cost up to '+stack.toLocaleString('en-CA');
 if(price&&!price.reason&&whole(price.value)){
  if(price.value===0)return 'Your turn · Check available';
  return 'Your turn · Call cost '+(price.partial?'at least ':'')+price.value.toLocaleString('en-CA');
 }
 if(rounded&&whole(rounded.value))return 'Your turn · Call cost ≈'+rounded.value.toLocaleString('en-CA');
 return 'Your turn · Price unavailable';
}

// Conditional sizing for the authorized local practice workspace. No
// external-room minimum is asserted when the last increment is unknown.
export function practiceRaiseSizing({street,hero,call,bigBlind,raiseVisible,zeroWagerEvidence=false}){
 const exact=c=>c&&!c.approximate&&whole(c.value)?c.value:null;
 let committed=exact(hero?.bet);
 if(committed===null&&!hero?.bet&&zeroWagerEvidence&&hero?.bet_chip_present===false)committed=0;
 const stack=exact(hero?.stack);
 if(!raiseVisible)return {reason:'Raise control not observed'};
 if(committed===null)return {reason:'Your current-street wager is unreadable'};
 if(stack===null)return {reason:'Exact remaining stack unavailable'};
 if(!whole(call)||stack<=call)return {reason:'No chips available beyond the call'};
 if(!(whole(bigBlind)&&bigBlind>0)&&!(street==='Preflop'&&committed+call>0))return {reason:'Big blind not established'};
 const bounds=conservativeRaiseBounds({street,heroBet:committed,stack,call,bigBlind,raiseVisible});
 return bounds?{bounds,assumedZero:!hero?.bet}:{reason:'No conservative full-raise size fits the remaining stack'};
}
export function sizedPracticeHeadline(model,raise,sizing){
 const baseline=practiceHeadline(model);
 if(!baseline)return null;
 if(raise?.action&&sizing?.bounds)return {text:'Raise to '+sizing.bounds.safeTo.toLocaleString('en-CA')+' (conditional)',raise:true};
 return {text:baseline.action==='Call'?'Call '+(model.estimated?'≈':model.pricePartial?'at least ':'')+model.call.toLocaleString('en-CA'):baseline.action,raise:false,reason:raise?.action?sizing?.reason:null};
}
