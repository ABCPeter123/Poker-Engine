"""Completed-image crop evaluation, not a screen or game integration.

Train only on explicitly labelled historical crops. Test an entire image/hand
group without looking at its labels during prediction. Regions are manually
localized, so this does not measure automatic full-screen localization.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import time
import numpy as np
from PIL import Image
from glyph_audit import feature, segment, read_samples
from amount_text import number_text

TRAIN_THRESHOLDS=(.55,.65,.75)
TEST_THRESHOLDS=(.45,.50,.55,.60,.65,.70,.75,.80)


def nearest(query, library):
    if query is None:
        return None
    scores={}
    for label,entry in library:
        if entry is None:
            continue
        distance=float(np.mean((query[0]-entry[0])**2)+.15*abs(query[1]-entry[1]))
        scores[label]=min(scores.get(label,float("inf")),distance)
    ordered=sorted((score,label) for label,score in scores.items())
    if len(ordered)<2:
        return None
    return {"label":ordered[0][1],"distance":ordered[0][0],
            "margin":ordered[1][0]-ordered[0][0]}


class GlyphBank:
    """Compile templates once, vectorize exact per-class nearest distances."""
    def __init__(self,library):
        entries=[(label,item) for label,item in library if item is not None]
        self.labels=sorted({label for label,_ in entries})
        self.pixels=np.asarray([item[0].ravel() for _,item in entries],dtype=np.float64).reshape(-1,384)
        self.aspects=np.asarray([item[1] for _,item in entries],dtype=np.float64)
        self.indices=[np.array([i for i,(c,_) in enumerate(entries) if c==label],dtype=int) for label in self.labels]
    def nearest(self,query):
        if query is None or len(self.labels)<2:
            return None
        pixels,aspect=query
        delta=self.pixels-pixels.ravel()
        distances=np.mean(delta*delta,axis=1)+.15*np.abs(self.aspects-aspect)
        ordered=sorted((float(distances[idx].min()),label) for label,idx in zip(self.labels,self.indices))
        return {"label":ordered[0][1],"distance":ordered[0][0],"margin":ordered[1][0]-ordered[0][0]}


def fit_amount(samples):
    library=[]
    for _,label,patch,_ in samples:
        parts=next((p for t in TRAIN_THRESHOLDS if len(p:=segment(patch,t))==len(label)),None)
        if parts is not None:
            library.extend((c,feature(g)) for c,g in zip(label,parts))
    return library


def predict_amount(patch, library):
    """Unknown character count: competing segmentations are evidence only."""
    readings=[]
    bank=library if isinstance(library,GlyphBank) else GlyphBank(library)
    feature_cache={}
    for t in TEST_THRESHOLDS:
        parts=segment(patch,t)
        if not parts or len(parts)>16:
            continue
        matches=[]
        for part in parts:
            key=(part.shape,part.tobytes())
            if key not in feature_cache:
                feature_cache[key]=bank.nearest(feature(part))
            matches.append(feature_cache[key])
        if any(m is None for m in matches):
            continue
        text="".join(m["label"] for m in matches)
        distance=max(m["distance"] for m in matches)
        margin=min(m["margin"] for m in matches)
        valid=number_text(text) is not None
        readings.append({"threshold":t,"text":text,"max_distance":distance,
            "min_margin":margin,"eligible":valid and distance<=.12 and margin>=.015})
    choices={r["text"] for r in readings if r["eligible"]}
    return {"candidate":next(iter(choices)) if len(choices)==1 else None,
            "reason":"unique candidate" if len(choices)==1 else "conflicting segmentations" if choices else "insufficient evidence",
            "readings":readings,"verified":False}


def amount_audit(samples):
    groups={s[0] for s in samples}
    libraries={group:GlyphBank(fit_amount([s for s in samples if s[0]!=group])) for group in groups}
    rows=[]
    for group,label,patch,name in samples:
        library=libraries[group]
        start=time.perf_counter()
        result=predict_amount(patch,library)
        result.update(group=group,name=name,expected=label,
            unseen_classes=sorted(set(label)-set(library.labels)),
            elapsed_ms=round(1000*(time.perf_counter()-start),3))
        rows.append(result)
    return summarize(rows)


def card_feature(im,binary):
    a=np.asarray(im.convert("RGB"),dtype=float)
    r,g,b=np.moveaxis(a,-1,0)
    gray=np.asarray(im.convert("L"),dtype=float)
    color=(r>g+40)&(r>b+35)&(g<r*.75)&(b<r*.75)
    gold=(r>140)&(g>95)&(b<120)&(r-g<130)
    neutral=(np.ptp(a,axis=-1)<55)&(gray<180)
    v=np.where((color|neutral)&~gold,np.clip((230-gray)/180,0,1),0)
    if binary:
        v=(v>.45).astype(float)
    y,x=np.where(v>.25)
    if not len(y):
        return None
    v=v[y.min():y.max()+1,x.min():x.max()+1]
    h,w=v.shape
    v=np.asarray(Image.fromarray(np.uint8(v*255)).resize((16,24),Image.Resampling.LANCZOS),dtype=float)/255
    if binary:
        v=(v>=.5).astype(float)
    return v,w/h


def card_audit(samples,binary):
    # No overlapping-hand group can contribute templates to its own test.
    prepared=[(group,label,card_feature(rank,binary),card_feature(suit,binary),name)
              for group,label,rank,suit,name in samples]
    rows=[]
    for group,label,rank,suit,name in prepared:
        matches=[]
        for i,q in enumerate((rank,suit)):
            library=[(other[i],entry) for g,other,r,s,_ in prepared if g!=group
                     for entry in [(r,s)[i]]]
            matches.append(nearest(q,library))
        partial=[m["label"] if m and m["distance"]<=.15 and m["margin"]>=.025 else None for m in matches]
        raw="".join(m["label"] if m else "?" for m in matches)
        rows.append({"group":group,"name":name,"expected":label,
                     "candidate":"".join(partial) if all(partial) else None,
                     "rank_candidate":partial[0],"suit_candidate":partial[1],"nearest":raw,
                     "rank_evidence":matches[0],"suit_evidence":matches[1]})
    result=summarize(rows)
    result.update(rank_correct=sum(r["rank_candidate"]==r["expected"][0] for r in rows),
                  suit_correct=sum(r["suit_candidate"]==r["expected"][1] for r in rows),
                  rank_nearest_correct=sum(r["nearest"][0]==r["expected"][0] for r in rows),
                  suit_nearest_correct=sum(r["nearest"][1]==r["expected"][1] for r in rows),
                  nearest_complete_correct=sum(r["nearest"]==r["expected"] for r in rows))
    return result


def summarize(rows):
    counts=Counter("missing" if r["candidate"] is None else
                   "correct" if r["candidate"]==r["expected"] else "incorrect" for r in rows)
    durations=[r["elapsed_ms"] for r in rows if "elapsed_ms" in r]
    return {"total":len(rows),**{k:counts[k] for k in ("correct","missing","incorrect")},
            "median_ms":statistics.median(durations) if durations else None,"details":rows}


def read_card_samples(root,manifest):
    samples=[]
    for item in manifest["cards"]:
        file=item["file"]
        label=item["label"]
        if Path(file).name!=file or len(label)!=2 or label[0] not in "23456789TJQKA" or label[1] not in "cdhs" or not item["group"]:
            raise ValueError("Invalid labelled card crop")
        with Image.open(root/file) as im:
            box=item["frame_crop"]
            if not 0<=box[0]<box[2]<=im.width or not 0<=box[1]<box[3]<=im.height:
                raise ValueError("Frame crop outside image")
            im=im.convert("RGB").crop(box).resize((1536,709))
            patches=[]
            for key in ("rank_box","suit_box"):
                x0,y0,x1,y1=item[key]
                if not (0<=x0<x1<=im.width and 0<=y0<y1<=im.height):
                    raise ValueError("Glyph crop outside image")
                patches.append(im.crop((x0,y0,x1,y1)))
        samples.append((item["group"],label,*patches,item["name"]))
    return samples


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("images",type=Path)
    p.add_argument("manifest",type=Path)
    p.add_argument("--kind",choices=("amount","card"),required=True)
    p.add_argument("--output",type=Path,default=Path("automatic-glyph-report.json"))
    args=p.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.kind=="amount":
        samples=read_samples(args.images,manifest)
    else:
        samples=read_card_samples(args.images,manifest)
    if len({s[0] for s in samples})<2:
        p.error("At least two independent labelled groups are required")
    report={"scope":"manually localized saved crops, held-out groups; not full-frame OCR",
            "kind":args.kind}
    if args.kind=="amount":
        report["automatic_segmentation"]=amount_audit(samples)
    else:
        report["binary"]=card_audit(samples,True)
        report["grayscale"]=card_audit(samples,False)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps({k:{a:b for a,b in v.items() if a!="details"} if isinstance(v,dict) else v
                      for k,v in report.items()},indent=2))

if __name__=="__main__":
    main()
