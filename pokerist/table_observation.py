"""Read-only visual observations for saved hands or authorized practice."""
import re
import tempfile
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view

SEAT_ORDER=("hero","left","upper_left","upper_right","right")
# Normalized 1536x709 coordinates. Other seats/layouts are not calibrated.
REGIONS={
 "hero":{"bet":(770,410,875,467),"status":(655,566,795,588),"back":None},
 "left":{"bet":(440,274,564,330),"status":(285,437,410,460),"back":(411,326,466,376)},
 "upper_left":{"bet":(495,184,604,238),"status":(490,142,625,165),"back":(620,143,675,191)},
 "upper_right":{"bet":(830,184,951,238),"status":(915,142,1048,165),"back":(858,143,912,191)},
 "right":{"bet":(988,274,1118,330),"status":(1128,437,1260,460),"back":(1070,326,1126,376)}
}
ANCHORS={"upper_left":(350,95),"upper_right":(418,95),"left":(241,175),"right":(527,175),"hero":(405,205)}
D=np.array([142,144,145,146,151,157,156,148,141,139,140,140,139,144,142,144,168,197,207,207,202,180,152,138,137,138,140,148,182,208,212,212,215,219,218,199,164,139,139,145,183,215,210,136,105,104,105,164,216,199,160,138,155,207,226,194,100,129,165,120,112,182,225,184,138,160,210,227,178,104,183,243,195,112,150,234,194,142,160,210,226,164,104,187,245,204,117,148,232,193,144,153,206,220,148,93,149,183,139,108,167,225,188,141,143,190,211,154,115,126,133,120,143,198,208,166,138,134,149,188,189,182,183,186,191,208,209,168,136,140,135,118,141,175,190,197,197,193,185,161,129,128,141,139,132,117,114,124,132,133,129,117,112,124,141,142,140,141,139,126,107,98,98,103,115,131,140,141,141],dtype=np.int16).reshape(13,13)

def dealer_marker(image):
    a=np.asarray(image.resize((768,355)).convert("L"),dtype=np.int16)
    matches=[]
    for seat,(x,y) in ANCHORS.items():
        windows=sliding_window_view(a[y-22:y+23,x-30:x+31],(13,13))
        distances=np.abs(windows-D).mean(axis=(-2,-1))
        dy,dx=np.unravel_index(distances.argmin(),distances.shape)
        matches.append((float(distances[dy,dx]),seat,[int((x-30+dx+6)*2),int((y-22+dy+6)*2)]))
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

def scan_labels(image,exe):
    if not exe:return {}, "Tesseract is unavailable"
    entries=[(seat,kind,REGIONS[seat][kind]) for seat in SEAT_ORDER for kind in ("bet","status")]
    canvas=Image.new("L",(560,240*len(entries)),255)
    for i,(seat,kind,box) in enumerate(entries):
        a=np.asarray(image.crop(box),dtype=np.int16)
        r,g,b=np.moveaxis(a,-1,0)
        # Bet labels are white; seat status labels are amber/yellow.
        if kind=="bet":
            mask=(a.min(2)>170)&(np.ptp(a,axis=2)<45)
        else:
            mask=(r>145)&(g>115)&(b<np.minimum(r,g)-35)
        crop=Image.fromarray(np.uint8(255-255*mask))
        crop=crop.resize((crop.width*4,crop.height*4))
        canvas.paste(crop,(12,i*240+6))
    try:
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"labels.png";canvas.save(p)
            result=subprocess.run([exe,str(p),"stdout","--psm","11","tsv"],capture_output=True,text=True,timeout=12,check=True)
        rows={i:[] for i in range(len(entries))}
        for line in result.stdout.splitlines()[1:]:
            c=line.split("\t",11)
            if len(c)!=12 or c[0]!="5" or not c[11].strip():continue
            row=(int(c[7])+int(c[9])//2)//240
            if row in rows:rows[row].append((int(c[6]),c[11],float(c[10])))
        data={}
        for i,(seat,kind,_) in enumerate(entries):
            words=sorted(rows[i])
            data[(seat,kind)]={"raw":" ".join(w[1] for w in words),"confidence":round(min((w[2] for w in words),default=-1),1)}
        return data,None
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        return {},str(exc)

def observe_table(image,exe,number_text,numbers,cues,hole):
    labels,error=scan_labels(image,exe)
    dealer=dealer_marker(image)
    seats={}
    for seat in SEAT_ORDER:
        bet=labels.get((seat,"bet"),{})
        status=labels.get((seat,"status"),{})
        value=number_text(bet.get("raw","")) if bet.get("confidence",-1)>=75 else None
        action=status_label(status.get("raw","")) if status.get("confidence",-1)>=65 else None
        cue=cues["seats"].get(seat,{})
        if cue.get("all_in_label",{}).get("candidate") is True:
            action="All-in"
        back=card_back(image,REGIONS[seat]["back"])
        visible=any(c is not None for c in hole) if seat=="hero" else back
        seats[seat]={"stack":numbers.get(seat,{}).get("candidate"),
            "stack_raw":numbers.get(seat,{}).get("raw",""),
            "bet":value,"bet_raw":bet.get("raw",""),"bet_confidence":bet.get("confidence"),
            "status_candidate":action,"status_raw":status.get("raw",""),
            "card_visible_candidate":True if visible else None,
            "turn_candidate":cues.get("active_band_candidate")==seat,
            "dealer_candidate":dealer["candidate"]==seat,
            "participation_candidate":"Sat out" if action=="Sat out" else "Fold" if action=="Fold" else "Cards visible" if visible else None,
            "verified":False}
    return {"dealer":dealer,"turn_candidate":cues.get("active_band_candidate"),
            "seats":seats,"ocr_sampled":bool(exe),"ocr_warning":error,
            "note":"Displayed bets are candidates, not total committed chips. Missing cards or labels do not establish folds or departures."}
