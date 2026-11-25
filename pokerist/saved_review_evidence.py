"""Visual evidence for completed-image verification only.

Independent rank/suit candidates retain their original crop and distance.
They are not combined into automatic card identities and do not modify
the normal recognition pipeline.
"""
from base64 import b64encode
from io import BytesIO
from collections import defaultdict
from PIL import Image

def union_box(boxes,image,pad=0):
    if not boxes:
        raise ValueError("At least one evidence box is required")
    return (max(0,min(b[0] for b in boxes)-pad),
            max(0,min(b[1] for b in boxes)-pad),
            min(image.width,max(b[2] for b in boxes)+pad),
            min(image.height,max(b[3] for b in boxes)+pad))

def crop_evidence(image,box):
    if not 0<=box[0]<box[2]<=image.width or not 0<=box[1]<box[3]<=image.height:
        raise ValueError("Invalid evidence crop")
    crop=image.crop(box).convert("RGB")
    with BytesIO() as data:
        crop.save(data,format="PNG")
        encoded=b64encode(data.getvalue()).decode("ascii")
    return {"bounds":list(box),"width":crop.width,"height":crop.height,
            "png_base64":encoded}

def component_choices(image,regions,recognizer,rank_templates,suit_templates):
    """Retain independently recognized characters, never infer a complete card."""
    by_kind={"rank":{},"suit":{}}
    for rank_box,suit_box,wide in regions:
        for color in ("red","black"):
            for kind,box,templates,limit in (
                    ("rank",rank_box,rank_templates,.18),
                    ("suit",suit_box,{k:v for k,v in suit_templates.items()
                                      if k[0] in ("dh" if color=="red" else "cs")},.25)):
                label,distance=recognizer(image,box,color,templates,limit)
                if label is None or distance is None or (kind=="rank" and wide and label!="T"):
                    continue
                item={"label":label,"distance":distance,"color":color,"bounds":list(box)}
                old=by_kind[kind].get(label)
                if old is None or distance<old["distance"]:
                    by_kind[kind][label]=item
    return {kind:sorted(choices.values(),key=lambda item:(item["distance"],item["label"]))[:4]
            for kind,choices in by_kind.items()}

def saved_evidence(image,cards):
    # Import here to avoid loading the review module while it defines constants.
    from review import (BOARD,HOLE,HOLE_MIRROR,HOLE_WIDE,HOLE_HIGHLIGHT,
                        HOLE_ROTATED,HOLE_GOLD_PAIR,lower_corner,narrow_suit,
                        ten_corner,NUMBERS,RANKS,SUITS,glyph,match)
    from card_geometry import corner_regions
    from table_observation import REGIONS
    def recognize(im,box,color,templates,threshold):
        return match(glyph(im,box,color),templates,threshold)
    out={}
    for group,specs in (
        ("hole",[list(items) for items in zip(HOLE,HOLE_MIRROR,HOLE_WIDE,
                                             HOLE_HIGHLIGHT,HOLE_ROTATED,HOLE_GOLD_PAIR)]),
        ("board",[[spec,lower_corner(spec),narrow_suit(spec)] for spec in BOARD])):
        for i,variants in enumerate(specs):
            slot=cards[group+"_slots"][i]
            boxes=[box for spec in variants for box in spec]
            regions=[]
            for spec in variants:
                options=corner_regions(image,spec)
                regions.extend((r,s,False) for r,s in (options or [(spec[0],spec[1])]))
                boxes.extend(box for pair in options for box in pair)
            if group=="board":
                r,s,_=ten_corner(variants[0])
                regions.append((r,s,True))
                boxes.extend((r,s))
            entry=crop_evidence(image,union_box(boxes,image,3))
            if isinstance(slot,dict) and not slot.get("candidate"):
                entry["components"]=component_choices(image,list(dict.fromkeys(regions)),
                                                      recognize,RANKS,SUITS)
            out[f"{group}.{i}"]=entry
    for key,box in NUMBERS.items():
        out[key]=crop_evidence(image,union_box([box],image,2))
    for seat,regions in REGIONS.items():
        out["bet."+seat]=crop_evidence(image,union_box([regions["bet"]],image,2))
    return out
