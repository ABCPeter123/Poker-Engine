"""Offline screenshot review prototype for the 1536 x 709 Pokerist layout.

No screen mirroring, continuous capture, game interaction or live advice.
All readings are candidates requiring confirmation. Original image stays local.
"""
import argparse
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import shutil
if __name__ == "__main__":
    from bootstrap import ensure_requirements
    ensure_requirements()

from PIL import Image
import numpy as np
from seat_cues import seat_evidence
from frame_crop import game_bounds
from table_observation import observe_table
from adaptive_labels import scan_regions, select_amount, reconcile_amount
from ocr_runtime import resolve_tesseract
from card_geometry import gold_mask, face_bounds, corner_regions

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
RANKS.update({"8_sample":"3fc,79c,606,606,e06,606,79c,3fc,79c,f07,e07,e07,e07,e07,79e,3fc","4_sample_black":"1e0,1f0,1f8,1f8,198,184,184,186,187,183,1c3,fff,fff,1c0,180,1c0","4_sample_red":"1c0,3e0,3f0,3f8,3f8,3f8,3fc,3dc,3de,3ce,fff,fff,ffc,7c0,380,300","7_sample":"fff,fff,600,300,380,1c0,1c0,1c0,0e0,0e0,070,070,070,078,078,078","6_sample":"3fc,79e,e07,007,007,0c7,7ff,f0f,e0f,e07,e07,e07,e07,e0f,78e,3fc","T_sample":"718,d98,89c,898,898,898,898,898,898,898,898,898,898,d98,700,000","9_sample":"1e0,7f8,7f8,e18,e1c,71c,70e,79e,7fc,3f8,3c0,3c2,3c7,1cf,1fe,07c"})
SUITS.update({"c_sample":"0f0,1f8,1f8,1f8,1f8,1f8,3fc,7fe,fff,fff,fff,fff,7fe,060,060,060","c_sample2":"0f0,1f0,1f8,1f8,1f8,1f8,3fc,7ff,fff,fff,fff,fff,7de,060,060,060","h_sample":"3bc,7fe,7fe,ffe,fff,fff,fff,ffe,7fe,7fe,3fc,3fc,1f8,0f0,0f0,060","s_sample":"060,060,0f0,1f8,3fc,7ff,fff,fff,fff,fff,fff,7fe,020,020,060,060","s_sample2":"040,060,0f0,1f8,3fc,7fe,7fe,7fe,fff,fff,7fe,7fe,040,060,060,000","s_sample3":"060,0f0,0f0,1f8,3fe,7fe,7ff,fff,fff,fff,7fe,7fe,020,060,060,060","d_sample":"0c0,0e0,1f0,1fc,3fc,3fe,7ff,7ff,fff,7fe,7fe,3fc,1fc,0f8,070,030"})
# Extracted corner glyphs from the four supplied saved screenshots.
RANKS.update({"K_corner0":"606,787,7cf,1ef,1ff,0ff,0ff,0ff,1ff,1ff,1cf,3cf,78f,78f,f0f,e07","K_corner1":"707,787,3c7,1e7,0f7,0ff,0ff,0ff,0ff,1ff,1c7,3c7,787,787,f07,f07","K_cornerblack":"e07,707,386,1c6,0c6,076,07f,0ff,0fe,1c6,1c6,386,707,707,f07,e07","A_corner0":"060,0f0,0f0,0f0,1f8,198,19c,38c,38c,30c,70e,7fe,7fe,606,e07,c03","A_corner1":"060,0f0,0f0,0f0,1f8,1d8,1dc,18c,38c,306,70e,7fe,7fe,606,e07,c03","A_corner2":"070,0f0,0f0,0f0,0f8,1d8,1dc,19c,38c,30e,70e,7fe,7fe,706,e07,e07","A_corner3":"070,070,070,0f8,1d8,1c8,1cc,18c,38e,38e,38e,7fe,7ff,e07,e07,e03","2_cornerred":"3fc,7fe,f9f,f8f,f8f,f86,780,7c0,3e0,1f0,0f8,07c,03e,07f,fff,fff","2_cornerblack":"1fc,7fc,f0e,e06,e06,600,700,380,1c0,0e0,070,078,01c,01e,01f,fff","5_corner":"7ff,01f,00f,00f,00f,7ff,fff,f0f,e00,e00,e00,e00,e07,f0f,7df,3fc","Q_cornerblack":"3f8,79e,e06,e07,e07,e07,e07,e07,e07,e07,e07,e07,e07,79e,3fc,700","Q_cornerred":"3f8,7fe,f1e,f0f,f0f,e0f,e0f,e0f,e0f,f0f,f0f,f0f,7de,7fc,7e0,700","J_highlightboard":"f00,f00,f00,f00,f00,f00,f00,f00,f00,f00,f00,f87,f87,7df,7fe,1fc","J_highlighthole":"c00,e00,e00,e00,e00,e00,e00,e00,e00,e00,e00,e03,e07,f07,7ff,3fe","3_cornerhole":"000,380,7c0,cc0,c40,c00,c00,700,780,700,600,610,218,318,3b0,1f0","8_corner":"3fc,78f,e0f,e07,e07,f07,79e,7fe,7fe,f07,e07,e07,e07,f0f,79f,3fc","9_corner":"3fc,7be,e0f,e07,e07,e07,e07,f0f,ffe,ffc,e00,e00,e07,f07,7fe,3fc"})
SUITS.update({"d_corner":"060,0f0,1f8,3fc,3fc,7fe,fff,fff,fff,7fe,7fe,3fc,1f8,1f0,0f0,060","d_highlight":"030,078,0f8,1fc,3fe,7fe,7fe,fff,fff,7fe,7fe,3fe,1fc,0fc,0f8,070","s_corner":"020,060,0f0,1f8,3fc,7fe,7fe,fff,fff,7ff,7fe,3fc,020,020,060,060","c_corner":"0f0,1f0,1f8,1f8,1f0,1f8,3fc,7fe,fff,fff,fff,7fe,7fc,040,060,060","c_highlight":"078,0fc,0fc,0fe,0fc,1fe,3ff,7ff,fff,fff,fff,fff,7ff,030,030,030","c_cornerhole":"1e0,1e0,3f0,3f0,3f0,3f8,1fe,3fe,7ff,7ff,fff,ffe,7fe,7c0,3a0,030"})
# Corner masks sampled from the November 24 saved images.
RANKS.update({"T_capture0":"788,f8c,ccf,84c,84c,84c,c4c,c4c,c4c,c4c,c4c,c4c,c4c,ccc,fcc,78c","8_capture1":"1f8,7fe,fff,f0f,f0f,f0f,bfe,7fe,ffe,fde,f0e,f0a,f0e,f9e,ffe,5fe","8_capture2":"1e0,3f0,ff8,e38,e18,f1c,73c,7fc,3fc,3fe,38c,38e,38b,3cf,1fe,1fc","3_capture4":"070,3fc,7be,78f,70e,780,780,7e0,7e0,f80,f80,e80,f8b,b9f,7fe,1f8"})
SUITS.update({"s_capture0":"060,0f0,0f0,1f8,3fc,7fe,ffe,fff,fff,fff,ffe,7fe,060,060,060,060","d_capture1":"040,0e0,0f0,1f8,3fc,3fe,7fe,7ff,fff,3fe,7fe,3fc,1f8,1f0,0e0,060","h_capture2":"03c,03c,7fe,7ff,7ff,ffe,ffe,fff,7ff,7fe,7fe,3fc,1f8,0f8,078,030","h_capture4":"3fe,7de,7ff,fff,ffe,ffe,ffe,ffe,7fe,7fc,3fc,1f8,1f8,0f8,060,060"})
# Gold-bordered pair from the supplied saved screenshot, sampled at the actual glyphs.
RANKS.update({"5_gold_red":"1f8,00c,014,016,036,3fe,ffe,f1e,b80,b80,b80,b8e,f0e,f7e,3fe,1fc","5_gold_black":"770,038,018,018,03c,1fc,79c,700,700,700,382,183,183,1c7,0fe,078"})
SUITS.update({"d_gold":"040,078,0f8,178,1fc,3fe,7fe,fff,fff,7fe,3fe,1fc,1f8,0f8,070,060","s_gold":"040,0e0,0f8,1fe,1fe,3fe,7fe,7ff,fff,fff,7ff,7ff,7fc,100,018,018"})
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
HOLE_WIDE = [
    ((805,470,841,508),(809,509,837,539),(811,471,836,544)),
    ((853,465,883,505),(847,506,874,535),(849,469,890,548))
]
# The title-bar crop and highlighted card frame can shift corner glyphs a few pixels.
def lower_corner(spec):
    r,s,body=spec
    return ((r[0],r[1]+4,r[2],r[3]+6),(s[0],s[1]+8,s[2],s[3]+8),body)

