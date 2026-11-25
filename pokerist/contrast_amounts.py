"""Batched grayscale OCR for saved five-seat screenshots.

This is a calibration-stage alternate reader, not proof of a chip balance.
No capture or gameplay integration.
"""
import io
import math
import subprocess
import numpy as np
from PIL import Image

PITCH=200
PAD=20
SCALE=5
MODES={"stretch":(25,95),"soft":(20,98)}

def prepare_contrast_line(image,box,kind,mode="stretch"):
    im=image.crop(box).convert("RGB")
    a=np.asarray(im,dtype=np.int16)
    lum=np.asarray(im.convert("L"),dtype=float)
    h,w=lum.shape
    if kind=="pot":
        # Calibrated pot region: chip artwork precedes the digits.
        # This alternate crop is only evidence; other layouts may shift.
        x0,x1,y0,y1=61,min(w,125),6,min(h,29)
    else:
        mask=(a.min(2)>135)&(np.ptp(a,axis=2)<60)
        mask[:,:int(w*.2)]=False
        mask[:,int(w*.8):]=False
        density=mask[:,w//5:w-w//5].sum(1)
        bands=np.flatnonzero(np.diff(np.r_[False,density>=3,False])).reshape(-1,2)
        if not len(bands):
            return None
        y0,y1=max(bands,key=lambda t:density[t[0]:t[1]].sum())
        mask[:y0]=False
        mask[y1:]=False
        xs=np.where(mask)[1]
        if not len(xs):
            return None
        # First 15 pixels are the calibrated leading chip emblem.
        x0,x1=int(xs.min())+15,min(w,int(xs.max())+2)
        y0,y1=max(0,y0-2),min(h,y1+2)
    if x1<=x0 or y1<=y0:
        return None
    lum=lum[y0:y1,x0:x1]
    lo,hi=np.percentile(lum,MODES[mode])
    if hi-lo<12:
        return None
    gray=np.uint8(np.clip((hi-lum)*255/max(hi-lo,25),0,255))
    return Image.fromarray(gray).resize((gray.shape[1]*SCALE,gray.shape[0]*SCALE),Image.Resampling.LANCZOS)

def scan_contrast_regions(image,executable,regions,mode="stretch"):
    results={key:{"raw":"","confidence":None,"method":mode} for key in regions}
    if not executable or not regions:
        return results
    crops=[(key,prepare_contrast_line(image,box,"pot" if key=="pot" else "stack",mode)) for key,box in regions.items()]
    sheet=Image.new("L",(800,PITCH*len(crops)),255)
    for i,(key,crop) in enumerate(crops):
        if crop is not None:
            if crop.width+PAD>sheet.width or crop.height+16>PITCH:
                results[key]["error"]="Crop exceeds montage cell"
                continue
            sheet.paste(crop,(PAD,i*PITCH+16))
    try:
        with io.BytesIO() as buf:
            sheet.save(buf,format="PNG")
            proc=subprocess.run([executable,"stdin","stdout","--psm","6","-c",
                "tessedit_char_whitelist=0123456789.KkMm,","tsv"],
                input=buf.getvalue(),capture_output=True,timeout=5,check=True)
        words={key:[] for key in regions}
        for line in proc.stdout.decode("utf-8",errors="replace").splitlines()[1:]:
            c=line.split("\t",11)
            if len(c)!=12 or c[0]!="5" or not c[11].strip():
                continue
            idx=(int(c[7])+int(c[9])//2)//PITCH
            confidence=float(c[10])
            if 0<=idx<len(crops) and math.isfinite(confidence):
                words[crops[idx][0]].append((int(c[6]),c[11].strip(),confidence))
        for key,items in words.items():
            if items:
                items.sort()
                results[key].update(raw=" ".join(v[1] for v in items),
                                    confidence=round(min(v[2] for v in items),1))
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        for item in results.values():
            item["error"]=str(exc)[:300]
    return results
