"""Evaluate completed dashboard screenshots using the upright board classifier."""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image
from upright_board import upright_board_card
def audit(root,manifest):
    rows=[]
    for frame in manifest["frames"]:
        path=root/frame["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=frame["sha256"]:raise ValueError("Image mismatch: "+frame["file"])
        with Image.open(path) as im:
            im=im.convert("RGB").crop(frame["crop"]).resize((1536,709),Image.Resampling.BILINEAR)
        for i,expected in enumerate(frame["board"]):
            found=upright_board_card(im,i)
            rows.append({"file":frame["file"],"slot":i,"expected":expected,"predicted":found["candidate"] if found else None,"calibration":i in frame.get("calibration_slots",[])})
    return rows
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("images",type=Path);p.add_argument("--manifest",type=Path,default=Path(__file__).parent/"fixtures"/"dashboard_board_nov25.json");a=p.parse_args()
    rows=audit(a.images,json.loads(a.manifest.read_text(encoding="utf-8")));print(json.dumps(rows,indent=2));return 0 if all(r["expected"]==r["predicted"] for r in rows) else 1
if __name__=="__main__":raise SystemExit(main())
