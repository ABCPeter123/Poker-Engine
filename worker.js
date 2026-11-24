import {equity} from './engine.js';
self.onmessage=({data})=>{try{self.postMessage({id:data.id,result:equity(data.input)});}catch(e){self.postMessage({id:data.id,error:e.message});}};
