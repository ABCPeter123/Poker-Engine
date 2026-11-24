const engine = function pokerEngine(){
  const RANKS="23456789TJQKA", SUITS="♣♦♥♠", DECK=Array.from({length:52},(_,i)=>i), NAMES=["High card","One pair","Two pair","Three of a kind","Straight","Flush","Full house","Four of a kind","Straight flush"];
  const cardLabel=c=>RANKS[c%13]+SUITS[Math.floor(c/13)];
  function validate(cards){if(!Array.isArray(cards)||cards.some(c=>!Number.isInteger(c)||c<0||c>=52)||new Set(cards).size!==cards.length)throw Error("Duplicate or invalid cards");}
  function pack(category,ranks){let s=category;for(let i=0;i<5;i++)s=s*15+(ranks[i]||0);return s;}
  function straight(ranks){const s=new Set(ranks);if(s.has(14))s.add(1);for(let h=14;h>=5;h--)if([0,1,2,3,4].every(x=>s.has(h-x)))return h;return 0;}
  function score(cards){const counts=Array(15).fill(0),suits=Array.from({length:4},()=>[]);for(const c of cards){const r=2+c%13;counts[r]++;suits[Math.floor(c/13)].push(r);}const ranks=Array.from({length:13},(_,i)=>14-i).filter(r=>counts[r]), flush=suits.find(s=>s.length>=5);if(flush){const h=straight(flush);if(h)return pack(8,[h]);}
    const four=ranks.find(r=>counts[r]===4);if(four)return pack(7,[four,ranks.find(r=>r!==four)]);
    const three=ranks.find(r=>counts[r]>=3),pair=three&&ranks.find(r=>r!==three&&counts[r]>=2);if(pair)return pack(6,[three,pair]);
    if(flush)return pack(5,flush.sort((a,b)=>b-a));const h=straight(ranks);if(h)return pack(4,[h]);
    if(three)return pack(3,[three,...ranks.filter(r=>r!==three).slice(0,2)]);
    const pairs=ranks.filter(r=>counts[r]===2);if(pairs.length>=2)return pack(2,[pairs[0],pairs[1],ranks.find(r=>!pairs.slice(0,2).includes(r))]);
    if(pairs.length)return pack(1,[pairs[0],...ranks.filter(r=>r!==pairs[0]).slice(0,3)]);return pack(0,ranks);}
  function evaluate(cards){validate(cards);if(cards.length<5||cards.length>7)throw Error("Enter 5–7 cards");const value=score(cards);return {value,category:Math.floor(value/15**5),name:NAMES[Math.floor(value/15**5)]};}
  function rng(seed=42){let a=seed>>>0;return ()=>{a=(a+0x6D2B79F5)|0;let t=Math.imul(a^(a>>>15),1|a);t^=t+Math.imul(t^(t>>>7),61|t);return ((t^(t>>>14))>>>0)/4294967296;};}
  function startingStrength(a,b){const x=2+a%13,y=2+b%13,hi=Math.max(x,y),lo=Math.min(x,y);return x===y?50+hi*3:hi*2+lo+(Math.floor(a/13)===Math.floor(b/13)?5:0)+Math.max(0,5-(hi-lo));}
  function poolPair(pool,style,random){const draws=style==="tight"?5:style==="loose"?2:1;let best=null,bestScore=-1;for(let i=0;i<draws;i++){let a=Math.floor(random()*pool.length),b=Math.floor(random()*(pool.length-1));if(b>=a)b++;let s=startingStrength(pool[a],pool[b]);if(s>bestScore){bestScore=s;best=[a,b];}}const cards=best.map(i=>pool[i]);best.sort((a,b)=>b-a).forEach(i=>pool.splice(i,1));return cards;}
  function equity({hole,board=[],opponents=1,styles=[],iterations=5000,seed=42}){
    validate([...hole,...board]);if(hole.length!==2||![0,3,4,5].includes(board.length))throw Error("Choose two hole cards and 0, 3, 4 or 5 board cards");
    if(!Number.isInteger(opponents)||opponents<1||opponents>8)throw Error("Choose 1–8 opponents");if(!Number.isInteger(iterations)||iterations<1||iterations>100000)throw Error("Invalid sample count");
    if(styles.some(s=>!["random","loose","tight"].includes(s)))throw Error("Invalid range style");
    const available=DECK.filter(c=>!hole.includes(c)&&!board.includes(c));let wins=0,ties=0,losses=0,shares=0,shareSq=0,n=0;
    function record(runout,hands){const hero=score([...hole,...runout]);let best=hero,leaders=1;for(const hand of hands){const v=score([...hand,...runout]);if(v>best){best=v;leaders=1;}else if(v===best)leaders++;}const share=hero===best?1/leaders:0;shares+=share;shareSq+=share*share;n++;if(!share)losses++;else if(leaders===1)wins++;else ties++;}
    const exact=board.length===5&&opponents===1&&(!styles[0]||styles[0]==="random");
    if(exact){for(let i=0;i<available.length;i++)for(let j=i+1;j<available.length;j++)record(board,[[available[i],available[j]]]);}
    else{const random=rng(seed);for(let i=0;i<iterations;i++){const pool=available.slice(),hands=Array.from({length:opponents},(_,j)=>poolPair(pool,styles[j]||"random",random)),runout=board.slice();while(runout.length<5)runout.push(pool.splice(Math.floor(random()*pool.length),1)[0]);record(runout,hands);}}
    const e=shares/n;return {equity:e,win:wins/n,tie:ties/n,loss:losses/n,samples:n,exact,standardError:exact?0:Math.sqrt(Math.max(0,shareSq/n-e*e)/n),madeHand:board.length?evaluate([...hole,...board]).name:null};
  }
  function analyze({equity:e,pot,call,stack,raiseTo,foldProbability=0,raiseAllowed=true}){
    if(![e,pot,call,stack,raiseTo,foldProbability].every(Number.isFinite)||e<0||e>1||pot<0||call<0||stack<0||raiseTo<0||foldProbability<0||foldProbability>1)throw Error("Invalid chip amounts or probabilities");
    const c=Math.min(call,stack),actions=[];if(call>0)actions.push({action:"Fold",ev:0});actions.push({action:call?"Call":"Check",cost:c,ev:e*(pot+c)-c}); 
    // Heads-up simplified raise branch: one opponent matches the extra raise, all others fold.
    if(raiseAllowed&&raiseTo>c&&raiseTo<=stack){const extra=raiseTo-c;actions.push({action:call?"Raise":"Bet",cost:raiseTo,ev:foldProbability*pot+(1-foldProbability)*(e*(pot+raiseTo+extra)-raiseTo),conditional:true});}
    const odds=c?c/(pot+c):0;return {potOdds:odds,edge:e-odds,actions:actions.sort((a,b)=>b.ev-a.ev),callCost:c};
  }
  function deal({opponents=1,seed=42}={}){if(!Number.isInteger(opponents)||opponents<1||opponents>8)throw Error("Invalid opponent count");const random=rng(seed),pool=DECK.slice(),draw=()=>pool.splice(Math.floor(random()*pool.length),1)[0];return {hole:[draw(),draw()],villains:Array.from({length:opponents},()=>[draw(),draw()]),board:Array.from({length:5},draw)};}
  function showdown(hole,board,villains){validate([...hole,...board,...villains.flat()]);if(hole.length!==2||board.length!==5||villains.some(h=>h.length!==2))throw Error("Invalid showdown");const all=[hole,...villains].map(h=>evaluate([...h,...board])),best=Math.max(...all.map(h=>h.value)),winners=all.flatMap((h,i)=>h.value===best?[i]:[]);return {hands:all,winners,heroShare:winners.includes(0)?1/winners.length:0};}
  return {RANKS,SUITS,DECK,NAMES,cardLabel,evaluate,rng,equity,analyze,deal,showdown};
};
export const {RANKS,SUITS,DECK,NAMES,cardLabel,evaluate,rng,equity,analyze,deal,showdown}=engine();
