"""Offline screenshot review prototype for the 1536 x 709 Pokerist layout.

No screen mirroring, continuous capture, game interaction or live advice.
All readings are candidates requiring confirmation. Original image stays local.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import shutil
if __name__ == "__main__":
    from bootstrap import ensure_requirements
    ensure_requirements()

from PIL import Image
import numpy as np
from seat_cues import seat_evidence
from frame_crop import game_bounds

WIDTH, HEIGHT = 1536, 709
# Coordinates are normalized to the supplied landscape layout.
RANKS = {
    "J":"e00,f00,f00,f00,f00,f00,f00,f00,f00,f00,f00,f07,f0f,f9f,7fe,1f8",
    "4":"3e0,3f0,3f0,3b8,398,3dc,3cc,3ce,3c6,3c3,3c7,fff,3c0,3c0,3c0,180",
    "9":"0ff,0fd,1fc,18e,1cc,1cc,18c,1ce,1fc,1fc,1c0,180,18c,1cc,0fc,070",
    "Q":"3f8,7fc,f0f,f0f,f0f,f0f,f0f,f0f,f0f,f0f,f0f,f0f,70f,7fe,3fc,7e0",
    "9_hole":"1c1,ff8,e1c,c1c,c0c,c1c,c0c,c1c,f3c,ff8,c00,c00,c0c,e1c,e38,7f8",
    "3":"3c0,ff0,f78,e38,e10,e00,f00,7e0,3c0,780,706,707,787,3cf,3fe,0fc"
}
RANKS.update({
    "J_mirror":"700,f00,f00,f00,f00,f00,f00,f00,f00,f00,f00,f03,f03,78f,7ff,1fe",
    "3_mirror":"3e0,670,c38,c10,c00,600,700,1e0,380,300,300,302,383,183,1ee,078",
    "9_black":"7fc,fff,e07,e07,e07,e07,e07,e07,fff,ffe,e00,e00,e07,e07,fff,7fe"
})
SUITS = {
    "d":"060,0f0,0f0,1f8,1fc,3fc,7fe,fff,fff,7ff,3fe,1fc,1f8,0f0,0f0,060",
    "d_board_q":"000,000,060,0f0,0f8,1fc,3fe,7ff,fff,fff,7fe,3fe,1fc,0f8,0f0,060",
    "d_hole":"0c0,1e0,1f0,3f8,3fc,3fe,7ff,7ff,ffe,ffe,ffc,3fc,1f8,0f8,070,030",
    "c":"060,0f0,1f8,1f8,1f8,0f0,1f8,7fe,fff,fff,fff,fff,7fe,39c,060,060",
    "h":"7bc,7fe,fff,fff,fff,fff,fff,7fe,7fc,3f8,1f0,0f0,0e0,040,001,001",
    "s":"001,040,0e0,1f1,3f8,7fc,ffd,fff,fff,7fd,3f9,041,0c1,001,001,001"
}
SUITS.update({
    "h_mirror":"188,3fc,7fe,fff,fff,fff,fff,fff,ffe,7fe,7fe,3fc,1f8,1f8,0f0,060",
    "s_mirror":"0c0,1e0,1f8,3fc,3fe,7ff,7ff,fff,fff,fff,ffe,ffc,3f0,000,010,030",
    "s_black":"020,070,0f0,1f8,3fc,3fe,7fe,fff,fff,fff,fff,7fe,3ec,020,060,070"
})
BOARD = [
    ((552,244,575,281),(550,282,576,309),(548,242,628,353)),
    ((642,244,666,281),(641,282,668,310),(638,242,719,353)),
    ((731,244,755,281),(730,282,757,309),(728,242,808,353)),
    ((820,244,845,281),(818,282,845,310),(817,242,898,353)),
    ((909,244,934,281),(907,282,934,310),(906,242,987,353)),
]
HOLE = [
    ((813,473,835,507),(810,510,837,540),(811,471,836,544)),
    ((854,468,879,505),(848,505,873,532),(849,469,890,548))
]
# Second observed layout: slightly lower glyphs in the mirrored frame.
HOLE_MIRROR = [
    ((815,480,837,518),(811,519,836,545),(811,477,836,548)),
    ((854,476,880,514),(848,515,873,541),(849,477,890,548))
]
NUMBERS = {
    "pot":(745,204,790,229),
    "hero":(704,590,766,610),
    "left":(325,460,392,480),
    "upper_left":(559,163,578,183),
    "upper_right":(960,163,1017,183),
    "right":(1169,460,1237,480)
}

def decode(value):
    return np.array([[bool(int(row,16)&(1<<j)) for j in range(12)]
                     for row in value.split(",")])

def glyph(image, box, color=None):
    a=np.array(image.crop(box)).astype(int)
    red=(a[:,:,0]-a[:,:,1]>50)&(a[:,:,0]-a[:,:,2]>45)
    black=a.max(2)<110
    m=red if color=="red" else black if color=="black" else red|black
    ys,xs=np.where(m)
    if len(ys)<15:
        return None
    m=m[ys.min():ys.max()+1,xs.min():xs.max()+1]
    return np.asarray(Image.fromarray(np.uint8(m*255)).resize((12,16)))>=128

def match(m, templates, threshold=.18):
    if m is None:
        return None, None
    grouped={}
    for key,value in templates.items():
        label=key.split("_")[0]
        distance=float(np.mean(m!=decode(value)))
        grouped[label]=min(grouped.get(label,1.0),distance)
    scores=sorted((distance,label) for label,distance in grouped.items())
    distance, label=scores[0]
    margin=scores[1][0]-distance
    return (label if distance<=threshold and margin>=.025 else None), round(distance,3)

def face_present(image, box):
    a=np.asarray(image.crop(box),dtype=np.int16)
    # Require sustained bright neutral card stock, not pale lettering on blue felt.
    light=(a.min(2)>180)&(np.ptp(a,axis=2)<32)
    return float(light.mean())>=.20 and float((light.mean(axis=1)>=.15).mean())>=.60

def card(image, spec, alternate=None):
    present=False
    readings={}
    for r,s,body in [spec]+([alternate] if alternate else []):
        if not face_present(image,body):
            continue
        present=True
        for color,allowed in [("red","dh"),("black","cs")]:
            rank,rd=match(glyph(image,r,color),RANKS)
            suit,sd=match(glyph(image,s,color),{k:v for k,v in SUITS.items() if k[0] in allowed},.25)
            if rank and suit:
                label=rank+suit
                reading=(rd+sd,rank,suit,rd,sd)
                if label not in readings or reading[0]<readings[label][0]:
                    readings[label]=reading
    if not present:
        return None
    ordered=sorted(readings.values())
    if not ordered or (len(ordered)>1 and ordered[1][0]-ordered[0][0]<.05):
        return {"candidate":None,"rank_candidate":None,"suit_candidate":None,
                "rank_distance":None,"suit_distance":None,"verified":False}
    _,rank,suit,rd,sd=ordered[0]
    return {"candidate":rank+suit,"rank_candidate":rank,"suit_candidate":suit,
            "rank_distance":rd,"suit_distance":sd,"verified":False}

def number_text(text):
    value=re.sub(r"\s+","",text.upper()).replace("O","0").replace(",",".")
    if not re.fullmatch(r"\d+(?:\.\d+)?[KM]?",value):
        return None
    unit=value[-1] if value[-1:] in ("K","M") else ""
    if not unit and "." in value:
        return None
    return {"display":text,"value":float(value[:-1])*({"K":1000,"M":1000000}[unit])
            if unit else int(value),"approximate":bool(unit),"verified":False}

def read_numbers(image, executable):
    if not executable:
        return {}, "Tesseract not installed; number OCR unavailable"
    # One OCR invocation per imported screenshot. Fixed rows map output to fields.
    canvas=Image.new("L",(500,100*len(NUMBERS)),255)
    for i,box in enumerate(NUMBERS.values()):
        a=np.asarray(image.crop(box))
        mask=a.min(2)>150
        crop=Image.fromarray(np.uint8(255-255*mask))
        crop=crop.resize((crop.width*3,crop.height*3))
        canvas.paste(crop,(20,i*100+10))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            filename=Path(tmp)/"numbers.png"
            canvas.save(filename)
            p=subprocess.run([executable,str(filename),"stdout","--psm","6","tsv"],
                             capture_output=True,text=True,timeout=20,check=True)
        rows={i:[] for i in range(len(NUMBERS))}
        for line in p.stdout.splitlines()[1:]:
            cols=line.split("\t",11)
            if len(cols)!=12 or cols[0]!="5" or not cols[11].strip():
                continue
            idx=(int(cols[7])+int(cols[9])//2)//100
            if idx in rows:
                rows[idx].append((int(cols[6]),cols[11],float(cols[10])))
        result={}
        for i,k in enumerate(NUMBERS):
            words=sorted(rows[i])
            text=" ".join(w[1] for w in words)
            candidate=number_text(text)
            confidence=round(min((w[2] for w in words),default=-1),1)
            if candidate and confidence>=75:
                candidate["ocr_confidence"]=confidence
            else:
                candidate=None
            result[k]={"raw":text,"candidate":candidate,"ocr_confidence":confidence}
        return result,None
    except (OSError,subprocess.SubprocessError,ValueError) as e:
        return {},f"Number OCR failed: {e}"

def normalize(original):
    original=original.convert("RGB")
    bounds=game_bounds(original)
    visible=original.crop(bounds)
    image=visible.resize((WIDTH,HEIGHT))
    image.info["capture_crop"]={"input_size":list(original.size),"bounds":list(bounds),"visible_size":list(visible.size),"cropped":bounds!=(0,0,*original.size)}
    return image

def review(path, executable=None, previous_path=None):
    with Image.open(path) as original:
        image=normalize(original)
    previous=None
    if previous_path:
        with Image.open(previous_path) as old:
            previous=normalize(old)
        if previous.info.get("capture_crop")!=image.info.get("capture_crop"):
            previous=None
    return review_image(image, executable, previous, Path(path).name)

def review_image(image, executable=None, previous=None, source="frame"):
    cues=seat_evidence(image,executable,previous)
    board=[card(image,spec) for spec in BOARD]
    hole=[card(image,spec,alternate) for spec,alternate in zip(HOLE,HOLE_MIRROR)]
    count=sum(c is not None for c in board)
    contiguous=all(c is not None for c in board[:count]) and all(c is None for c in board[count:])
    known=[c["candidate"] for c in hole+board if c and c["candidate"]]
    duplicate=len(set(known))!=len(known)
    numbers,err=read_numbers(image,executable)
    return {"layout":"Pokerist landscape, five seats, prototype",
            "source":source,"verified":False,
            "capture_crop":image.info.get("capture_crop"),
            "board_slots":board,"hole_slots":hole,
            "street_candidate":{0:"Preflop",3:"Flop",4:"Turn",5:"River"}.get(count) if contiguous else None,
            "quality":{"duplicate_card_candidates":duplicate,"noncontiguous_board":not contiguous,"unrecognized_visible_cards":sum(c is not None and c["candidate"] is None for c in hole+board)},
            "number_candidates":numbers,
            "dealer":None,"active_player":None,"bets":None,"actions":None,
            "seat_evidence":cues,
            "limitations":["Only five rank glyphs are calibrated; unknown ranks can be rejected or misclassified.",
                           "Fixed crop coordinates assume the supplied screen layout and scale.",
                           "All candidates require human review; no inferred player actions.",
                           "A rounded pot label is not an exact chip count."]+([err] if err else [])}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot",nargs="?")
    parser.add_argument("--output",default="pokerist-review.json")
    parser.add_argument("--previous",help="Earlier saved screenshot of the same table for visual comparison")
    parser.add_argument("--tesseract",default=os.getenv("TESSERACT_CMD") or shutil.which("tesseract"))
    args=parser.parse_args()
    if not args.screenshot:
        from tkinter import Tk,filedialog
        root=Tk();root.withdraw()
        args.screenshot=filedialog.askopenfilename(filetypes=[("Images","*.png *.jpg *.jpeg")])
        root.destroy()
        if not args.screenshot:
            return
    result=review(args.screenshot,args.tesseract,args.previous)
    Path(args.output).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    print("Review saved to",args.output)

if __name__=="__main__":
    main()
