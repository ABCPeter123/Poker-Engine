"""Offline saved-image corpus benchmark. No screen capture or game interaction."""
import argparse
from collections import Counter, defaultdict
import io
import json
import math
import hashlib
from pathlib import Path
import statistics
import time

from check_saved_frame import field_results

VARIANTS=("original","downscale","jpeg")
CARD_GROUPS=("hole_slots","board_slots")


def validate_manifest(data):
    cases=data.get("cases")
    if not isinstance(cases,list) or not cases:
        raise ValueError("Manifest must contain a nonempty cases array.")
    seen=set()
    for case in cases:
        if not isinstance(case,dict):
            raise ValueError("Every case must be an object.")
        name=case.get("file")
        if not isinstance(name,str) or not name or "/" in name or "\\" in name or name in (".","..") or Path(name).name!=name or name in seen:
            raise ValueError("Image names must be unique local filenames.")
        seen.add(name)
        expected=case.get("expected")
        if not isinstance(expected,dict):
            raise ValueError(f"{name}: missing expected observations")
        for key,length in (("hole_slots",2),("board_slots",5)):
            cards=expected.get(key)
            if not isinstance(cards,list) or len(cards)!=length:
                raise ValueError(f"{name}: {key} needs {length} entries including nulls")
            if any(c is not None and (not isinstance(c,str) or len(c)!=2 or c[0] not in "23456789TJQKA" or c[1] not in "cdhs") for c in cards):
                raise ValueError(f"{name}: invalid card label")
        known=[c for key in CARD_GROUPS for c in expected[key] if c is not None]
        if len(known)!=len(set(known)):
            raise ValueError(f"{name}: duplicate expected card")
    return cases


def transform(image, variant):
    from PIL import Image
    if variant=="original":
        return image
    if variant=="downscale":
        w,h=image.size
        return image.resize((max(100,round(w*.75)),max(100,round(h*.75)))).resize((w,h))
    if variant=="jpeg":
        with io.BytesIO() as data:
            image.save(data,format="JPEG",quality=65)
            data.seek(0)
            with Image.open(data) as compressed:
                return compressed.convert("RGB")
    raise ValueError("Unknown image variant")


def score(rows):
    counts=Counter()
    for row in rows:
        field=row["field"]
        card=field.startswith(("hole_slots[","board_slots["))
        group=("empty_slots" if row["expected"] is None else "visible_cards") if card else field.split(".")[0]
        counts[(group,row["status"])]+=1
    groups={}
    for group in sorted({g for g,_ in counts}):
        totals={key:counts[group,key] for key in ("match","missing","incorrect")}
        total=sum(totals.values())
        groups[group]={**totals,"total":total,"accuracy":totals["match"]/total if total else None}
    return groups


def evaluate_case(case,root,variants,ocr,enhanced=False):
    from PIL import Image
    from review import normalize, read_cards, review_image
    with Image.open(root/case["file"]) as raw:
        image=raw.convert("RGB")
    if "crop" in case:
        l,t,r,b=case["crop"]
        if not 0<=l<r<=image.width or not 0<=t<b<=image.height:
            raise ValueError("Saved screenshot crop outside image.")
        image=image.crop((l,t,r,b))
    expected=case["expected"] if ocr else {k:case["expected"][k] for k in CARD_GROUPS}
    digest=hashlib.sha256((root/case["file"]).read_bytes()).hexdigest()
    results=[]
    for variant in variants:
        t=time.perf_counter()
        normalized=normalize(transform(image,variant))
        if ocr:
            result=review_image(normalized,ocr,source="saved benchmark",enhanced=enhanced)
        elif enhanced:
            from saved_card_review import read_enhanced
            result=read_enhanced(normalized,read_cards)
        else:
            result=read_cards(normalized)
        results.append({"file":case["file"],"sha256":digest,"variant":variant,"elapsed_ms":round((time.perf_counter()-t)*1000,1),
                        "fields":field_results(result,expected)})
    return results


def summarize(results,errors):
    by_variant=defaultdict(list)
    for item in results:
        by_variant[item["variant"]].append(item)
    variants={}
    for variant,items in by_variant.items():
        times=sorted(i["elapsed_ms"] for i in items)
        variants[variant]={"frames":len(items),
            "exact_card_frames":sum(all(row["status"]=="match" for row in i["fields"] if row["field"].startswith(("hole_slots[","board_slots["))) for i in items),
            "median_ms":round(statistics.median(times),1),
            "p95_ms":times[max(0,math.ceil(.95*len(times))-1)],
            "groups":score([row for item in items for row in item["fields"]])}
    return {"frames_processed":len(results),"errors":errors,"variants":variants,"details":results}


