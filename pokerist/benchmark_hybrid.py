"""Controlled offline text recognition comparison, never a real screenshot accuracy claim."""
import argparse
import json
import os
from pathlib import Path
os.environ.setdefault("OMP_THREAD_LIMIT","1")
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from hybrid_amount_audit import measure
from ocr_runtime import resolve_tesseract

# Groups differ in rendering conditions; none contributes its own templates.
CONDITIONS=(
    (18,0.0,0.0,1.0),
    (22,0.4,1.5,1.0),
    (16,0.65,2.0,1.0),
    (20,0.35,2.5,0.8),
)
# Fixed disjoint labels deliberately include every digit and several suffixes.
LABELS=(
    ("0123456789","97531","24680","12345","67890","1.5K","2.4M","100"),
    ("9876543210","10239","45678","25000","93841","2.5K","4.6M","907"),
    ("2468013579","98712","30456","13679","82405","3.5K","6.7M","410"),
    ("1357924680","86420","97514","52136","70893","4.5K","8.9M","305"),
)
def render(text,condition,seed):
    size,blur,noise,scale=condition
    font=ImageFont.load_default(size=size)
    bounds=font.getbbox(text)
    im=Image.new("L",(bounds[2]-bounds[0]+16,bounds[3]-bounds[1]+12),32)
    ImageDraw.Draw(im).text((8-bounds[0],6-bounds[1]),text,font=font,fill=242)
    if scale!=1:
        im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
    if blur:im=im.filter(ImageFilter.GaussianBlur(blur))
    a=np.asarray(im,dtype=float)
    if noise:a+=np.random.default_rng(seed).normal(0,noise,a.shape)
    return np.clip(a,0,255)

def synthetic_samples():
    return [(f"render-{g}",label,render(label,condition,100*g+i),f"line-{i}")
            for g,condition in enumerate(CONDITIONS) for i,label in enumerate(LABELS[g])]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=Path("synthetic-hybrid-validation.json"))
    args=p.parse_args()
    exe,error=resolve_tesseract()
    if not exe:p.error(error)
    report=measure(synthetic_samples(),exe)
    report["scope"]="Synthetic text crops; disjoint labels and rendering groups; not game font or live accuracy"
    report["real_frame_accuracy_verified"]=False
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="details"},indent=2))

if __name__=="__main__":main()
