"""Experimental visual evidence for saved Pokerist screenshots, not a live tracker."""
import re
import subprocess
import tempfile
from pathlib import Path
from PIL import Image
import numpy as np

# Layout calibrated only for the supplied 1536x709 five-seat frame.
# Each seat has a profile base, avatar, label, and possible bet/label region.
SEATS = {
    "hero": {"bar":(652,526,795,568),"avatar":(674,420,768,527),"label":(682,568,771,611),"bet":(620,366,800,420)},
    "left": {"bar":(278,389,416,434),"avatar":(301,296,389,389),"label":(305,437,398,481),"bet":(415,352,546,414)},
    "upper_left": {"bar":(493,100,634,145),"avatar":(515,20,599,100),"label":(526,144,589,183),"bet":(582,180,708,237)},
    "upper_right": {"bar":(904,99,1043,144),"avatar":(931,20,1017,100),"label":(946,144,1030,183),"bet":(825,180,951,237)},
    "right": {"bar":(1118,389,1264,435),"avatar":(1143,285,1238,389),"label":(1149,437,1245,481),"bet":(968,352,1115,414)}
}
def pixels(image,box):
    return np.asarray(image.crop(box).convert("RGB"),dtype=np.int16)

def colors(a):
    r,g,b=np.moveaxis(a,-1,0)
    hi=np.maximum(np.maximum(r,g),b)
    lo=np.minimum(np.minimum(r,g),b)
    bright=(hi>165)&(hi-lo>75)
    return {
        "red":bright&(r>g+35)&(r>b+35),
        "green":bright&(g>r+25)&(g>b+20),
        "amber":bright&(r>170)&(g>110)&(b<np.minimum(r,g)-50),
    }

def bar_evidence(a):
    masks=colors(a)
    counts={k:int(v.sum()) for k,v in masks.items()}
    # Reject isolated saturated pixels. Require at least two distinct
    # horizontal segments, green and either red or amber.
    width=a.shape[1]
    def span(m):
        columns=np.flatnonzero(m.sum(axis=0)>=2)
        return int(len(columns))
    spans={k:span(v) for k,v in masks.items()}
    green=counts["green"]>=20 and spans["green"]>=max(5,width*.045)
    warm=any(counts[k]>=20 and spans[k]>=max(5,width*.045) for k in ("red","amber"))
    return {"multicolor_band_candidate":bool(green and warm),
            "bright_pixels":counts,"colored_columns":spans,
            "verified":False}

def label_candidate(raw):
    # Require actual label text. Yellow pixels alone are not an all-in.
    normalized=re.sub(r"[^A-Z]","",raw.upper())
    return normalized=="ALLIN"

def allin_ocr(image, executable):
    result={seat:{"candidate":None,"raw":"","verified":False} for seat in SEATS}
    if not executable:
        return result,"All-in OCR unavailable without Tesseract"
    # Search only approximate bet zones; these boxes are not yet confirmed
    # using positive all-in screenshots.
    # Size the montage from the actual regions: the hero crop used to be clipped.
    scale,pad=3,5
    pitch=max((spec["bet"][3]-spec["bet"][1])*scale for spec in SEATS.values())+2*pad
    width=max((spec["bet"][2]-spec["bet"][0])*scale for spec in SEATS.values())+2*pad
    canvas=Image.new("L",(width,pitch*len(SEATS)),255)
    for i,(seat,spec) in enumerate(SEATS.items()):
        a=pixels(image,spec["bet"])
        r,g,b=np.moveaxis(a,-1,0)
        warm=(r>160)&(g>85)&(r>b+55)&(g>b+25)&(r>=g-12)
        result[seat]["warm_pixels"]=int(warm.sum())
        crop=Image.fromarray(np.uint8(255-255*warm))
        crop=crop.resize((crop.width*scale,crop.height*scale))
        canvas.paste(crop,(pad,i*pitch+pad))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"allin.png"
            canvas.save(path)
            p=subprocess.run([executable,str(path),"stdout","--psm","11","tsv"],
                             capture_output=True,text=True,timeout=20,check=True)
        rows={i:[] for i in range(len(SEATS))}
        for line in p.stdout.splitlines()[1:]:
            cols=line.split("\t",11)
            if len(cols)!=12 or cols[0]!="5" or not cols[11].strip():
                continue
            idx=(int(cols[7])+int(cols[9])//2)//pitch
            if idx in rows:
                rows[idx].append((int(cols[6]),cols[11]))
        for i,seat in enumerate(SEATS):
            raw=" ".join(v for _,v in sorted(rows[i]))
            result[seat]["raw"]=raw
            # Absence of a recognized label is unknown, not proof of not all-in.
            result[seat]["candidate"]=True if label_candidate(raw) else None
        return result,None
    except (OSError,ValueError,subprocess.SubprocessError) as e:
        return result,f"All-in OCR failed: {e}"

def seat_evidence(image, executable=None, previous=None):
    labels,err=allin_ocr(image,executable)
    evidence={}
    for name,spec in SEATS.items():
        avatar=pixels(image,spec["avatar"])
        brightness=float(avatar.mean())
        item={"bar":bar_evidence(pixels(image,spec["bar"])),
              "all_in_label":labels[name],"avatar_mean_brightness":round(brightness,2),
              "brightness_change":None,"darkened_candidate":None,
              "appearance_change_candidate":None,"folded":None,"departed":None,
              "verified":False}
        if previous is not None:
            old=pixels(previous,spec["avatar"])
            delta=float(np.mean(np.abs(avatar-old)))
            ratio=brightness/max(1,float(old.mean()))
            item["brightness_change"]=round(ratio-1,3)
            item["darkened_candidate"]=bool(ratio<.72)
            item["appearance_change_candidate"]=bool(delta>32)
            item["avatar_mean_absolute_change"]=round(delta,2)
        evidence[name]=item
    hits=[k for k,v in evidence.items() if v["bar"]["multicolor_band_candidate"]]
    return {"seats":evidence,"active_band_candidate":hits[0] if len(hits)==1 else None,
            "active_band_conflict":len(hits)>1,"active_band_hits":hits,
            "note":"Candidates only. Darkness or appearance changes do not establish folding, departure, or occupancy. No active band is not proof of inactivity.",
            "ocr_warning":err}