def gate(report,min_card_accuracy,max_incorrect,max_p95_ms=None):
    if report["errors"] or not report["frames_processed"]:
        return False
    for variant in report["variants"].values():
        if max_p95_ms is not None and variant["p95_ms"]>max_p95_ms:
            return False
        groups=variant["groups"]
        cards=groups.get("visible_cards")
        if not cards or cards["accuracy"]<min_card_accuracy:
            return False
        if sum(g["incorrect"] for g in groups.values())>max_incorrect:
            return False
        if any(g["missing"] or g["incorrect"] for name,g in groups.items() if name!="visible_cards"):
            return False
    return True


def compare_reports(current,baseline):
    """Compare paired fields only if their source image bytes and labels match."""
    def index(report):
        out={}
        for frame in report.get("details",[]):
            for row in frame["fields"]:
                key=(frame["file"],frame["variant"],row["field"])
                if key in out:
                    raise ValueError("Duplicate report field")
                out[key]=(frame.get("sha256"),row)
        return out
    old,new=index(baseline),index(current)
    improved=[];regressed=[];changed_wrong=[];unpaired=[]
    for key in sorted(set(old)|set(new)):
        a,b=old.get(key),new.get(key)
        if not a or not b or not a[0] or a[0]!=b[0] or a[1]["expected"]!=b[1]["expected"]:
            unpaired.append(list(key))
            continue
        before,after=a[1],b[1]
        entry={"file":key[0],"variant":key[1],"field":key[2],"expected":before["expected"],
               "before":before["actual"],"after":after["actual"]}
        if before["status"]=="match" and after["status"]!="match":
            regressed.append(entry)
        elif before["status"]!="match" and after["status"]=="match":
            improved.append(entry)
        elif before["status"]!="incorrect" and after["status"]=="incorrect":
            changed_wrong.append(entry)
    return {"improved":improved,"regressed":regressed,"new_incorrect":changed_wrong,"unpaired":unpaired,
            "passed":bool(old) and not regressed and not changed_wrong and not unpaired}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images",type=Path,help="Local directory containing original saved images")
    parser.add_argument("--manifest",type=Path,default=Path(__file__).with_name("fixtures")/"saved_corpus.json")
    parser.add_argument("--output",type=Path,default=Path("saved-benchmark.json"))
    parser.add_argument("--variants",nargs="+",choices=VARIANTS,default=list(VARIANTS))
    parser.add_argument("--ocr",action="store_true",help="Include numeric and seat observations; requires installed Tesseract")
    parser.add_argument("--enhanced",action="store_true",help="Test optional saved-image multi-view card recovery")
    parser.add_argument("--min-card-accuracy",type=float,default=1.0)
    parser.add_argument("--max-incorrect",type=int,default=0)
    parser.add_argument("--max-p95-ms",type=float,help="Optional latency gate, measured per variant")
    parser.add_argument("--baseline",type=Path,help="Require no field-level regressions against an earlier report with the same image hashes")
    args=parser.parse_args()
    if not 0<=args.min_card_accuracy<=1 or args.max_incorrect<0 or (args.max_p95_ms is not None and (not math.isfinite(args.max_p95_ms) or args.max_p95_ms<=0)):
        parser.error("Invalid quality thresholds.")
    if len(set(args.variants))!=len(args.variants):
        parser.error("Choose each variant at most once.")
    cases=validate_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    exe=None
    if args.ocr:
        from ocr_runtime import resolve_tesseract
        exe,error=resolve_tesseract()
        if not exe:
            parser.error(error)
    results=[];errors=[]
    for case in cases:
        try:
            results.extend(evaluate_case(case,args.images,args.variants,exe,args.enhanced))
        except Exception as exc:
            errors.append({"file":case["file"],"error":str(exc)})
    report=summarize(results,errors)
    report["reader_mode"]="enhanced" if args.enhanced else "baseline"
    report["expected_frames"]=len(cases)*len(args.variants)
    report["passed"]=report["frames_processed"]==report["expected_frames"] and gate(report,args.min_card_accuracy,args.max_incorrect,args.max_p95_ms)
    if args.baseline:
        baseline=json.loads(args.baseline.read_text(encoding="utf-8"))
        report["comparison"]=compare_reports(report,baseline)
        report["passed"]=report["passed"] and report["comparison"]["passed"]
    args.output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="details"},indent=2))
    return 0 if report["passed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
