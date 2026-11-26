// Offline study of completed, manually verified practice hands.
// No screen input, action execution, or connection to the live overlay.
import {equity} from '../engine.js';
export function rangeStudy({hole,board=[],opponents,pot,call,iterations=10000,seed=42}){
 if(!Number.isSafeInteger(pot)||pot<0||!Number.isSafeInteger(call)||call<0)throw Error('Enter verified pot and call amounts');
 if(!Number.isInteger(opponents)||opponents<1||opponents>8)throw Error('Invalid opponent count');
 const scenarios=[
  {name:'Uniform',styles:Array(opponents).fill('random')},
  {name:'One stronger range',styles:['tight',...Array(opponents-1).fill('random')]},
  {name:'All stronger ranges',styles:Array(opponents).fill('tight')}
 ].map(s=>{
  const r=equity({hole,board,opponents,styles:s.styles,iterations,seed});
  return {...s,equity:r.equity,standardError:r.standardError,showdownCallEV:r.equity*(pot+call)-call};
 });
 return {assumption:'No future betting, no rake or side pots. Range styles are synthetic sampling heuristics, not calibrated opponent distributions.',breakEven:pot+call===0?0:call/(pot+call),scenarios};
}
// Explicit opportunity denominators and beta-prior smoothing avoid
// drawing strong conclusions from a small number of reviewed hands.
export function reviewedFrequency(successes,opportunities,{alpha=2,beta=2}={}){
 if(!Number.isSafeInteger(successes)||!Number.isSafeInteger(opportunities)||successes<0||opportunities<successes||!Number.isFinite(alpha)||!Number.isFinite(beta)||alpha<=0||beta<=0)throw Error('Invalid frequency counts');
 return {successes,opportunities,raw:opportunities?successes/opportunities:null,smoothed:(successes+alpha)/(opportunities+alpha+beta),alpha,beta};
}
