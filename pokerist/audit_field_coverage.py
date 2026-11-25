"""Audit field completeness of an existing completed-image benchmark report.

No image processing, capture, scheduling, or recommendation integration.
A field not manually labelled is untested, not correct.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

SEATS=("hero","left","upper_left","upper_right","right")
FIELDS=tuple([f"amount.{s}" for s in SEATS]+[f"bet.{s}" for s in SEATS]+
             ["dealer","turn"]+[f"board_slots[{i}]" for i in range(5)]+
             [f"hole_slots[{i}]" for i in range(2)]+["amount.pot"])
STATUSES=("match","missing","incorrect","untested")

def audit(report):
    frames=report.get("details",[])
    if not isinstance(frames,list):
        raise ValueError("Expected existing saved benchmark details")
    variants={}
    seen=set()
    for frame in frames:
        variant=frame["variant"]
        identity=(variant,frame["file"])
        if identity in seen:
            raise ValueError("Duplicate benchmark frame")
        seen.add(identity)
        v=variants.setdefault(variant,{"frames":0,"complete_matches":0,
             "fully_labelled_frames":0,"fields":{f:Counter() for f in FIELDS},
             "durations":[],"errors":0})
        v["frames"]+=1
        rows={}
        for row in frame["fields"]:
            field=row["field"]
            if field not in FIELDS:
                continue
            if field in rows or row["status"] not in STATUSES[:3]:
                raise ValueError("Duplicate field or invalid status")
            if "expected" not in row or "actual" not in row:
                raise ValueError("Field row lacks expected or actual evidence")
            a,e=row["actual"],row["expected"]
            if row["status"]=="match" and (type(a) is not type(e) or a!=e):
                raise ValueError("Field marked match despite conflicting evidence")
            rows[field]=row["status"]
        for f in FIELDS:
            v["fields"][f][rows.get(f,"untested")]+=1
        v["fully_labelled_frames"]+=len(rows)==len(FIELDS)
        v["complete_matches"]+=len(rows)==len(FIELDS) and all(s=="match" for s in rows.values())
        elapsed=frame.get("elapsed_ms")
        if type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>0:
            v["durations"].append(elapsed)
        v["errors"]+=bool(frame.get("ocr_error"))
    for v in variants.values():
        n=v["frames"]
        for field,counter in v["fields"].items():
            tested=n-counter["untested"]
            v["fields"][field]={**{s:counter[s] for s in STATUSES},
                "label_coverage":tested/n,
                "accuracy_when_tested":counter["match"]/tested if tested else None}
        durations=v.pop("durations")
        v["timed_frames"]=len(durations)
        v["mean_reported_ms"]=sum(durations)/len(durations) if durations else None
        v["sequential_equivalent_fps"]=1000*len(durations)/sum(durations) if durations else None
        v["all_fields_validated"]=v["complete_matches"]==n and not v["errors"]
    return {"scope":"Existing completed-image benchmark reports only",
            "field_count":len(FIELDS),"variants":variants,
            "benchmark_errors":report.get("errors",[]),
            "complete_validation":bool(variants) and not report.get("errors") and
                 report.get("expected_frames")==len(frames) and
                 all(v["all_fields_validated"] for v in variants.values()),
            "limitations":["Reported duration excludes some input/output and video decode costs.",
                           "Sequential equivalent FPS is not measured sustained capture throughput.",
                           "Unlabelled fields cannot establish recognition accuracy."]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("benchmark",type=Path)
    p.add_argument("--output",type=Path,default=Path("field-coverage.json"))
    args=p.parse_args()
    result=audit(json.loads(args.benchmark.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(result,indent=2))
    return 0 if result["complete_validation"] else 1

if __name__=="__main__":
    raise SystemExit(main())