HOLE_HIGHLIGHT = [
    ((811,478,832,515),(810,516,835,545),(811,477,836,548)),
    ((852,473,878,514),(846,514,874,539),(849,477,890,548))
]
# Keep the normal rank crop for single characters; only the ten candidate
# can be sourced from a wider rank strip.
def ten_corner(spec):
    r,s,body=spec
    return ((r[0]-5,r[1]-2,r[0]+32,r[3]),s,body)

def narrow_suit(spec):
    r,s,body=spec
    return (r,(s[0],s[1]-2,s[2],s[3]-3),body)

HOLE_ROTATED = [
    HOLE[0],
    ((852,464,879,501),(845,503,874,529),(849,469,890,548))
]
HOLE_GOLD_PAIR = [
    ((814,473,831,508),(810,510,833,538),(811,471,836,544)),
    ((855,469,878,503),(846,506,872,531),(849,469,890,548))
]
NUMBERS = {
    "pot":(685,198,850,234),
    "hero":(640,584,820,617),
    "left":(265,454,435,485),
    "upper_left":(480,158,650,188),
    "upper_right":(890,158,1060,188),
    "right":(1110,454,1280,485)
}

@lru_cache(maxsize=256)
def decode(value):
    mask=np.array([[bool(int(row,16)&(1<<j)) for j in range(12)]
                   for row in value.split(",")])
    if mask.shape != (16,12):
        raise ValueError("Template must contain sixteen 12-bit rows")
    mask.setflags(write=False)
    return mask

