"""Offline, supervised glyph diagnostic. Only completed saved images.

This measures character classification with oracle-assisted segmentation:
ground truth selects a segmentation with the right number of characters.
It is NOT a reader for unlabelled images or a runtime recognition path.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
from PIL import Image

THRESHOLDS=(.55,.65,.75)

def ink(a):
    lo,hi=np.percentile(a,[15,99])
    return np.clip((a-lo)/max(hi-lo,20),0,1)

def segment(a,t):
    g=ink(a)
    mask=g>=t
    runs=np.flatnonzero(np.diff(np.r_[False,mask.any(0),False])).reshape(-1,2)
    return [g[:,x:y] for x,y in runs if mask[:,x:y].sum()>=2]

def feature(g,binary=False):
    ys,xs=np.where(g>=.55)
    if not len(xs):
        return None
    crop=g[ys.min():ys.max()+1,xs.min():xs.max()+1]
    h,w=crop.shape
    v=np.asarray(Image.fromarray(np.uint8(crop*255)).resize((16,24),Image.Resampling.LANCZOS),dtype=float)/255
    if binary:
        v=(v>=.5).astype(float)
    return v,w/h

def evaluate(samples,binary=False):
    prepared=[]
    for group,label,patch,name in samples:
        options=[segment(patch,t) for t in THRESHOLDS]
        parts=next((o for o in options if len(o)==len(label)),None)
        prepared.append((group,label,parts,name))
    rows=[]
    for group,label,parts,name in prepared:
        library=[(c,feature(g,binary)) for other,text,segments,_ in prepared
                 if other!=group and segments is not None for c,g in zip(text,segments)]
        classes={c for c,v in library if v is not None}
        def classify(g):
            q=feature(g,binary)
            if q is None:
                return "?"
            scores={}
            for c,v in library:
                if v is None:
                    continue
                d=float(np.mean((q[0]-v[0])**2)+.15*abs(q[1]-v[1]))
                scores[c]=min(d,scores.get(c,float("inf")))
            return min(scores,key=scores.get) if scores else "?"
        prediction="".join(map(classify,parts)) if parts is not None else None
        rows.append({"group":group,"name":name,"label":label,"prediction":prediction,
                     "segmented":parts is not None,"unseen_classes":sorted(set(label)-classes),
                     "correct_characters":sum(a==b for a,b in zip(label,prediction or "")),
                     "evaluated_characters":len(label) if parts is not None else 0})
    return {"lines":len(rows),"segmented_lines":sum(r["segmented"] for r in rows),
            "matching_lines":sum(r["prediction"]==r["label"] for r in rows),
            "correct_characters":sum(r["correct_characters"] for r in rows),
            "evaluated_characters":sum(r["evaluated_characters"] for r in rows),
            "lines_with_unseen_classes":sum(bool(r["unseen_classes"]) for r in rows),
            "details":rows}

def read_samples(root,manifest):
    samples=[]
    for item in manifest["lines"]:
        file=item["file"]
        if Path(file).name!=file or not item["label"] or not item["group"]:
            raise ValueError("Expected local image filename, label and group")
        with Image.open(root/file) as im:
            if "frame_crop" in item:
                box=item["frame_crop"]
                if not (0<=box[0]<box[2]<=im.width and 0<=box[1]<box[3]<=im.height):
                    raise ValueError("Frame crop outside image")
                im=im.crop(box).resize((1536,709))
            x0,y0,x1,y1=item["box"]
            if not (0<=x0<x1<=im.width and 0<=y0<y1<=im.height):
                raise ValueError("Line crop outside image")
            patch=np.asarray(im.crop((x0,y0,x1,y1)).convert("L"),dtype=float)
            if item.get("dark_ink"):
                patch=255-patch
        samples.append((item["group"],item["label"],patch,item.get("name",file)))
    return samples

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("images",type=Path)
    p.add_argument("manifest",type=Path)
    p.add_argument("--output",type=Path,default=Path("glyph-audit.json"))
    args=p.parse_args()
    samples=read_samples(args.images,json.loads(args.manifest.read_text(encoding="utf-8")))
    if len({s[0] for s in samples})<2:
        p.error("Provide at least two independent image groups.")
    report={"scope":"oracle-assisted segmentation, leave-image-group-out; not automatic recognition accuracy",
            "binary":evaluate(samples,True),"grayscale":evaluate(samples,False)}
    args.output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:{a:b for a,b in v.items() if a!="details"} if isinstance(v,dict) else v for k,v in report.items()},indent=2))
if __name__=="__main__":
    main()
