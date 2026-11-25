"""Adaptive text-line extraction inside broad, seat-relative search areas.

Coordinates define search areas, not exact digit locations. Never turn an
unreadable or ambiguous label into zero. All returned amounts are candidates.
"""
import re
from collections import OrderedDict
from native_ocr import recognize_tsv
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image

SCALE=4
PITCH=320
PAD=12

def text_lines(words):
    """Cluster OCR words by baseline, independent of sparse OCR block IDs."""
    lines=[]
    for word in sorted(words,key=lambda w:(w["y"]+w["h"]/2,w["x"])):
        center=word["y"]+word["h"]/2
        matches=[line for line in lines if abs(center-line[0])<=max(5,.45*word["h"])]
        if matches:
            line=min(matches,key=lambda l:abs(center-l[0]))
            line[1].append(word)
        else:
            lines.append([center,[word]])
    return [sorted(line[1],key=lambda w:w["x"]) for line in lines]

def select_amount(words, parse, threshold=75):
    lines=text_lines(words)
    raw=" / ".join(" ".join(w["text"] for w in line) for line in lines)
    result={"raw":raw,"candidate":None,"ocr_confidence":round(min((w["confidence"] if np.isfinite(w["confidence"]) else -1 for w in words),default=-1),1),"text_bounds":None}
    candidates=[]
    plausible=[]
    for line in lines:
        tokens=[w["text"].strip() for w in line]
        # Parse the complete line, including a detached K/M suffix.
        candidate=parse(" ".join(tokens))
        if not candidate:
            continue
        plausible.append(candidate["value"])
        if any(not np.isfinite(w["confidence"]) or w["confidence"]<threshold for w in line):
            continue
        confidence=round(min(w["confidence"] for w in line),1)
        bounds=[min(w["x"] for w in line),min(w["y"] for w in line),
                max(w["x"]+w["w"] for w in line),max(w["y"]+w["h"] for w in line)]
        candidates.append((candidate,confidence,bounds))
    # Multiple plausible numeric lines are ambiguous. Do not choose a stack
    # from a nearby bet, or vice versa.
    if len(candidates)==1 and len(plausible)==1:
        candidate,confidence,bounds=candidates[0]
        candidate["ocr_confidence"]=confidence
        result.update(candidate=candidate,ocr_confidence=confidence,text_bounds=bounds)
    return result

