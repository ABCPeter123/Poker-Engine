"""Evaluate avatar appearance on completed screenshots, not gameplay participation."""
import argparse,json
from pathlib import Path
from collections import Counter
from PIL import Image
from offline_font_review import read_image
from seat_cues import SEATS,pixels,avatar_appearance
def audit(root,manifest,width=1536):
    rows=[]
    for frame in manifest["frames"]:
        image=Image.fromarray(read_image(root,frame["file"],manifest.get("image_sha256",{})))
        if width!=1536:image=image.resize((width,round(709*width/1536))).resize((1536,709))
        for seat,expected in frame.get("avatar_appearance",{}).items():
            observed=avatar_appearance(pixels(image,SEATS[seat]["avatar"]))
            candidate=observed["candidate"]
            rows.append({"file":frame["file"],"seat":seat,"expected":expected,"observed":observed,
                         "status":"correct" if candidate==expected else "unknown" if candidate=="unknown" else "incorrect"})
    return {"width":width,"scope":"Development-set appearance classification, not verified participant count",
            "scores":dict(Counter(r["status"] for r in rows)),"details":rows}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("images",type=Path);p.add_argument("manifest",type=Path)
    p.add_argument("--width",type=int,choices=(1536,960,720,480),default=1536)
    p.add_argument("--output",type=Path,default=Path("avatar-appearance-report.json"))
    a=p.parse_args();r=audit(a.images,json.loads(a.manifest.read_text(encoding="utf-8")),a.width)
    a.output.write_text(json.dumps(r,indent=2),encoding="utf-8");print(json.dumps({k:v for k,v in r.items() if k!="details"},indent=2))
if __name__=="__main__":main()
