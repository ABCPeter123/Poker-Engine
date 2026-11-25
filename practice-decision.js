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
 if(!Number.isInteger(opponents)||opponents<1||opponents>4)return {reason:'Confirm 1–4 opponents'};
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
