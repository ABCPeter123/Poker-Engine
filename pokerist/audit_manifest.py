"""Audit explicit ground-truth coverage before running saved-image recognition.

No live capture or automatic labelling. Missing labels stay missing.
"""
import argparse
import json
from pathlib import Path
from benchmark_saved_frames import validate_manifest
from audit_field_coverage import FIELDS

def labelled_fields(expected):
    return ({f"{group}[{i}]" for group in ("hole_slots","board_slots")
             for i in range(len(expected.get(group,[])))}
            | {f"amount.{key}" for key in expected.get("amounts",{})}
            | {f"bet.{key}" for key in expected.get("bets",{})}
            | {key for key in ("dealer","turn") if key in expected})

def audit_manifest(manifest):
    cases=validate_manifest(manifest)
    counts=dict.fromkeys(FIELDS,0)
    missing=[]
    for case in cases:
        present=labelled_fields(case["expected"])
        for field in present:
            counts[field]+=1
        absent=[field for field in FIELDS if field not in present]
        if absent:
            missing.append({"file":case["file"],"missing_labels":absent})
    total=len(FIELDS)*len(cases)
    labelled=sum(counts.values())
    return {"frames":len(cases),"fields_per_frame":len(FIELDS),
            "possible_labels":total,"labelled":labelled,"unlabelled":total-labelled,
            "label_coverage":labelled/total,
            "fields":{field:{"labelled":n,"unlabelled":len(cases)-n} for field,n in counts.items()},
            "fully_labelled_frames":len(cases)-len(missing),
            "missing_by_file":missing,
            "complete":labelled==total,
            "recognition_accuracy_verified":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,default=Path(__file__).with_name("fixtures")/"saved_corpus.json")
    p.add_argument("--output",type=Path,default=Path("manifest-coverage.json"))
    a=p.parse_args()
    report=audit_manifest(json.loads(a.manifest.read_text(encoding="utf-8")))
    a.output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="missing_by_file"},indent=2))
    return 0 if report["complete"] else 1

if __name__=="__main__":
    raise SystemExit(main())
