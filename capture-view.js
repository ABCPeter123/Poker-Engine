export function previewDimensions(width,height,limit,availableWidth,availableHeight,native=false){
 const nums=[width,height,limit,availableWidth,availableHeight];if(nums.some(n=>!Number.isFinite(n)||n<=0))return null;
 const scale=Math.min(limit/width,availableWidth/width,availableHeight/height,native?1:Infinity);
 return {width:Math.max(1,Math.floor(width*scale)),height:Math.max(1,Math.floor(height*scale)),scale};
}
export function captureOptions(profile){
 const fps=profile==='detail'?30:profile==='smooth'?60:30;
 return {video:{width:{ideal:3840},height:{ideal:2160},frameRate:{ideal:fps,max:fps}},audio:false};
}
export function captureHealth({width,height,sourceWidth,sourceHeight,renderWidth,renderHeight,fps,dropped,total}){
 const lines=[];
 if(width&&height)lines.push(width+' × '+height+' px');
 if(Number.isFinite(fps)&&fps>=0)lines.push(fps.toFixed(1)+' FPS');
 if(Number.isFinite(dropped)&&Number.isFinite(total)&&total>0)lines.push((100*dropped/total).toFixed(1)+'% dropped');
 if(width&&renderWidth&&height&&renderHeight&&Math.max(renderWidth/width,renderHeight/height)>1.05)lines.push('Preview upscaled');
 if(sourceWidth&&sourceHeight&&width&&height&&(width<sourceWidth*.9||height<sourceHeight*.9))lines.push('Capture below reported track resolution');
 return lines.join(' · ');
}

export function orientationDegrees(mode){return ({auto:0,left:-90,right:90,flip:180})[mode]??0;}
export function orientedDimensions(width,height,degrees){return Math.abs(degrees%180)===90?{width:height,height:width}:{width,height};}

export function shareOptions(profile,mode='window'){
 if(mode==='compat')return {video:true,audio:false};
 return {...captureOptions(profile),video:{...captureOptions(profile).video,displaySurface:mode==='monitor'?'monitor':'window'},selfBrowserSurface:'exclude',surfaceSwitching:'exclude'};
}
export function shareError(error){
 const name=error?.name;
 if(name==='NotAllowedError'||name==='AbortError')return 'Sharing cancelled or denied. Your previous source is unchanged.';
 if(name==='NotReadableError')return 'Windows or the browser could not capture this window. Restore UxPlay and try Compatibility mode.';
 if(name==='NotFoundError')return 'No capturable source found. Connect the iPhone and restore the UxPlay video window first.';
 if(name==='OverconstrainedError'||name==='TypeError')return 'Capture options were rejected. Try Compatibility mode.';
 if(name==='InvalidStateError')return 'Click Share again while this browser tab is active.';
 return error?.message||'Screen capture failed.';
}
export function shareTrackState(track,hasFrame,lastFrame,now){
 if(!track||track.readyState==='ended')return 'ended';
 if(track.muted)return 'muted';
 if(!hasFrame)return 'waiting';
 if(Number.isFinite(lastFrame)&&now-lastFrame>5000)return 'stalled';
 return 'ready';
}