def ink_masks(a):
    # The gold outline and warm face-card illustration are not rank ink.
    a=np.asarray(a,dtype=np.int16)
    r,g,b=np.moveaxis(a,-1,0)
    gold=gold_mask(a)
    red=(r>95)&(r-g>40)&(r-b>35)&~gold&((g-b<35)|(g<r*.55))
    black=(a.max(2)<125)&(np.ptp(a,axis=2)<55)&~gold
    return red,black

def glyph(image, box, color=None):
    a=np.asarray(image.crop(box).convert("RGB"),dtype=np.int16)
    red,black=ink_masks(a)
    m=red if color=="red" else black if color=="black" else red|black
    ys,xs=np.where(m)
    if len(ys)<15:
        return None
    m=m[ys.min():ys.max()+1,xs.min():xs.max()+1]
    return np.asarray(Image.fromarray(np.uint8(m*255)).resize((12,16)))>=128

def _pack_mask(mask):
    return int.from_bytes(np.packbits(mask).tobytes(),"big")

@lru_cache(maxsize=32)
def _packed_templates(items):
    return tuple((key.split("_")[0],_pack_mask(decode(value))) for key,value in items)

def match(m, templates, threshold=.18):
    if m is None:
        return None, None
    if m.shape != (16,12) or m.dtype != np.bool_:
        raise ValueError("Expected a 16x12 boolean glyph")
    packed=_pack_mask(m)
    grouped={}
    # The glyph contains exactly 192 bits; XOR counts the same mismatches
    # as the previous elementwise numpy comparison, without per-template arrays.
    for label,value in _packed_templates(tuple(templates.items())):
        distance=(packed^value).bit_count()
        grouped[label]=min(grouped.get(label,192),distance)
    scores=sorted((count/192,label) for label,count in grouped.items())
    distance,label=scores[0]
    margin=scores[1][0]-distance if len(scores)>1 else 1.0
    return (label if distance<=threshold and margin>=.025 else None),round(distance,3)

def face_present(image, box):
    a=np.asarray(image.crop(box),dtype=np.int16)
    # Require sustained bright neutral card stock, not pale lettering on blue felt.
    light=(a.min(2)>180)&(np.ptp(a,axis=2)<32)
    return float(light.mean())>=.20 and float((light.mean(axis=1)>=.15).mean())>=.60

