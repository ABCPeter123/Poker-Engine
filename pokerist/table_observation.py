"""Read-only visual observations for saved hands or authorized practice."""
import re
import tempfile
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view
from adaptive_labels import scan_regions, select_amount, text_lines
from calibrated_amounts import BET_KEYS, candidate as font_amount, combine as combine_amount

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

def dealer_marker(image,cache=None):
    a=np.asarray(image.resize((768,355)).convert("L"),dtype=np.int16)
    matches=[]
    if cache is not None and not hasattr(cache,"dealer_regions"):
        cache.dealer_regions={}
    for seat,(x,y) in ANCHORS.items():
        region=a[y-22:y+23,x-30:x+31]
        signature=region.tobytes() if cache is not None else None
        prior=cache.dealer_regions.get(seat) if cache is not None else None
        if prior is not None and prior[0]==signature:
            matches.append(prior[1])
            continue
        windows=sliding_window_view(region,(13,13))
        distances=np.abs(windows-D).sum(axis=(-2,-1),dtype=np.int32)
        dy,dx=np.unravel_index(distances.argmin(),distances.shape)
        reading=(float(distances[dy,dx])/D.size,seat,[int((x-30+dx+6)*2),int((y-22+dy+6)*2)])
        if cache is not None:
            cache.dealer_regions[seat]=(signature,reading)
        matches.append(reading)
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
    labels={"ALLIN":"All-in","SATOUT":"Sat out","FOLD":"Fold","FOLDED":"Fold","CHECK":"Check","CALL":"Call","RAISE":"Raise","BET":"Bet","BIGBLIND":"Big blind","SMALLBLIND":"Small blind","ANTE":"Ante"}
    return labels.get(key)

# Normalized wager-chip positions in the five-seat layout. White rim pips
# occur around a real chip; isolated OCR ink from cards/avatars does not.
CHIP_CENTERS={"hero":(815,438),"left":(465,307),"upper_left":(536,211),"upper_right":(999,211),"right":(1073,308)}
_yy,_xx=np.indices((37,37))
_radius=np.hypot(_xx-18,_yy-18)
_annulus=(_radius>=10)&(_radius<=16)
_angles=(np.arctan2(_yy-18,_xx-18)+np.pi)/(2*np.pi)
_sectors=tuple(_annulus&(_angles>=i/8)&(_angles<(i+1)/8) for i in range(8))

def wager_chip_present(image,seat):
    x,y=CHIP_CENTERS[seat]
    a=np.asarray(image.crop((x-18,y-18,x+19,y+19)),dtype=np.int16)
    lo=a.min(2);hi=a.max(2)
    white=(lo>145)&(hi-lo<65)
    return bool((white&_annulus).sum()>=30 and
                sum((white&sector).sum()>=3 for sector in _sectors)>=5)

def scan_labels(image,exe,number_text,cache=None):
    chips={seat:wager_chip_present(image,seat) for seat in SEAT_ORDER}
    entries=[((seat,kind),REGIONS[seat][kind],kind) for seat in SEAT_ORDER for kind in ("bet","status") if kind=="status" or chips[seat]]
    rows,error=scan_regions(image,exe,entries,cache=cache)
    data={}
    for seat in SEAT_ORDER:
        if not chips[seat]:
            data[(seat,"bet")]={"candidate":None,"chip_present":False,"raw":"","warning":"No wager chip evidence"}
    for seat,kind in (entry[0] for entry in entries):
        words=rows.get((seat,kind),[])
        if kind=="bet":
            primary=select_amount(words,number_text)
            glyph,bounds=font_amount(image,BET_KEYS[seat],cache) if exe else (None,None)
            data[(seat,kind)]={**combine_amount(primary,glyph,bounds),"chip_present":True}
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

def call_prompt(text,confidence,parse):
    # The central CALL ... or RAISE prompt is distinct from pre-action
    # checkboxes. Do not infer a price from a bare "Call" label.
    if not np.isfinite(confidence) or confidence<75:return None
    if re.fullmatch(r"\s*CHECK\s+OR\s+RAISE\s*",text.upper()):
        return {**parse("0"),"source":"explicit check prompt"}
    m=re.fullmatch(r"\s*CALL\s*[^A-Z0-9]*\s*([0-9][0-9 ,.]*[KM]?)\s+OR\s+RAISE\s*",text.upper())
    if not m:return None
    c=parse(m.group(1).strip())
    return c if c and not c.get("approximate") else None

def action_prompt_panel(image):
    # The central blue prompt has two long pale horizontal borders.
    # Excludes the narrow hand-strength banner and ordinary felt.
    a=np.asarray(image.crop((630,382,907,424)),dtype=np.int16)
    r,g,b=np.moveaxis(a,-1,0)
    pale=(a.min(2)>105)&(a.max(2)-a.min(2)<65)
    blue=(b>r+35)&(b>g+10)&(r<75)&(g<130)
    return bool(pale[:10].sum(1).max()>=200 and
                pale[-10:].sum(1).max()>=200 and
                blue[9:-9,10:-10].mean()>.35)

def read_call_prompt(image,exe,number_text,cache=None):
    key="hero_call_prompt"
    rows,error=scan_regions(image,exe,[(key,(635,391,904,415),"prompt")],unrestricted=True,cache=cache)
    words=rows.get(key,[])
    lines=text_lines(words)
    raw=" / ".join(" ".join(w["text"] for w in line) for line in lines)
    confidence=min((w["confidence"] for w in words),default=-1)
    return {"candidate":call_prompt(raw,confidence,number_text),"raw":raw,"confidence":confidence,"warning":error}

def observe_table(image,exe,number_text,numbers,cues,hole,cache=None):
    labels,error=scan_labels(image,exe,number_text,cache=cache)
    dealer=dealer_marker(image,cache=cache)
    ring=cues.get("active_band_candidate")
    visible_hero=any(c is not None for c in hole)
    panel=visible_hero and action_prompt_panel(image)
    # A complete explicit prompt can corroborate a missing ring, but cannot
    # override another seat's ring or a simultaneous ring conflict.
    prompt=read_call_prompt(image,exe,number_text,cache) if exe and panel and ring in (None,"hero") and not cues.get("active_band_conflict") else None
    turn=ring
    source="ring" if ring else None
    if visible_hero and prompt and prompt.get("candidate") is not None and turn is None:
        turn="hero"
        source="explicit action prompt"
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
            "bet":value,"bet_raw":bet.get("raw",""),"bet_chip_present":bet.get("chip_present"),
            "bet_font_candidate":bet.get("font_candidate"),"bet_reader_conflict":bool(bet.get("reader_conflict")),
            "stack_font_candidate":numbers.get(seat,{}).get("font_candidate"),"stack_reader_conflict":bool(numbers.get(seat,{}).get("reader_conflict")),"bet_confidence":bet.get("ocr_confidence"),
            "bet_text_bounds":bet.get("text_bounds"),
            "stack_text_bounds":numbers.get(seat,{}).get("text_bounds"),
            "status_candidate":action,"status_raw":status.get("raw",""),
            "card_visible_candidate":True if visible else None,
            "turn_candidate":turn==seat,
            "dealer_candidate":dealer["candidate"]==seat,
            "participation_candidate":participation_label(action,visible,turn==seat),
            "verified":False}
    return {"dealer":dealer,"turn_candidate":turn,"turn_source":source,"hero_call_prompt":prompt,"hero_prompt_panel":panel,
            "seats":seats,"ocr_sampled":bool(exe),"ocr_warning":error,
            "note":"Displayed bets are candidates, not total committed chips. Missing cards or labels do not establish folds or departures."}
