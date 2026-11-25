"""Audit timestamp coverage in a completed, local video recording.

No screen capture, live streams, recognition loop or action recommendations.
A timestamp is evidence of a decoded frame, not proof of a visible action.
"""
import argparse
import bisect
import json
import math
from pathlib import Path
import statistics
import subprocess


def finite_number(value):
    if isinstance(value,bool):
        return None
    try:
        n=float(value)
    except (TypeError,ValueError,OverflowError):
        return None
    return n if math.isfinite(n) else None


def audit_frames(frames, max_gap_ms=100, events=()):
    if finite_number(max_gap_ms) is None or max_gap_ms<=0:
        raise ValueError("max_gap_ms must be positive and finite")
    timestamps=[]
    missing=0
    for frame in frames:
        t=finite_number(frame.get("best_effort_timestamp_time"))
        if t is None:
            missing+=1
        else:
            timestamps.append(t)
    backwards=sum(b<a for a,b in zip(timestamps,timestamps[1:]))
    ordered=sorted(set(timestamps))
    duplicates=len(timestamps)-len(ordered)
    gaps=[round((b-a)*1000,6) for a,b in zip(ordered,ordered[1:])]
    long_gaps=[{"from_s":a,"to_s":b,"gap_ms":g}
               for a,b,g in zip(ordered,ordered[1:],gaps) if g>max_gap_ms]
    windows=[]
    for event in events:
        start=finite_number(event.get("start_s"))
        end=finite_number(event.get("end_s"))
        if start is None or end is None or end<=start:
            raise ValueError("Event windows need finite start_s < end_s")
        # Half-open intervals: adjacent windows cannot share an endpoint.
        lo,hi=bisect.bisect_left(ordered,start),bisect.bisect_left(ordered,end)
        windows.append({"label":str(event.get("label","unlabelled")),
                        "start_s":start,"end_s":end,"frames_in_window":hi-lo,
                        "sample_present":hi>lo,
                        "outside_timestamp_span":not ordered or start<ordered[0] or end>ordered[-1]})
    return {"frames":len(timestamps)+missing,"timestamped_frames":len(timestamps),
            "unique_timestamps":len(ordered),"missing_timestamps":missing,
            "duplicate_timestamps":duplicates,"backwards_timestamps":backwards,
            "first_s":ordered[0] if ordered else None,"last_s":ordered[-1] if ordered else None,
            "median_gap_ms":statistics.median(gaps) if gaps else None,
            "p95_gap_ms":sorted(gaps)[math.ceil(.95*len(gaps))-1] if gaps else None,
            "max_gap_ms":max(gaps) if gaps else None,"gap_limit_ms":max_gap_ms,
            "large_gaps":long_gaps,"labelled_windows":windows,
            "coverage_pass":bool(gaps) and not (missing or duplicates or backwards or long_gaps)
                and all(w["sample_present"] and not w["outside_timestamp_span"] for w in windows),
            "limitations":["Frame timestamps do not prove that an action is visible.",
                           "No inference of individual actions from merged wagers.",
                           "Coverage checks do not guarantee recognition accuracy."]}


def probe_recording(path, ffprobe="ffprobe"):
    path=Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError("Supply a completed local video file.")
    command=[ffprobe,"-v","error","-select_streams","v:0","-show_frames",
             "-show_entries","frame=best_effort_timestamp_time","-of","json",str(path)]
    proc=subprocess.run(command,capture_output=True,text=True,check=True,timeout=300)
    result=json.loads(proc.stdout)
    if not isinstance(result.get("frames"),list):
        raise ValueError("No video frames returned")
    return result["frames"]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("recording",type=Path)
    p.add_argument("--max-gap-ms",type=float,default=100)
    p.add_argument("--events",type=Path,help="Optional JSON array of manually labelled event windows")
    p.add_argument("--ffprobe",default="ffprobe")
    p.add_argument("--output",type=Path,default=Path("recording-coverage.json"))
    args=p.parse_args()
    events=json.loads(args.events.read_text(encoding="utf-8")) if args.events else []
    if not isinstance(events,list) or any(not isinstance(e,dict) for e in events):
        p.error("Event labels must be an array of objects")
    report=audit_frames(probe_recording(args.recording,args.ffprobe),args.max_gap_ms,events)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("large_gaps","labelled_windows")},indent=2))
    print("Report:",args.output)
    return 0 if report["coverage_pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
