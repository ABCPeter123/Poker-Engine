import test from 'node:test';
import assert from 'node:assert/strict';
import {validateReview,parseReviewAmount,reviewSlotDefaults} from '../review-validation.js';
test('partial slots preserved without collapsing positions',()=>{
 const r=validateReview({'hole.0':'As','hole.1':'?','board.0':'4h','board.1':'?','board.2':'5d','board.3':'-','board.4':'-',street:'Flop',pot:'4.5K'});
 assert.equal(r.hole,null);assert.equal(r.board,null);assert.equal(r.street,'Flop');
 assert.deepEqual(r.board_slots.map(x=>x.card),['4h',null,'5d',null,null]);
 assert.equal(r.pot.value,4500);
});
test('empty and unknown distinguish preflop from incomplete board',()=>{
 const a={'hole.0':'As','hole.1':'Kd','board.0':'-','board.1':'-','board.2':'-','board.3':'-','board.4':'-'};
 assert.deepEqual(validateReview(a).board,[]);
 assert.equal(validateReview({...a,'board.0':'?'}).board,null);
 assert.throws(()=>validateReview({...a,street:'Flop'}));
});
test('partial duplicate and contradictory street rejected',()=>{
 assert.throws(()=>validateReview({'hole.0':'As','board.0':'As'}));
 assert.throws(()=>validateReview({'board.0':'As',street:'Preflop'}));
 assert.throws(()=>validateReview({board:'As Kd Qh',street:'Turn'}));
});
test('grouped and abbreviated amounts are parsed exactly as displayed',()=>{
 for(const [s,n] of [['4k',4000],['200K',200000],['4 K',4000],['19,950',19950],['19 950',19950],['1.001K',1001],['0',0],['2.2K',2200]])assert.equal(parseReviewAmount(s).value,n);
 for(const s of ['1 23','1O0','4.0001K','1,500K','9007199254740992'])assert.throws(()=>parseReviewAmount(s));
});
test('bet and stack zero retained independently',()=>{
 const r=validateReview({'bet.hero':'0',hero:'4K',dealer:'left',turn:'hero'});
 assert.equal(r.bets.hero.value,0);assert.equal(r.stacks.hero.value,4000);
 assert.equal(r.bets.left,null);assert.equal(r.dealer,'left');assert.equal(r.turn,'hero');
});
test('prefill distinguishes empty from unknown and preserves slots',()=>{
 const v=reviewSlotDefaults({hole_slots:[{candidate:'As'},null],board_slots:[{candidate:null},null,{candidate:'2h'}]});
 assert.equal(v['hole.0'],'As');assert.equal(v['hole.1'],'-');assert.equal(v['board.0'],'?');assert.equal(v['board.2'],'2h');assert.equal(v['board.4'],'?');
});
