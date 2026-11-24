import {parseCards} from './quick-input.js';
export function reviewEquityInput(record,opponents,iterations=5000){
 const data=record?.corrected;
 if(record?.source!=='saved frame'||data?.verified_by_user!==true||!Array.isArray(data.hole)||!Array.isArray(data.board))throw Error('Confirm complete cards from a completed-hand recording first.');
 if(!Number.isInteger(opponents)||opponents<1||opponents>8)throw Error('Choose the observed number of opponents.');
 if(![1000,5000,20000].includes(iterations))throw Error('Invalid sample count.');
 const hole=parseCards(data.hole.join(' ')),board=data.board.length?parseCards(data.board.join(' ')):[];
 if(hole.length!==2||![0,3,4,5].includes(board.length)||new Set([...hole,...board]).size!==hole.length+board.length)throw Error('Invalid confirmed cards.');
 return {hole,board,opponents,styles:Array(opponents).fill('random'),iterations,seed:42};
}