def card(image, spec, *alternates, wide_ten=None):
    present=False
    readings={}
    regions=set()
    for item in [spec]+list(alternates):
        r,s,body=item
        options=corner_regions(image,item)
        if not options and not face_present(image,body):
            continue
        present=True
        regions.update(options or [(r,s)])
    # Repeated alternative corner pairs often share one rank or suit box.
    # Cache within this card only; never reuse pixels across images.
    @lru_cache(maxsize=None)
    def recognized(box,color,kind):
        if kind=="rank":
            return match(glyph(image,box,color),RANKS)
        allowed="dh" if color=="red" else "cs"
        return match(glyph(image,box,color),{k:v for k,v in SUITS.items() if k[0] in allowed},.25)
    for r,s in sorted(regions):
        for color in ("red","black"):
            rank,rd=recognized(r,color,"rank")
            suit,sd=recognized(s,color,"suit")
            if rank and suit:
                label=rank+suit
                reading=(rd+sd,rank,suit,rd,sd)
                if label not in readings or reading[0]<readings[label][0]:
                    readings[label]=reading
    if not present:
        return None
    if wide_ten is not None:
        r,s,_=wide_ten
        # Compare against all ranks, not just T, so other broad glyphs
        # cannot become a ten simply because it is the only candidate.
        for color in ("red","black"):
            rank,rd=recognized(r,color,"rank")
            suit,sd=recognized(s,color,"suit")
            if rank=="T" and suit:
                label=rank+suit
                reading=(rd+sd,rank,suit,rd,sd)
                if label not in readings or reading[0]<readings[label][0]:
                    readings[label]=reading
    ordered=sorted(readings.values())
    if not ordered or (len(ordered)>1 and ordered[1][0]-ordered[0][0]<.05):
        return {"candidate":None,"rank_candidate":None,"suit_candidate":None,
                "rank_distance":None,"suit_distance":None,"verified":False}
    _,rank,suit,rd,sd=ordered[0]
    return {"candidate":rank+suit,"rank_candidate":rank,"suit_candidate":suit,
            "rank_distance":rd,"suit_distance":sd,"verified":False}

from amount_text import number_text

def read_numbers(image, executable):
    regions=[(key,box,"bet" if key=="pot" else "stack") for key,box in NUMBERS.items()]
    rows,error=scan_regions(image,executable,regions)
    results={key:select_amount(rows.get(key,[]),number_text) for key in NUMBERS}
    # A whitelist can yield zero confidence on a correct digit sequence.
    # Only retry rejected nonempty stack strings, and require agreement.
    retry=[entry for entry in regions if entry[2]=="stack" and
           results[entry[0]]["raw"] and results[entry[0]]["candidate"] is None]
    if retry and executable and not error:
        alternate,alt_error=scan_regions(image,executable,retry,unrestricted=True)
        if not alt_error:
            for key,_,_ in retry:
                results[key]=reconcile_amount(results[key],select_amount(alternate.get(key,[]),number_text),number_text)
    return results,error

def normalize(original):
    original=original.convert("RGB")
    bounds=game_bounds(original)
    visible=original.crop(bounds)
    image=visible.resize((WIDTH,HEIGHT))
    image.info["capture_crop"]={"input_size":list(original.size),"bounds":list(bounds),"visible_size":list(visible.size),"cropped":bounds!=(0,0,*original.size)}
    return image

def review(path, executable=None, previous_path=None, *, enhanced=False, deep=False):
    with Image.open(path) as original:
        image=normalize(original)
    previous=None
    if previous_path:
        with Image.open(previous_path) as old:
            previous=normalize(old)
        if previous.info.get("capture_crop")!=image.info.get("capture_crop"):
            previous=None
    return review_image(image, executable, previous, Path(path).name, enhanced=enhanced, deep=deep)

