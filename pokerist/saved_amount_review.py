"""Additional OCR evidence for completed-hand saved image review.

Each pass sees the same pixels. Agreement is a heuristic, not proof.
Do not use these results as verified balances.
"""
import io
import math
import re
import subprocess
from copy import deepcopy
import numpy as np
from PIL import Image

THRESHOLDS=(140,115,160)

def prepare_line(image,box,kind,threshold):
    a=np.asarray(image.crop(box).convert("RGB"),dtype=np.int16)
    mask=(a.min(2)>threshold)&(np.ptp(a,axis=2)<55)
    h,w=mask.shape
    if kind=="stack":
        density=mask[:,w//5:w-w//5].sum(1)
        bands=np.flatnonzero(np.diff(np.r_[False,density>=3,False])).reshape(-1,2)
        if len(bands):
            y0,y1=max(bands,key=lambda t:(density[t[0]:t[1]].sum(),t[1]-t[0]))
            mask[:y0]=False;mask[y1:]=False
        runs=np.flatnonzero(np.diff(np.r_[False,mask.sum(0)>=2,False])).reshape(-1,2)
        if len(runs)>1:
            x,y=map(int,runs[0])
            if 10<=y-x<=18 and 1<=int(runs[1,0])-y<=8:
                mask[:,:y]=False
    ys,xs=np.where(mask)
    if not len(xs):
        return None
    mask=mask[ys.min():ys.max()+1,xs.min():xs.max()+1]
    crop=Image.fromarray(np.uint8(255-255*mask)).resize(
        (mask.shape[1]*4,mask.shape[0]*4),Image.Resampling.NEAREST)
    canvas=Image.new("L",(crop.width+32,crop.height+32),255)
    canvas.paste(crop,(16,16))
    return canvas

def scan_line(image,executable,box,kind,threshold):
    canvas=prepare_line(image,box,kind,threshold)
    if canvas is None:
        return {"threshold":threshold,"raw":"","confidence":None}
    try:
        with io.BytesIO() as buf:
            canvas.save(buf,format="PNG")
            proc=subprocess.run([executable,"stdin","stdout","--psm","7","tsv"],
                input=buf.getvalue(),capture_output=True,timeout=4,check=True)
        rows=[]
        for line in proc.stdout.decode("utf-8",errors="replace").splitlines()[1:]:
            c=line.split("\t",11)
            if len(c)==12 and c[0]=="5" and c[11].strip():
                confidence=float(c[10])
                if math.isfinite(confidence):
                    rows.append((c[11].strip(),confidence))
        return {"threshold":threshold,"raw":" ".join(row[0] for row in rows),
                "confidence":round(min(row[1] for row in rows),1) if rows else None}
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        return {"threshold":threshold,"raw":"","confidence":None,"error":str(exc)[:300]}

def strict_amount(text,parse):
    # No guessing O/0, omitted digits, or malformed digit grouping.
    value=str(text).strip().upper()
    if not re.fullmatch(r"(?:[0-9]+(?:\.[0-9]+)?[KM]|[0-9]+|[0-9]{1,3}(?: +[0-9]{3})+)",value):
        return None
    candidate=parse(value)
    if not candidate or not math.isfinite(candidate["value"]) or candidate["value"]>2**53-1:
        return None
    return candidate

def add_evidence(primary,passes,parse):
    result=deepcopy(primary)
    observations=[]
    for p in passes:
        candidate=strict_amount(p.get("raw",""),parse)
        observations.append({**p,"candidate":candidate})
    result["saved_line_evidence"]=observations
    valid=[o for o in observations if o["candidate"] is not None]
    def identity(c):
        return c["value"],bool(c.get("approximate"))
    choices={identity(o["candidate"]) for o in valid}
    base=strict_amount(primary.get("raw",""),parse)
    existing=primary.get("candidate")
    if existing:
        choices.add(identity(existing))
    if base:
        choices.add(identity(base))
    # Do not alter original accepted candidates: flag disagreements for manual review.
    if len(choices)>1:
        result["saved_line_status"]="conflicting readings"
        return result
    eligible=[o for o in valid if isinstance(o.get("confidence"),(int,float)) and o["confidence"]>=75]
    if existing:
        result["saved_line_status"]="original candidate retained"
    elif len(choices)==1 and len(eligible)>=2 and base is not None:
        result["candidate"]={**eligible[0]["candidate"],"verified":False,
            "source":"saved-line agreement","ocr_confidence":min(o["confidence"] for o in eligible)}
        result["saved_line_status"]="agreement candidate"
    else:
        result["saved_line_status"]="insufficient agreement"
    return result

def add_saved_amount_evidence(image,executable,regions,numbers,parse):
    if not executable:
        return numbers
    # Bound work: only six fields, three passes each, with per-process timeout.
    results={}
    for key,box in regions.items():
        primary=numbers.get(key,{})
        kind="pot" if key=="pot" else "stack"
        passes=[scan_line(image,executable,box,kind,t) for t in THRESHOLDS]
        results[key]=add_evidence(primary,passes,parse)
    return results
