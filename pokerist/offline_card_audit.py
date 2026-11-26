"""Held-hand-out rank/suit and card-presence audit, saved images only."""
import argparse,json,math
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from offline_font_review import read_image
from offline_ocr_fallback import board_rank_fallback
from review import RANKS, SUITS, match
from ocr_runtime import resolve_tesseract

BOARD_X=(547,637,726,815,905)

def glyph(mask):
    y,x=np.where(mask)
    if len(x)<15:return None
    crop=mask[y.min():y.max()+1,x.min():x.max()+1]
    h,w=crop.shape
    return np.asarray(Image.fromarray(np.uint8(crop*255)).resize((16,24),Image.Resampling.LANCZOS),dtype=float)/255,w/h

def board_features(a,index):
    x=BOARD_X[index];body=a[241:354,x:x+83].astype(np.int16)
    lo=body.min(2);hi=body.max(2);face=(lo>132)&(hi-lo<40)
    if face.mean()<.30 or (face.mean(0)>.25).sum()<50:return None
    def mask(b):
        r,g,bl=np.moveaxis(b.astype(np.int16),-1,0)
        red=(r>95)&(r-g>45)&(r-bl>35)&(g<r*.63)
        black=(b.max(2)<115)&(b.max(2).astype(int)-b.min(2)<45)
        return red|black
    rank=mask(a[244:281,x+4:x+34]);suit=mask(a[283:309,x+4:x+30])
    def isolate(m,gap):
        cols=np.flatnonzero(m.any(0))
        if not len(cols):return m
        end=cols[0]
        for c in cols[1:]:
            if c-end>gap:break
            end=c
        return m[:,:end+1]
    return glyph(isolate(rank,4)),glyph(isolate(suit,2))

def warped(im,x,y,angle):
    a=math.radians(angle);c,s=math.cos(a),math.sin(a)
    return np.asarray(im.transform((40,77),Image.Transform.AFFINE,(c,-s,x,s,c,y),resample=Image.Resampling.BILINEAR))

def hero_features(im,slot):
    """Select a calibrated face geometry by pixel evidence, without rank labels."""
    geoms=[(807,468,0),(807,453,0)] if slot==0 else [(854,462,10),(853,461,10),(841,468,0),(842,453,0)]
    candidates=[]
    def mask(b):
        r,g,bl=np.moveaxis(b.astype(np.int16),-1,0)
        return ((r>70)&(r-g>32)&(r-bl>30)&(g<r*.69))|((b.max(2)<110)&(b.max(2).astype(int)-b.min(2)<45))
    def isolate(m,gap):
        cols=np.flatnonzero(m.any(0))
        if not len(cols):return m
        end=cols[0]
        for c in cols[1:]:
            if c-end>gap:break
            end=c
        return m[:,:end+1]
    for x,y,ang in geoms:
        p=warped(im,x,y,ang).astype(np.int16)
        r,g,b=np.moveaxis(p,-1,0);lo=p.min(2);hi=p.max(2)
        face=(lo>120)&(hi-lo<45)
        gold=(r>120)&(g>80)&(b<110)&(r-b>50)&(g-b>35)
        edge=(face|gold)[:5,5:30].mean()
        left=(face|gold)[5:68,:4].mean()
        interior=face[5:70,3:34].mean()
        if edge<.5 or left<.5 or interior<.35:continue
        f=(glyph(isolate(mask(p[4:40,4:33]),4)),glyph(isolate(mask(p[42:68,3:29]),2)))
        if any(v is None for v in f):continue
        candidates.append((edge+left+interior,f))
    return max(candidates,key=lambda v:v[0])[1] if candidates else None

def enclosed_loops(feature):
    """Count four-connected background regions fully enclosed by the glyph."""
    if feature is None:return None
    a=np.pad(feature[0]>=.5,1,constant_values=False)
    bg=~a;seen=np.zeros_like(bg);num=0
    for y,x in zip(*np.where(bg)):
        if seen[y,x]:continue
        stack=[(y,x)];seen[y,x]=True;n=0;edge=False
        while stack:
            j,i=stack.pop();n+=1
            edge|=j==0 or i==0 or j==a.shape[0]-1 or i==a.shape[1]-1
            for J,I in ((j-1,i),(j+1,i),(j,i-1),(j,i+1)):
                if 0<=J<a.shape[0] and 0<=I<a.shape[1] and bg[J,I] and not seen[J,I]:
                    seen[J,I]=True;stack.append((J,I))
        if not edge and n>=4:num+=1
    return num

