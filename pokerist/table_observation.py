"""Read-only visual observations for saved hands or authorized practice."""
import re
import tempfile
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view
from adaptive_labels import scan_regions, select_amount, text_lines

SEAT_ORDER=("hero","left","upper_left","upper_right","right")
# Normalized 1536x709 coordinates. Other seats/layouts are not calibrated.
REGIONS={
 "hero":{"bet":(725,420,905,461),"status":(655,566,795,588),"back":None},
 "left":{"bet":(420,285,590,320),"status":(285,437,410,460),"back":(411,326,466,376)},
 "upper_left":{"bet":(475,193,645,228),"status":(490,142,625,165),"back":(620,143,675,191)},
 "upper_right":{"bet":(890,193,1060,228),"status":(915,142,1048,165),"back":(858,143,912,191)},
 "right":{"bet":(960,285,1150,320),"status":(1128,437,1260,460),"back":(1070,326,1126,376)}
}
ANCHORS={"upper_left":(350,95),"upper_right":(418,95),"left":(241,175),"right":(527,175),"hero":(405,205)}
D=np.array([142,144,145,146,151,157,156,148,141,139,140,140,139,144,142,144,168,197,207,207,202,180,152,138,137,138,140,148,182,208,212,212,215,219,218,199,164,139,139,145,183,215,210,136,105,104,105,164,216,199,160,138,155,207,226,194,100,129,165,120,112,182,225,184,138,160,210,227,178,104,183,243,195,112,150,234,194,142,160,210,226,164,104,187,245,204,117,148,232,193,144,153,206,220,148,93,149,183,139,108,167,225,188,141,143,190,211,154,115,126,133,120,143,198,208,166,138,134,149,188,189,182,183,186,191,208,209,168,136,140,135,118,141,175,190,197,197,193,185,161,129,128,141,139,132,117,114,124,132,133,129,117,112,124,141,142,140,141,139,126,107,98,98,103,115,131,140,141,141],dtype=np.int16).reshape(13,13)

def dealer_marker(image):
    a=np.asarray(image.resize((768,355)).convert("L"),dtype=np.int16)
    matches=[]
    for seat,(x,y) in ANCHORS.items():
        windows=sliding_window_view(a[y-22:y+23,x-30:x+31],(13,13))
        distances=np.abs(windows-D).sum(axis=(-2,-1),dtype=np.int32)
        dy,dx=np.unravel_index(distances.argmin(),distances.shape)
        matches.append((float(distances[dy,dx])/D.size,seat,[int((x-30+dx+6)*2),int((y-22+dy+6)*2)]))
    matches.sort()
    score,seat,center=matches[0]
    return {"candidate":seat if score<=15 and matches[1][0]-score>=6 else None,
            "distance":round(score,2),"center":center if score<=15 else None,
            "verified":False}

def card_back(image,box):
    if box is None:return None
    a=np.asarray(image.crop(box),dtype=np.int16)
    r,g,b=np.moveaxis(a,-1,0)
    red=(r>125)&(r>g+55)&(r>b+45)
    return bool(red.mean()>.14 and (red.mean(1)>.12).mean()>.40)

def status_label(text):
    key=re.sub(r"[^A-Z]","",text.upper())
    labels={"ALLIN":"All-in","SATOUT":"Sat out","FOLD":"Fold","FOLDED":"Fold","CHECK":"Check","CALL":"Call","RAISE":"Raise","BET":"Bet","BIGBLIND":"Big blind","SMALLBLIND":"Small blind"}
    return labels.get(key)

def scan_labels(image,exe,number_text,cache=None):
    entries=[((seat,kind),REGIONS[seat][kind],kind) for seat in SEAT_ORDER for kind in ("bet","status")]
    rows,error=scan_regions(image,exe,entries,cache=cache)
    data={}
    for seat,kind in (entry[0] for entry in entries):
        words=rows.get((seat,kind),[])
        if kind=="bet":
            data[(seat,kind)]=select_amount(words,number_text)
        else:
            lines=text_lines(words)
            data[(seat,kind)]={"raw":" / ".join(" ".join(w["text"] for w in line) for line in lines),
                "confidence":round(min((w["confidence"] for w in words),default=-1),1)}
    return data,error

def participation_label(action,visible,turn=False):
    if action in ("Sat out","Fold"):
        return action
    if visible or turn or action in ("Check","Call","Raise","Bet","All-in","Big blind","Small blind"):
        return "Participation evidence"
    return "No participation detected"

def observe_table(image,exe,number_text,numbers,cues,hole,cache=None):
    labels,error=scan_labels(image,exe,number_text,cache=cache)
    dealer=dealer_marker(image)
    seats={}
    for seat in SEAT_ORDER:
        bet=labels.get((seat,"bet"),{})
        status=labels.get((seat,"status"),{})
        value=bet.get("candidate")
        action=status_label(status.get("raw","")) if status.get("confidence",-1)>=65 else None
        cue=cues["seats"].get(seat,{})
        if cue.get("all_in_label",{}).get("candidate") is True:
            action="All-in"
        back=card_back(image,REGIONS[seat]["back"])
        visible=any(c is not None for c in hole) if seat=="hero" else back
        seats[seat]={"stack":numbers.get(seat,{}).get("candidate"),
            "stack_raw":numbers.get(seat,{}).get("raw",""),
            "stack_confidence":numbers.get(seat,{}).get("ocr_confidence"),
            "bet":value,"bet_raw":bet.get("raw",""),"bet_confidence":bet.get("ocr_confidence"),
            "bet_text_bounds":bet.get("text_bounds"),
            "stack_text_bounds":numbers.get(seat,{}).get("text_bounds"),
            "status_candidate":action,"status_raw":status.get("raw",""),
            "card_visible_candidate":True if visible else None,
            "turn_candidate":cues.get("active_band_candidate")==seat,
            "dealer_candidate":dealer["candidate"]==seat,
            "participation_candidate":participation_label(action,visible,cues.get("active_band_candidate")==seat),
            "verified":False}
    return {"dealer":dealer,"turn_candidate":cues.get("active_band_candidate"),
            "seats":seats,"ocr_sampled":bool(exe),"ocr_warning":error,
            "note":"Displayed bets are candidates, not total committed chips. Missing cards or labels do not establish folds or departures."}
