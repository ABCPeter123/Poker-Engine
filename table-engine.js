const factory = function tableEngine(){
 const STREETS=["Preflop","Flop","Turn","River"];
 const copy=s=>JSON.parse(JSON.stringify(s));
 const int=n=>Number.isSafeInteger(n)&&n>=0;
 const live=p=>!p.folded;
 const can=p=>live(p)&&p.stack>0;
 const order=(s,after)=>Array.from({length:s.players.length},(_,i)=>(after+i+1)%s.players.length);
 const pot=s=>s.players.reduce((n,p)=>n+p.total,0);
 const currentBet=s=>Math.max(0,...s.players.map(p=>p.street));
 const callFor=(s,i)=>Math.min(s.players[i].stack,Math.max(0,s.bet-s.players[i].street));
 function pay(p,n){p.stack-=n;p.street+=n;p.total+=n;}
 function log(s,i,action,amount=0){s.log.push({street:s.street,seat:i,action,amount,pot:pot(s)});}
 function refund(s){const sorted=s.players.map((p,i)=>({i,n:p.street})).sort((a,b)=>b.n-a.n);const n=sorted[0].n-sorted[1].n;if(n>0){const p=s.players[sorted[0].i];p.stack+=n;p.total-=n;p.street-=n;log(s,sorted[0].i,"Uncalled return",n);}s.bet=currentBet(s);}
 function finishStreet(s){refund(s);s.actor=null;s.pending=[];s.phase=s.players.filter(live).length===1||s.street===3?"result":"board";}
 function advance(s,after){
  const remaining=s.players.filter(live),able=s.players.filter(can);
  if(remaining.length===1){finishStreet(s);return;}
  s.pending=s.pending.filter(i=>can(s.players[i]));
  if(able.length<=1){s.pending=s.pending.filter(i=>s.players[i].street<s.bet);}
  const next=order(s,after).find(i=>s.pending.includes(i));
  if(next===undefined)finishStreet(s);else{s.actor=next;s.phase="betting";}
 }
 function draft({stacks=Array(6).fill(1000),hero=0,button=0,sb=5,bb=10,hand=1,hole=[]}={}){
  if(!Array.isArray(stacks)||stacks.length<2||stacks.length>9||stacks.some(n=>!int(n))||!int(hero)||hero>=stacks.length||!int(button)||button>=stacks.length||!int(sb)||!int(bb)||sb<=0||bb<sb)throw Error("Enter valid seats, stacks and blinds");
  const s={players:stacks.map((stack,i)=>({seat:i,stack,start:stack,street:0,total:0,folded:stack===0,sittingOut:stack===0,actedAt:null,last:""})),hero,button,sb,bb,hand,street:0,bet:0,minIncrement:bb,actor:null,phase:"setup",pending:[],hole:[],board:[],log:[],payouts:null};
  return setCards(s,"hole",hole);
 }
 function blindSeats(s){
  const active=s.players.filter(p=>p.stack>0||(!p.sittingOut&&s.phase!=="setup")).map(p=>p.seat);
  if(active.length<2||!active.includes(s.button))return {small:null,big:null};
  const next=i=>order(s,i).find(j=>active.includes(j));
  const small=active.length===2?s.button:next(s.button);
  return {small,big:next(small)};
 }
 function prepareNext(s){const stacks=s.players.map(p=>p.stack);const button=order(s,s.button).find(i=>stacks[i]>0)??s.button;return draft({stacks,hero:s.hero,button,sb:s.sb,bb:s.bb,hand:s.hand+1});}
 function editDraft(prev,patch){if(prev.phase!=="setup")throw Error("Edit seats and blinds before starting the hand");const old=prev.players.map(p=>p.stack),stacks=patch.stacks??old;const hero=patch.hero??Math.min(prev.hero,stacks.length-1),button=patch.button??Math.min(prev.button,stacks.length-1);return draft({stacks,hero,button,sb:patch.sb??prev.sb,bb:patch.bb??prev.bb,hand:prev.hand,hole:hero===prev.hero?prev.hole:[]});}
 function correctStack(prev,i,stack){if(prev.phase==="setup"){const stacks=prev.players.map(p=>p.stack);if(!int(i)||i>=stacks.length||!int(stack))throw Error("Invalid stack");stacks[i]=stack;return editDraft(prev,{stacks});}
  if(!["betting","board","result"].includes(prev.phase)||!int(i)||i>=prev.players.length||!int(stack))throw Error("Invalid stack correction");
  const s=copy(prev),p=s.players[i];if(p.sittingOut||(!p.folded&&((p.stack===0)!==(stack===0))))throw Error("Use undo to correct an all-in or sitting-out status");
  const delta=stack-p.stack;if(!delta)return s;p.stack=stack;p.start+=delta;log(s,i,"Stack correction",delta);return s;
 }
 function launch(s){if(s.phase!=="setup")throw Error("Hand already started");const next=start({stacks:s.players.map(p=>p.stack),hero:s.hero,button:s.button,sb:s.sb,bb:s.bb,hand:s.hand});return setCards(next,"hole",s.hole);}
 function start({stacks,hero=0,button=0,sb=5,bb=10,hand=1}){
  const s=draft({stacks,hero,button,sb,bb,hand});const {small,big}=blindSeats(s);
  if(small===null)throw Error("At least two funded seats are required and dealer must be funded");
  if(s.players[hero].stack===0)throw Error("Your seat needs chips before starting");
  s.phase="betting";s.bet=bb;
  for(const [i,n,label] of [[small,sb,"SB"],[big,bb,"BB"]]){const p=s.players[i],v=Math.min(p.stack,n);pay(p,v);p.last=label+" "+v;log(s,i,label,v);}
  s.pending=s.players.map((p,i)=>can(p)?i:-1).filter(i=>i>=0);advance(s,big);return s;
 }
 function legal(s){if(s.phase!=="betting"||s.actor===null)return null;const p=s.players[s.actor],due=Math.max(0,s.bet-p.street),call=Math.min(p.stack,due),maxTo=p.street+p.stack,minTo=s.bet<s.bb?s.bb:s.bet+s.minIncrement;
  const reopened=p.actedAt===null||s.bet-p.actedAt>=s.minIncrement;
  const raise=reopened&&maxTo>s.bet&&s.players.some((x,i)=>i!==s.actor&&can(x));
  return {due,call,check:due===0,fold:due>0,raise,minTo,maxTo,allIn:p.stack<=due||raise};
 }
 function act(prev,type,to){const s=copy(prev),i=s.actor,p=s.players[i],l=legal(s);if(!l)throw Error("No active player");let n=0,label=type;
  if(type==="fold"){if(!l.fold)throw Error("Check is available; folding is disabled");p.folded=true;}
  else if(type==="check"){if(!l.check)throw Error("Cannot check facing a bet");}
  else if(type==="call"){if(l.check)throw Error("Nothing to call");n=l.call;pay(p,n);}
  else if(type==="raise"||type==="all-in"){
   if(type==="all-in"){if(!l.allIn)throw Error("All-in is not available");to=l.maxTo;if(to<=s.bet){n=p.stack;pay(p,n);label="all-in call";}}
   if(to>s.bet){if(!l.raise||!int(to)||to>l.maxTo||(to<l.minTo&&to!==l.maxTo))throw Error("Raise must meet minimum, or be all-in");const old=s.bet;n=to-p.street;pay(p,n);s.bet=to;const full=to>=l.minTo;if(full){s.minIncrement=old<s.bb?to:to-old;for(const q of s.players)q.actedAt=null;}s.pending=s.players.flatMap((q,j)=>j!==i&&can(q)&&q.street<s.bet?[j]:[]);label=old===0?"bet":"raise";}
   else if(type==="raise")throw Error("Raise must exceed the current bet");
  }else throw Error("Unknown action");
  p.actedAt=s.bet;p.last=label+(n?" "+n:"")+(p.stack===0&&!p.folded?" · all-in":"");log(s,i,label,n);s.pending=s.pending.filter(j=>j!==i);advance(s,i);return s;
 }
 function setCards(prev,zone,cards){const s=copy(prev);if(!["hole","board"].includes(zone)||!Array.isArray(cards)||cards.length>(zone==="hole"?2:5))throw Error("Invalid card entry");const all=zone==="hole"?[...cards,...s.board]:[...s.hole,...cards];if(new Set(all).size!==all.length||all.some(c=>!int(c)||c>51))throw Error("Duplicate or invalid cards");
  if(zone==="board"){const max=s.phase==="board"?[3,4,5][s.street]:[0,3,4,5][s.street];if(cards.length>max)throw Error("Wait until the betting street closes");}s[zone]=cards.slice();return s;}
 function nextStreet(prev){const s=copy(prev);if(s.phase!=="board"||s.board.length!==[3,4,5][s.street])throw Error("Enter all cards for the next street");s.street++;s.bet=0;s.minIncrement=s.bb;for(const p of s.players){p.street=0;p.actedAt=null;p.last=p.folded?"Folded":p.stack===0?"All-in":"";}s.pending=s.players.flatMap((p,i)=>can(p)?[i]:[]);advance(s,s.button);return s;}
 function pots(s){const levels=[...new Set(s.players.map(p=>p.total).filter(x=>x>0))].sort((a,b)=>a-b);let prev=0;return levels.map(level=>{const members=s.players.filter(p=>p.total>=level),amount=(level-prev)*members.length;prev=level;return {amount,eligible:members.filter(live).map(p=>p.seat)};});}
 function eligibleAfterCall(s){const h=s.players[s.hero],cost=callFor(s,s.hero),cap=h.total+cost;return {cost,eligible:s.players.reduce((n,p)=>n+Math.min(p.total,cap),0),opponents:s.players.filter((p,i)=>i!==s.hero&&live(p)).length};}
 function settle(prev,winners){const s=copy(prev);if(s.phase!=="result")throw Error("Hand has not ended");const layers=pots(s),payouts=s.players.map(()=>0);if(!Array.isArray(winners)||winners.length!==layers.length)throw Error("Select winners for every pot");
  layers.forEach((layer,j)=>{const selected=layer.eligible.length===1?layer.eligible:winners[j];if(!Array.isArray(selected)||!selected.length||new Set(selected).size!==selected.length||selected.some(i=>!layer.eligible.includes(i)))throw Error("Select eligible winners for each pot");const share=Math.floor(layer.amount/selected.length);selected.forEach(i=>payouts[i]+=share);let odd=layer.amount%selected.length;for(const i of order(s,s.button))if(odd&&selected.includes(i)){payouts[i]++;odd--;}});
  s.players.forEach((p,i)=>p.stack+=payouts[i]);s.payouts=payouts;s.phase="settled";return s;}
 return {STREETS,draft,blindSeats,editDraft,correctStack,prepareNext,launch,start,legal,act,setCards,nextStreet,pot,pots,eligibleAfterCall,settle};
};
export const {STREETS,draft,blindSeats,editDraft,correctStack,prepareNext,launch,start,legal,act,setCards,nextStreet,pot,pots,eligibleAfterCall,settle}=factory();