def rank_candidate(q,bank):
    candidate=nearest(q,bank)
    # The calibrated 8 has two loops. Veto, never promote a runner-up.
    if candidate=="8" and enclosed_loops(q)!=2:return None
    return candidate

def nearest(q,bank):
    if q is None:return None
    p,aspect=q;s={}
    for label,f in bank:
        if f is None:continue
        d=float(np.mean((p-f[0])**2)+.15*abs(aspect-f[1]))
        s[label]=min(s.get(label,float("inf")),d)
    ordered=sorted((v,k) for k,v in s.items())
    if len(ordered)<2 or ordered[0][0]>.15 or ordered[1][0]-ordered[0][0]<.025:return None
    return ordered[0][1]

def legacy_candidate(q,kind):
    if q is None:return None
    mask=np.asarray(Image.fromarray(np.uint8(q[0]*255)).resize((12,16)))>=128
    label,_=match(mask,RANKS if kind=='rank' else SUITS,.18 if kind=='rank' else .25)
    if kind=='rank' and label=='8' and enclosed_loops(q)!=2:return None
    return label

def audit(root,manifest,*,fallback=False):
    samples=[];images={}
    exe=resolve_tesseract()[0] if fallback else None
    for row in manifest["frames"]:
        a=read_image(root,row["file"],manifest.get("image_sha256",{}))
        if fallback:images[row["file"]]=Image.fromarray(a)
        for i,label in enumerate(row["board"]):
            samples.append((row["group"],row["file"],"board",i,label,board_features(a,i)))
        if "hero" in row:
            im=Image.fromarray(a)
            for i,label in enumerate(row["hero"]):
                samples.append((row["group"],row["file"],"hero",i,label,hero_features(im,i)))
    rows=[]
    for group,file,kind,i,label,f in samples:
        others=[(c,v) for g,_,_,_,c,v in samples if g!=group and c and v]
        banks=[[(c[j],v[j]) for c,v in others] for j in (0,1)]
        rank,suit=(rank_candidate(f[0],banks[0]),nearest(f[1],banks[1])) if f else (None,None)
        baseline=rank+suit if rank and suit else None
        sources={"rank":"held-out glyph" if rank else None,"suit":"held-out glyph" if suit else None}
        if fallback and f:
            if rank is None:
                rank=legacy_candidate(f[0],"rank")
                if rank:sources["rank"]="legacy template"
            if suit is None:
                suit=legacy_candidate(f[1],"suit")
                if suit:sources["suit"]="legacy template"
            if rank is None and kind=="board":
                rank=board_rank_fallback(images[file],BOARD_X[i],exe)
                if rank=="8" and enclosed_loops(f[0])!=2:rank=None
                if rank:sources["rank"]="line OCR fallback"
        candidate=rank+suit if rank and suit else None
        status=("absent_correct" if f is None else "false_presence") if label is None else "unknown" if not candidate else "correct" if label==candidate else "incorrect"
        rows.append({"group":group,"file":file,"kind":kind,"slot":i,"expected":label,"rank":rank,"suit":suit,"candidate":candidate,"baseline":baseline,"sources":sources,"status":status})
    def stats(subset):
        return {"scores":dict(Counter(r["status"] for r in subset)),
                "rank_correct":sum(r["expected"] is not None and r["rank"]==r["expected"][0] for r in subset),
                "suit_correct":sum(r["expected"] is not None and r["suit"]==r["expected"][1] for r in subset),
                "present_cards":sum(r["expected"] is not None for r in subset)}
    return {"scope":"Saved-image held-hand-out board and calibrated hero position audit; geometry and loop veto developed on these images, not independent full-screen or live validation",
            "fallback_enabled":fallback,"ocr_available":bool(exe),**stats(rows),"by_kind":{k:stats([r for r in rows if r["kind"]==k]) for k in ("board","hero")},
            "details":rows}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("images",type=Path);p.add_argument("manifest",type=Path);p.add_argument("--output",type=Path,default=Path("offline-card-report.json"));p.add_argument("--fallback",action="store_true");a=p.parse_args();r=audit(a.images,json.loads(a.manifest.read_text(encoding="utf-8")),fallback=a.fallback);a.output.write_text(json.dumps(r,indent=2),encoding="utf-8");print(json.dumps({k:v for k,v in r.items() if k!="details"},indent=2))
if __name__=="__main__":main()