def read_cards(image):
    board=[card(image,spec,lower_corner(spec),narrow_suit(spec),wide_ten=ten_corner(spec)) for spec in BOARD]
    hole=[card(image,spec,alternate,wide,highlight,rotated,gold_pair) for spec,alternate,wide,highlight,rotated,gold_pair in zip(HOLE,HOLE_MIRROR,HOLE_WIDE,HOLE_HIGHLIGHT,HOLE_ROTATED,HOLE_GOLD_PAIR)]
    count=sum(c is not None for c in board)
    contiguous=all(c is not None for c in board[:count]) and all(c is None for c in board[count:])
    known=[c["candidate"] for c in hole+board if c and c["candidate"]]
    duplicate=len(set(known))!=len(known)
    return {"board_slots":board,"hole_slots":hole,
            "street_candidate":{0:"Preflop",3:"Flop",4:"Turn",5:"River"}.get(count) if contiguous else None,
            "quality":{"duplicate_card_candidates":duplicate,
                       "noncontiguous_board":not contiguous,
                       "unrecognized_visible_cards":sum(c is not None and c["candidate"] is None for c in hole+board)}}

def review_image(image, executable=None, previous=None, source="frame", *, enhanced=False, deep=False):
    started=time.perf_counter()
    cues=seat_evidence(image,executable,previous)
    after_cues=time.perf_counter()
    if deep:
        from saved_card_review import read_deep
        cards=read_deep(image,read_cards)
    elif enhanced:
        from saved_card_review import read_enhanced
        cards=read_enhanced(image,read_cards)
    else:
        cards=read_cards(image)
    after_cards=time.perf_counter()
    hole=cards["hole_slots"]
    numbers,err=read_numbers(image,executable)
    if (enhanced or deep) and executable:
        from saved_amount_review import add_saved_amount_evidence
        numbers=add_saved_amount_evidence(image,executable,NUMBERS,numbers,number_text)
    after_amounts=time.perf_counter()
    observation=observe_table(image,executable,number_text,numbers,cues,hole)
    evidence={}
    if enhanced or deep:
        from saved_review_evidence import saved_evidence
        evidence=saved_evidence(image,cards)
    finished=time.perf_counter()
    timings={"seat_cues":round(1000*(after_cues-started),3),"cards":round(1000*(after_cards-after_cues),3),
             "amounts":round(1000*(after_amounts-after_cards),3),"table_observation":round(1000*(finished-after_amounts),3),
             "total":round(1000*(finished-started),3)}
    return {"layout":"Pokerist landscape, five seats, prototype",
            "source":source,"verified":False,
            "capture_crop":image.info.get("capture_crop"),
            "timings_ms":timings,
            **cards,
            **({"saved_field_evidence":evidence} if enhanced or deep else {}),
            "number_candidates":numbers,"number_ocr_error":err,
            "dealer":None,"active_player":None,"bets":None,"actions":None,
            "table_observation":observation,
            "seat_evidence":cues,
            "limitations":["All thirteen ranks and four suits have sample glyphs. Recognition can still reject or misclassify unfamiliar rendering or occluded characters.",
                           "Fixed crop coordinates assume the supplied screen layout and scale.",
                           "All candidates require human review; no inferred player actions.",
                           "A rounded pot label is not an exact chip count."]+([err] if err else [])}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot",nargs="?")
    parser.add_argument("--output",default="pokerist-review.json")
    parser.add_argument("--quiet",action="store_true",help="Write JSON to output without echoing the full report")
    parser.add_argument("--previous",help="Earlier saved screenshot of the same table for visual comparison")
    parser.add_argument("--tesseract",default=None)
    parser.add_argument("--no-ocr",action="store_true")
    parser.add_argument("--enhanced",action="store_true",help="Try conservative multi-view card recovery on a saved image")
    parser.add_argument("--deep",action="store_true",help="Additional saved-image alignment checks; slower than enhanced review")
    args=parser.parse_args()
    if not args.screenshot:
        from tkinter import Tk,filedialog
        root=Tk();root.withdraw()
        args.screenshot=filedialog.askopenfilename(filetypes=[("Images","*.png *.jpg *.jpeg")])
        root.destroy()
        if not args.screenshot:
            return
    executable=args.tesseract
    if args.no_ocr:
        executable=None
    elif not executable:
        executable,error=resolve_tesseract()
        if error:
            print(error,flush=True)
    result=review(args.screenshot,executable,args.previous,enhanced=args.enhanced,deep=args.deep)
    Path(args.output).write_text(json.dumps(result,indent=2),encoding="utf-8")
    if not args.quiet:
        print(json.dumps(result,indent=2))
    print("Review saved to",args.output)

if __name__=="__main__":
    main()
