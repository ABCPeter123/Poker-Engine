"""Held-hand-out rank/suit and card-presence audit, saved images only."""
import argparse,json
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
from offline_font_review import read_image

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

def audit(root,manifest):
    samples=[]
    for row in manifest["frames"]:
        a=read_image(root,row["file"],manifest.get("image_sha256",{}))
        for i,label in enumerate(row["board"]):samples.append((row["group"],row["file"],i,label,board_features(a,i)))
    rows=[]
    for group,file,i,label,f in samples:
        others=[(c,v) for g,_,_,c,v in samples if g!=group and c and v]
        banks=[[(c[j],v[j]) for c,v in others] for j in (0,1)]
        rank,suit=(nearest(q,b) for q,b in zip(f,banks)) if f else (None,None)
        candidate=rank+suit if rank and suit else None
        status=("absent_correct" if f is None else "false_presence") if label is None else "unknown" if not candidate else "correct" if label==candidate else "incorrect"
        rows.append({"group":group,"file":file,"slot":i,"expected":label,"rank":rank,"suit":suit,"candidate":candidate,"status":status})
    return {"scope":"Held-hand-out automatic board-corner audit; no hero-card or live accuracy claim",
            "scores":dict(Counter(r["status"] for r in rows)),
            "rank_correct":sum(r["expected"] is not None and r["rank"]==r["expected"][0] for r in rows),
            "suit_correct":sum(r["expected"] is not None and r["suit"]==r["expected"][1] for r in rows),
            "present_cards":sum(r["expected"] is not None for r in rows),"details":rows}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("images",type=Path);p.add_argument("manifest",type=Path);p.add_argument("--output",type=Path,default=Path("offline-card-report.json"));a=p.parse_args();r=audit(a.images,json.loads(a.manifest.read_text(encoding="utf-8")));a.output.write_text(json.dumps(r,indent=2),encoding="utf-8");print(json.dumps({k:v for k,v in r.items() if k!="details"},indent=2))
if __name__=="__main__":main()
