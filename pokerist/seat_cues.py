"""Experimental visual evidence for saved Pokerist screenshots, not a live tracker."""
import re
from native_ocr import recognize_tsv
import subprocess
import tempfile
from pathlib import Path
from PIL import Image
import numpy as np

# Layout calibrated only for the supplied 1536x709 five-seat frame.
# Each seat has a profile base, avatar, label, and possible bet/label region.
SEATS = {
    "hero": {"bar":(646,528,802,571),"avatar":(674,420,768,527),"label":(682,568,771,611),"bet":(620,366,800,420)},
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

def hero_bar_evidence(a):
    """Supplement the multicolor detector for a partially elapsed hero ring.
    Require substantial green spatial evidence in the calibrated lower arc;
    a yellow winner border alone never qualifies.
    """
    evidence=bar_evidence(a)
    green=colors(a)["green"]
    rows=int((green.sum(axis=1)>=2).sum())
    strong=bool(evidence["bright_pixels"]["green"]>=65
        and evidence["colored_columns"]["green"]>=12 and rows>=4)
    evidence["green_rows"]=rows
    evidence["hero_green_fallback"]=strong and not evidence["multicolor_band_candidate"]
    evidence["multicolor_band_candidate"]=bool(evidence["multicolor_band_candidate"] or strong)
    return evidence

def avatar_appearance(a,seat=None):
    """Appearance only: distinguish blue-grey overlays from normal profiles.
    Default blue silhouettes and card-covered profiles remain ambiguous.
    Thresholds calibrated on the supplied five-seat saved screenshots.
    """
    r,g,b=np.moveaxis(a.astype(np.int16,copy=False),-1,0)
    lo=np.minimum(np.minimum(r,g),b)
    hi=np.maximum(np.maximum(r,g),b)
    warm=float(((r-b>18)&(r>g+8)&(r>70)).mean())
    blue=float(((b-r>10)&(b>g+3)).mean())
    white=float(((lo>120)&(hi-lo<30)).mean())
    cyan=float(((b>140)&(g>100)&(g-r>55)&(b-r>65)).mean())
    gray=a.mean(2)
    brightness=float(gray.mean())
    texture=float((np.abs(np.diff(gray,axis=0)).mean()+np.abs(np.diff(gray,axis=1)).mean())/2)
    if white>.35:kind="obscured"
    elif cyan>.025 and warm<.02 and blue>.5:kind="empty"
    elif warm<.02 and ((blue>.97 and brightness>60) or (seat=="left" and blue>.94 and brightness>65 and texture<3.5)):kind="silhouette"
    elif blue>.45 and warm<.015:kind="dimmed"
    elif warm>.15:kind="colored"
    else:kind="unknown"
    return {"candidate":kind,"warm_fraction":round(warm,4),
            "blue_fraction":round(blue,4),"white_fraction":round(white,4),
            "cyan_fraction":round(cyan,4),"brightness":round(brightness,2),"texture":round(texture,3),"verified":False}

def profile_appearance(image,seat):
    evidence=avatar_appearance(pixels(image,SEATS[seat]["avatar"]),seat)
    if seat=="hero":
        r,g,b=np.moveaxis(pixels(image,(695,545,755,605)),-1,0)
        cyan=(b>140)&(g>100)&(g-r>55)&(b-r>65)
        evidence["empty_chair_cyan_pixels"]=int(cyan.sum())
        if cyan.sum()>=350 and evidence["warm_fraction"]<.02:
            evidence["candidate"]="empty"
    return evidence

def label_candidate(raw):
    # Require actual label text. Yellow pixels alone are not an all-in.
    normalized=re.sub(r"[^A-Z]","",raw.upper())
    return normalized=="ALLIN"

def allin_ocr(image, executable, *, persistent=False):
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
        if not any(item.get("warm_pixels") for item in result.values()):
            return result,None
        tsv=recognize_tsv(canvas,executable,persistent=persistent)
        rows={i:[] for i in range(len(SEATS))}
        for line in tsv.splitlines()[1:]:
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

def seat_evidence(image, executable=None, previous=None, cache=None):
    if cache is None or not executable:
        labels,err=allin_ocr(image,executable)
    else:
        # Exact warm-ink masks match allin_ocr preprocessing. No stale label
        # may survive a changed mask or failed OCR.
        masks=[]
        for spec in SEATS.values():
            a=pixels(image,spec['bet']);r,g,b=np.moveaxis(a,-1,0)
            warm=(r>160)&(g>85)&(r>b+55)&(g>b+25)&(r>=g-12)
            masks.append(warm.tobytes())
        key=tuple(masks)
        old=getattr(cache,'allin',None)
        if old is not None and old[0]==key:
            labels,err=old[1],None
        else:
            labels,err=allin_ocr(image,executable,persistent=True)
            cache.allin=(key,labels) if not err else None
    evidence={}
    for name,spec in SEATS.items():
        avatar=pixels(image,spec["avatar"])
        brightness=float(avatar.mean())
        bar=pixels(image,spec["bar"])
        item={"bar":hero_bar_evidence(bar) if name=="hero" else bar_evidence(bar),
              "all_in_label":labels[name],"avatar_mean_brightness":round(brightness,2),
              "avatar_appearance":profile_appearance(image,name),
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

