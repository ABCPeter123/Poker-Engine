"""Offline automatic text-crop audit of completed saved screenshots."""
import argparse,json,time,statistics,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image
from amount_text import number_text
from amount_glyph_library import decode_library
from automatic_glyph_audit import GlyphBank
from glyph_audit import feature

SIZE=(1536,709)
STACKS={'hero':(725,600),'left':(347,469),'upper_left':(557,172),'upper_right':(975,172),'right':(1191,469)}
AMOUNTS={'pot':(745,203,815,232),'bet_ul':(553,197,630,226),'bet_ur':(907,197,984,226),'bet_left':(481,294,555,322),'bet_right':(980,294,1058,323),'bet_hero':(831,424,911,456)}

def runs(mask):
    return np.flatnonzero(np.diff(np.r_[False,mask,False])).reshape(-1,2)

def read_glyphs(patch,bank):
    if patch.size==0:return None
    lo,hi=np.percentile(patch,[15,99])
    g=np.clip((patch-lo)/max(hi-lo,20),0,1)
    options=set();cache={}
    for t in (.45,.50,.55,.60,.65,.70,.75,.80):
        m=g>=t
        parts=[g[:,x:y] for x,y in runs(m.any(0)) if m[:,x:y].sum()>=2]
        if not 1<=len(parts)<=16:continue
        matches=[]
        for part in parts:
            key=part.shape,part.tobytes()
            if key not in cache:cache[key]=bank.nearest(feature(part))
            matches.append(cache[key])
        if any(x is None or x["distance"]>.12 or x["margin"]<.015 for x in matches):continue
        text=''.join(x["label"] for x in matches)
        if number_text(text) is not None:options.add(text)
    return next(iter(options)) if len(options)==1 else None

def stack_crop(rgb,x,y):
    x0,y0=x-60,y-10
    a=rgb[y0:y+10,x0:x+65].astype(np.int16)
    lo=a.min(2);hi=a.max(2);m=(lo>125)&(hi-lo<60)
    rr=[(int(l),int(r)) for l,r in runs(m.sum(0)>=2) if r-l>=3]
    if len(rr)<2:return None
    l,r=rr[0]
    if not (11<=r-l<=17 and 65<=m[:,l:r].sum()<=180 and 0<=rr[1][0]-r<=5):return None
    end=rr[1][1]
    for l2,r2 in rr[2:]:
        if l2-end>8:break
        end=r2
    return x0+r,y0,x0+end+3,y+10

def amount_crop(rgb,name):
    x,y,X,Y=AMOUNTS[name]
    a=rgb[y:Y,x:X].astype(np.int16)
    lo=a.min(2);hi=a.max(2);m=(lo>150)&(hi-lo<50)
    rr=[(int(l),int(r)) for l,r in runs(m.sum(0)>=2) if r-l>=2]
    if not rr:return None
    if name in ('bet_ur','bet_right'):
        rr=rr[::-1];end=rr[0][0];start=rr[0][1]
        for l,r in rr[1:]:
            if end-r>8:break
            end=l
        l,r=end,start
    else:
        l,r=rr[0]
        for L,R in rr[1:]:
            if L-r>8:break
            r=R
    if m[:,l:r].sum()<12:return None
    return x+max(0,l-2),y,x+min(X-x,r+2),Y

def read_amount(rgb,name,bank):
    b=stack_crop(rgb,*STACKS[name]) if name in STACKS else amount_crop(rgb,name)
    if b is None:return None,None
    x,y,X,Y=b
    gray=np.asarray(Image.fromarray(rgb[y:Y,x:X]).convert('L'),dtype=float)
    return read_glyphs(gray,bank),list(b)

def read_image(root,file,hashes):
    if Path(file).name!=file:raise ValueError("Invalid image filename")
    p=root/file
    if file in hashes and hashlib.sha256(p.read_bytes()).hexdigest()!=hashes[file]:raise ValueError("Source image hash mismatch: "+file)
    with Image.open(p) as im:
        if im.size!=SIZE:raise ValueError("Unsupported image dimensions: "+file)
        return np.asarray(im.convert("RGB"))

def evaluate(root,manifest,bank):
    results=[];images={}
    for item in manifest["lines"]:
        name=item["name"];name="bet_ul" if name=="showdown_payout_ul" else name
        if item["file"] not in images:images[item["file"]]=read_image(root,item["file"],manifest.get("image_sha256",{}))
        t=time.perf_counter();v,b=read_amount(images[item["file"]],name,bank)
        truth=item["label"]
        status=("absent_correct" if v is None else "false_positive") if truth is None else "unknown" if v is None else "correct" if v==truth else "incorrect"
        results.append({**item,"predicted":v,"automatic_box":b,"status":status,"ms":round((time.perf_counter()-t)*1000,3)})
    return {"scope":"Offline automatic text localization; labelled fields only, not complete-table or live accuracy",
            "scores":dict(Counter(x["status"] for x in results)),
            "median_ms":statistics.median(x["ms"] for x in results),"details":results}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("images",type=Path);p.add_argument("--model",type=Path,required=True);p.add_argument("--manifest",type=Path,required=True);p.add_argument("--output",type=Path,default=Path("automatic-font-report.json"));a=p.parse_args()
    model=json.loads(a.model.read_text(encoding="utf-8"));bank=GlyphBank(decode_library(model))
    report=evaluate(a.images,json.loads(a.manifest.read_text(encoding="utf-8")),bank)
    a.output.write_text(json.dumps(report,indent=2),encoding="utf-8");print(json.dumps({k:v for k,v in report.items() if k!="details"},indent=2))
if __name__=="__main__":main()
