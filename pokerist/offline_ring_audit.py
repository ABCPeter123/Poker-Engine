"""Saved-image visual marker diagnostic. No live tracking or recommendations."""
import argparse,json
from pathlib import Path
from collections import Counter
import numpy as np
from offline_font_review import read_image
BOXES={'hero':(652,536,795,569),'left':(278,399,416,438),'upper_left':(493,110,634,145),'upper_right':(904,109,1043,145),'right':(1118,399,1264,438)}
def markers(rgb):
    active=[];winner=[];evidence={}
    for seat,(x,y,X,Y) in BOXES.items():
        r,g,b=np.moveaxis(rgb[y:Y,x:X].astype(np.int16),-1,0)
        green=(g>165)&(g-r>25)&(g-b>45)
        gold=(r>160)&(g>110)&(r-b>60)&(g-b>50)&(r-g<100)
        n=int(green.sum());k=int(gold.sum());span=int((gold.sum(0)>=2).sum())
        evidence[seat]={"green_pixels":n,"gold_pixels":k,"gold_columns":span}
        if n>=100 and k>=200:active.append(seat)
        if n<20 and k>=1000 and span>=100:winner.append(seat)
    return {"active":active[0] if len(active)==1 else None,"winner_ring":winner[0] if len(winner)==1 else None,"evidence":evidence}
def audit(root,m):
    scores={key:Counter() for key in ("active","winner_ring")};rows=[]
    for row in m["frames"]:
        r=markers(read_image(root,row["file"],m.get("image_sha256",{})))
        for k in scores:
            truth=row[k];v=r[k];scores[k]["correct" if v==truth else "unknown" if v is None else "incorrect"]+=1
        rows.append({"file":row["file"],"expected":{k:row[k] for k in scores},"result":r})
    return {"scope":"Development-set ring diagnostic; thresholds inspected on same images, not independent accuracy","scores":{k:dict(v) for k,v in scores.items()},"details":rows}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("images",type=Path);p.add_argument("manifest",type=Path);p.add_argument("--output",type=Path,default=Path("offline-ring-report.json"));a=p.parse_args();r=audit(a.images,json.loads(a.manifest.read_text(encoding="utf-8")));a.output.write_text(json.dumps(r,indent=2),encoding="utf-8");print(json.dumps({k:v for k,v in r.items() if k!="details"},indent=2))
if __name__=="__main__":main()
