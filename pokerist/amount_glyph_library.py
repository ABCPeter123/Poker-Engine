"""Build and evaluate digit templates using labelled completed screenshots only.

A template library is not a trained/validated model until independent
unlabelled-at-inference crops have been evaluated. Keep image pixels local.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
from glyph_audit import read_samples, feature, segment
from automatic_glyph_audit import fit_amount, predict_amount, amount_audit
from amount_text import number_text

def build_library(samples):
    library=fit_amount(samples)
    entries=[]
    for label,item in library:
        if item is None or label not in "0123456789.KkMm,":
            continue
        pixels,aspect=item
        entries.append({"label":label,"aspect":float(aspect),
                        "pixels":np.rint(pixels*255).astype(np.uint8).ravel().tolist()})
    counts=Counter(e["label"] for e in entries)
    return {"format":1,"feature_size":[24,16],"templates":entries,
            "counts":dict(sorted(counts.items())),
            "missing_digits":sorted(set("0123456789")-set(counts)),
            "source_groups":sorted({s[0] for s in samples}),
            "validated_for_automatic_full_screen":False}

def decode_library(model):
    if model.get("format")!=1 or model.get("feature_size")!=[24,16]:
        raise ValueError("Unsupported glyph library")
    entries=model.get("templates",[])
    if not isinstance(entries,list) or len(entries)>10000:
        raise ValueError("Invalid template count")
    output=[]
    for e in entries:
        label=e["label"];p=np.asarray(e["pixels"],dtype=float);aspect=float(e["aspect"])
        if len(label)!=1 or label not in "0123456789.KkMm," or p.shape!=(384,) or not np.isfinite(p).all() or (p<0).any() or (p>255).any() or not np.isfinite(aspect) or aspect<=0:
            raise ValueError("Invalid glyph entry")
        output.append((label,(p.reshape(24,16)/255,aspect)))
    return output

def evaluate_and_build(samples):
    groups={s[0] for s in samples}
    if len(groups)<2:raise ValueError("At least two independent source groups required")
    audit=amount_audit(samples)
    model=build_library(samples)
    model["held_out_crop_audit"]={k:v for k,v in audit.items() if k!="details"}
    model["scope"]="Manually localized completed-image crops; group-held-out segmentation and recognition, not full-screen accuracy"
    return model,audit

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("images",type=Path,help="Directory containing original saved screenshots")
    p.add_argument("--manifest",type=Path,default=Path(__file__).parent/"fixtures"/"glyph_amount_crops.json")
    p.add_argument("--output",type=Path,default=Path("local-amount-glyphs.json"))
    p.add_argument("--report",type=Path,default=Path("amount-glyph-validation.json"))
    args=p.parse_args()
    raw=args.manifest.read_bytes()
    manifest=json.loads(raw)
    missing=sorted({line["file"] for line in manifest["lines"] if not (args.images/line["file"]).is_file()})
    if missing:p.error("Missing original image files: "+", ".join(missing))
    samples=read_samples(args.images,manifest)
    model,audit=evaluate_and_build(samples)
    model["manifest_sha256"]=hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(model,separators=(",",":"),allow_nan=False),encoding="utf-8")
    args.report.write_text(json.dumps(audit,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps({k:v for k,v in model.items() if k!="templates"},indent=2))
    return 0 if not model["missing_digits"] and audit["incorrect"]==0 and audit["missing"]==0 else 1

if __name__=="__main__":
    raise SystemExit(main())