def stack_line_mask(a):
    # Isolate the dense amount stripe before inspecting the leading emblem.
    # Preserve full horizontal width for large amounts.
    a=np.asarray(a,dtype=np.int16)
    r,g,b=np.moveaxis(a,-1,0)
    lo=np.minimum(np.minimum(r,g),b)
    hi=np.maximum(np.maximum(r,g),b)
    mask=(lo>140)&(hi-lo<55)
    h,w=mask.shape
    density=mask[:,w//5:w-w//5].sum(1)
    bands=np.flatnonzero(np.diff(np.r_[False,density>=3,False])).reshape(-1,2)
    if not len(bands):
        return mask
    y0,y1=max(bands,key=lambda t:(density[t[0]:t[1]].sum(),t[1]-t[0]))
    mask[:y0]=False
    mask[y1:]=False
    return mask

def numeric_mask(a,kind):
    """Separate white digit ink from chip artwork. All readings stay candidates."""
    a=np.asarray(a,dtype=np.int16)
    r,g,b=np.moveaxis(a,-1,0)
    lo=np.minimum(np.minimum(r,g),b)
    hi=np.maximum(np.maximum(r,g),b)
    spread=hi-lo
    mask=(lo>112)&(spread<45)
    if kind=="stack":
        mask=stack_line_mask(a)
        # Stack labels have a leading chip emblem. Remove a separated,
        # emblem-sized first run only within the expected text line.
        runs=np.flatnonzero(np.diff(np.r_[False,mask.sum(0)>=2,False])).reshape(-1,2)
        if len(runs)>1:
            x,y=map(int,runs[0])
            gap=int(runs[1,0])-y
            if 10<=y-x<=18 and 1<=gap<=8:
                mask[:,:y]=False
    elif kind=="bet":
        # Colored chips have saturated bodies and white markings.
        # Remove their full horizontal span, not just the colored pixels.
        sat=(spread>85)&(hi>145)
        cols=np.flatnonzero(sat.sum(0)>=5)
        if 8<=len(cols)<=36 and cols[-1]-cols[0]<=40:
            mask[:,max(0,int(cols[0])-6):min(mask.shape[1],int(cols[-1])+7)]=False
    return mask

def prepared_region_mask(image,box,kind):
    a=np.asarray(image.crop(box).convert("RGB"),dtype=np.int16)
    r,g,b=np.moveaxis(a,-1,0)
    return ((r>145)&(g>115)&(b<np.minimum(r,g)-35)) if kind=="status" else numeric_mask(a,kind)


class RegionOCRCache:
    """Bounded cache of exact prepared OCR masks, never approximate pixel matches."""
    def __init__(self):
        self.entries={}
        self.hits=0
        self.misses=0
        self.history=OrderedDict()
        self.history_limit=256

    def scan(self,image,exe,regions,*,unrestricted=False):
        rows={}
        changed=[]
        keys={}
        masks={}
        for entry in regions:
            key,box,kind=entry
            mask=prepared_region_mask(image,box,kind)
            identity=(key,box,kind,unrestricted)
            signature=(mask.shape,mask.tobytes())
            old=self.entries.get(identity)
            if old is not None and old[0]==signature:
                rows[key]=old[1]
                self.hits+=1
            elif (identity,signature) in self.history:
                history_key=(identity,signature)
                value=self.history[history_key]
                self.history.move_to_end(history_key)
                self.entries[identity]=(signature,value)
                rows[key]=value
                self.hits+=1
            elif not mask.any():
                rows[key]=[]
                self.entries[identity]=(signature,[])
                self.hits+=1
            else:
                changed.append(entry)
                masks[key]=mask
                keys[key]=(identity,signature)
                self.misses+=1
        if changed:
            new,error=scan_regions(image,exe,changed,unrestricted=unrestricted,persistent=True,prepared_masks=masks)
            if error:
                # Failed scans cannot keep previous values for changed regions.
                for identity,_ in keys.values():
                    self.entries.pop(identity,None)
                return rows,error
            for key,(identity,signature) in keys.items():
                value=new.get(key,[])
                self.entries[identity]=(signature,value)
                rows[key]=value
                if value:
                    history_key=(identity,signature)
                    self.history[history_key]=value
                    self.history.move_to_end(history_key)
                    while len(self.history)>self.history_limit:
                        self.history.popitem(last=False)
        return rows,None


def scan_regions(image, executable, regions, *, unrestricted=False, cache=None,persistent=False,prepared_masks=None):
    """One OCR pass across variable-width search regions; retain source boxes."""
    if not executable:
        return {}, "Tesseract unavailable"
    if cache is not None:
        return cache.scan(image,executable,regions,unrestricted=unrestricted)
    # Separate numeric and language OCR. Applying a numeric whitelist to
    # status labels would silently destroy words such as Call and All-in.
    numeric=[entry for entry in regions if entry[2]!="status"]
    status=[entry for entry in regions if entry[2]=="status"]
    if numeric and status:
        a,ea=scan_regions(image,executable,numeric,unrestricted=unrestricted,persistent=persistent,prepared_masks=prepared_masks)
        b,eb=scan_regions(image,executable,status,unrestricted=unrestricted,persistent=persistent,prepared_masks=prepared_masks)
        return {**a,**b}, "; ".join(x for x in (ea,eb) if x) or None
    if not regions:
        return {},None
    width=max((box[2]-box[0])*SCALE+2*PAD for _,box,_ in regions)
    canvas=Image.new("L",(width,PITCH*len(regions)),255)
    for i,(key,box,kind) in enumerate(regions):
        mask=prepared_masks[key] if prepared_masks is not None else prepared_region_mask(image,box,kind)
        crop=Image.fromarray(np.uint8(255-255*mask))
        crop=crop.resize((crop.width*SCALE,crop.height*SCALE),Image.Resampling.NEAREST)
        if crop.height+2*PAD>PITCH:
            raise ValueError("OCR region exceeds row height")
        canvas.paste(crop,(PAD,i*PITCH+PAD))
    try:
        tsv=recognize_tsv(canvas,executable,6 if unrestricted else 11,
                          "0123456789.,KkMm" if numeric and not unrestricted else "",
                          persistent=persistent)
        rows={key:[] for key,_,_ in regions}
        for line in tsv.splitlines()[1:]:
            cols=line.split("\t",11)
            if len(cols)!=12 or cols[0]!="5" or not cols[11].strip():
                continue
            x,y,w,h=map(int,cols[6:10])
            idx=(y+h//2)//PITCH
            if not 0<=idx<len(regions):
                continue
            key,box,_=regions[idx]
            rows[key].append({"text":cols[11].strip(),"confidence":float(cols[10]),
                "x":box[0]+(x-PAD)/SCALE,"y":box[1]+(y-idx*PITCH-PAD)/SCALE,
                "w":w/SCALE,"h":h/SCALE})
        return rows,None
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        return {},str(exc)

def reconcile_amount(primary, alternate, parse):
    """An alternate scan can rescue rejected confidence, not disagreements."""
    if primary.get("candidate") is not None:
        return primary
    result=dict(primary)
    result["alternate_raw"]=alternate.get("raw","")
    result["alternate_confidence"]=alternate.get("ocr_confidence")
    # Require both entire strings to parse to the same amount and precision.
    a=parse(primary.get("raw",""))
    b=parse(alternate.get("raw",""))
    if not a or not b or (a["value"],a.get("approximate"),a.get("display_step"))!=(b["value"],b.get("approximate"),b.get("display_step")):
        return result
    if alternate.get("candidate") is not None:
        result["candidate"]=dict(alternate["candidate"],confirmed_by_two_passes=True)
        result["text_bounds"]=alternate.get("text_bounds")
        result["ocr_confidence"]=alternate.get("ocr_confidence")
    return result
