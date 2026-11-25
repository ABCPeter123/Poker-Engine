"""Offline OCR evaluation: measure transcription, acceptance and uncertainty separately."""
from collections import Counter
from amount_text import number_text
from check_saved_frame import chip_value

def numeric_evidence(result, expected):
    rows=[]
    for field,wanted in expected.get("amounts",{}).items():
        observation=(result.get("number_candidates") or {}).get(field) or {}
        candidate=observation.get("candidate")
        conflict=observation.get("saved_line_status")=="conflicting readings"
        def classify(value):
            return "missing" if value is None else "match" if value==wanted else "incorrect"
        def reading(method,raw,confidence=None):
            parsed=number_text(raw)
            value=parsed["value"] if parsed else None
            return {"method":method,"raw":raw,"confidence":confidence,"value":value,
                    "approximate":parsed.get("approximate") if parsed else None,
                    "status":classify(value)}
        readings=[reading("primary",observation.get("raw",""),observation.get("ocr_confidence"))]
        if "alternate_raw" in observation:
            readings.append(reading("alternate",observation["alternate_raw"],observation.get("alternate_confidence")))
        for item in observation.get("saved_line_evidence",[]):
            method=item.get("method") or "threshold_"+str(item.get("threshold","unknown"))
            readings.append(reading(method,item.get("raw",""),item.get("confidence")))
        accepted=chip_value(candidate) if not conflict else None
        rows.append({"field":field,"expected_display_value":wanted,"accepted":accepted,
                     "accepted_status":classify(accepted),"conflict":conflict,
                     "accepted_approximate":bool(candidate.get("approximate")) if accepted is not None else None,
                     "readings":readings})
    return rows

def summarize_numeric(rows):
    accepted=Counter(row["accepted_status"] for row in rows)
    raw={}
    for row in rows:
        for r in row["readings"]:
            raw.setdefault(r["method"],Counter())[r["status"]]+=1
    def counts(counter):
        total=sum(counter.values())
        return {**{k:counter[k] for k in ("match","missing","incorrect")},
                "total":total,"accuracy":counter["match"]/total if total else None}
    return {"accepted":counts(accepted),"conflicts":sum(r["conflict"] for r in rows),
            "approximate_accepted":sum(r["accepted_approximate"] is True for r in rows),
            "raw_by_method":{k:counts(v) for k,v in sorted(raw.items())}}
