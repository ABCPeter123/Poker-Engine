"""Adaptive text-line extraction inside broad, seat-relative search areas.

Coordinates define search areas, not exact digit locations. Never turn an
unreadable or ambiguous label into zero. All returned amounts are candidates.
"""
import re
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
    result={"raw":raw,"candidate":None,"ocr_confidence":None,"text_bounds":None}
    candidates=[]
    for line in lines:
        tokens=[w["text"].strip() for w in line]
        # Grouped integer labels can be split at thousands separators.
        # Reject unexpected extra numeric fragments instead of concatenating.
        if len(tokens)>1 and not (re.fullmatch(r"\d{1,3}",tokens[0]) and
                                  all(re.fullmatch(r"\d{3}",t) for t in tokens[1:])):
            continue
        if not re.fullmatch(r"\d+(?:[.,]\d+)?[KMkm]?\.?",tokens[0]):
            continue
        if any(w["confidence"]<threshold for w in line):
            continue
        candidate=parse(" ".join(tokens))
        if not candidate:
            continue
        confidence=round(min(w["confidence"] for w in line),1)
        bounds=[min(w["x"] for w in line),min(w["y"] for w in line),
                max(w["x"]+w["w"] for w in line),max(w["y"]+w["h"] for w in line)]
        candidates.append((candidate,confidence,bounds))
    # Multiple plausible numeric lines are ambiguous. Do not choose a stack
    # from a nearby bet, or vice versa.
    if len(candidates)==1:
        candidate,confidence,bounds=candidates[0]
        candidate["ocr_confidence"]=confidence
        result.update(candidate=candidate,ocr_confidence=confidence,text_bounds=bounds)
    return result

def scan_regions(image, executable, regions):
    """One OCR pass across variable-width search regions; retain source boxes."""
    if not executable:
        return {}, "Tesseract unavailable"
    width=max((box[2]-box[0])*SCALE+2*PAD for _,box,_ in regions)
    canvas=Image.new("L",(width,PITCH*len(regions)),255)
    for i,(_,box,kind) in enumerate(regions):
        a=np.asarray(image.crop(box),dtype=np.int16)
        r,g,b=np.moveaxis(a,-1,0)
        mask=((r>145)&(g>115)&(b<np.minimum(r,g)-35)) if kind=="status" else ((a.min(2)>112)&(np.ptp(a,axis=2)<45))
        crop=Image.fromarray(np.uint8(255-255*mask))
        crop=crop.resize((crop.width*SCALE,crop.height*SCALE),Image.Resampling.NEAREST)
        if crop.height+2*PAD>PITCH:
            raise ValueError("OCR region exceeds row height")
        canvas.paste(crop,(PAD,i*PITCH+PAD))
    try:
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"labels.png";canvas.save(p)
            proc=subprocess.run([executable,str(p),"stdout","--psm","11","tsv"],capture_output=True,text=True,timeout=20,check=True)
        rows={key:[] for key,_,_ in regions}
        for line in proc.stdout.splitlines()[1:]:
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
