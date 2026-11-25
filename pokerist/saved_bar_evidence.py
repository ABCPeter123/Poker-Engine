"""Preserve bottom-bar evidence from a completed-hand saved screenshot.

No live integration. Raw text may describe inactive or preselected controls.
Never interpret a word as proof of a legal action.
"""
import argparse
import io
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageOps


def evidence_crop(image, box=None):
    w,h=image.size
    box=tuple(box) if box is not None else (0,round(h*.84),w,round(h*.96))
    if len(box)!=4 or not (0<=box[0]<box[2]<=w and 0<=box[1]<box[3]<=h):
        raise ValueError("Crop must be within the supplied screenshot")
    return image.crop(box).convert("RGB"),box


def raw_passes(crop, executable):
    gray=ImageOps.autocontrast(crop.convert("L"))
    gray=gray.resize((gray.width*4,gray.height*4),Image.Resampling.LANCZOS)
    readings=[]
    with io.BytesIO() as buf:
        gray.save(buf,format="PNG")
        data=buf.getvalue()
    for psm in (7,11):
        try:
            proc=subprocess.run([executable,"stdin","stdout","--psm",str(psm)],
                                input=data,capture_output=True,check=True,timeout=5)
            readings.append({"psm":psm,"raw":proc.stdout.decode("utf-8",errors="replace").strip()})
        except (OSError,subprocess.SubprocessError) as exc:
            readings.append({"psm":psm,"raw":"","error":str(exc)[:300]})
    return readings


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("image",type=Path)
    p.add_argument("--crop",type=int,nargs=4,metavar=("LEFT","TOP","RIGHT","BOTTOM"),
                   help="Specify pixel bounds if the file contains window chrome or other UI")
    p.add_argument("--tesseract",default="tesseract")
    p.add_argument("--output",type=Path,default=Path("bar-evidence"))
    args=p.parse_args()
    with Image.open(args.image) as im:
        crop,box=evidence_crop(im,args.crop)
    args.output.mkdir(parents=True,exist_ok=True)
    crop.save(args.output/"original-crop.png")
    report={"source":args.image.name,"crop":list(box),"raw_readings":raw_passes(crop,args.tesseract),
            "verified":False,"limitations":["Text may be occluded, inactive, or part of a preselection control.",
                "No legal actions or amounts are inferred from this evidence."]}
    (args.output/"evidence.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
