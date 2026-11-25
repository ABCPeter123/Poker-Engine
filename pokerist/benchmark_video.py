"""Measure full saved-video decoding and screenshot review throughput.
Only completed local recordings; no screen capture or recommendations.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import time

from audit_recording import audit_frames, probe_recording

def summarize(expected, durations, elapsed, coverage, ocr, errors, target=60):
    n=len(durations)
    fps=n/elapsed if elapsed>0 else 0
    times=sorted(durations)
    p95=times[math.ceil(.95*n)-1] if n else None
    budget=1000/target
    complete=expected>0 and n==expected and not errors
    return {"expected_frames":expected,"processed_frames":n,
            "unprocessed_frames":max(0,expected-n),"elapsed_seconds":elapsed,
            "processing_fps":fps,"target_fps":target,"frame_budget_ms":budget,
            "p50_frame_ms":statistics.median(times) if n else None,"p95_frame_ms":p95,
            "max_frame_ms":max(times) if n else None,
            "frames_over_budget":sum(t>budget for t in times),
            "all_frames_processed":complete,"source_coverage_pass":coverage,
            "ocr_enabled":ocr,"errors":errors,
            "throughput_pass":complete and coverage and fps>=target,
            "strict_frame_budget_pass":complete and coverage and fps>=target and max(times,default=math.inf)<=budget,
            "full_field_accuracy_verified":False}

def read_exact(stream, n):
    data=bytearray()
    while len(data)<n:
        chunk=stream.read(n-len(data))
        if not chunk:
            if data:
                raise EOFError("Truncated decoded frame")
            return None
        data.extend(chunk)
    return bytes(data)

def benchmark(path, *, ffmpeg="ffmpeg", ffprobe="ffprobe", ocr=True, target=60, incremental=False):
    from PIL import Image
    from review import normalize, review_image
    from ocr_runtime import resolve_tesseract
    from adaptive_labels import RegionOCRCache
    from native_ocr import backend_name
    path=Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError("A completed local recording is required")
    # Reject non-video inputs and changing dimensions (rawvideo needs fixed size).
    meta=subprocess.run([ffprobe,"-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height","-of","json",str(path)],
        capture_output=True,text=True,check=True,timeout=60)
    stream=json.loads(meta.stdout)["streams"][0]
    w,h=int(stream["width"]),int(stream["height"])
    if min(w,h)<100 or w*h>12000000:
        raise ValueError("Unsupported video dimensions")
    stamps=probe_recording(path,ffprobe)
    coverage=audit_frames(stamps,1000/target*1.10)
    if not coverage["geometry_consistent"] or any(d!=[w,h] for d in coverage["observed_dimensions"]):
        raise ValueError("Recording geometry changes; fixed-size raw frame decoding would misalign pixels")
    # A gap test alone does not establish source FPS.
    span=(coverage["last_s"]-coverage["first_s"]) if len(stamps)>1 and coverage["first_s"] is not None else 0
    source_fps=(coverage["unique_timestamps"]-1)/span if span>0 else 0
    source_ok=coverage["coverage_pass"] and source_fps>=target-.01
    exe=None
    if ocr:
        exe,error=resolve_tesseract()
        if not exe: raise RuntimeError(error)
    previous=None
    cache=RegionOCRCache() if incremental else None
    durations=[]; errors=[]; stages={}
    previous_digest=None; consecutive_identical=0; sequence=hashlib.sha256()
    overhead={name:[] for name in ("decode_and_hash","normalize","recognition")}
    start=time.perf_counter()
    proc=subprocess.Popen([ffmpeg,"-v","error","-nostdin","-noautorotate","-i",str(path),
        "-map","0:v:0","-an","-sn","-dn","-vsync","0","-pix_fmt","rgb24","-f","rawvideo","pipe:1"],
        stdout=subprocess.PIPE)
    try:
        while True:
            t=time.perf_counter()
            raw=read_exact(proc.stdout,w*h*3)
            if raw is None: break
            digest=hashlib.sha256(raw).digest()
            consecutive_identical+=int(digest==previous_digest)
            previous_digest=digest
            sequence.update(digest)
            decoded=time.perf_counter()
            image=normalize(Image.frombytes("RGB",(w,h),raw))
            normalized=time.perf_counter()
            comparable=previous if previous is not None and previous.info.get("capture_crop")==image.info.get("capture_crop") else None
            if previous is not None and comparable is None and incremental:
                cache=RegionOCRCache()
            result=review_image(image,exe,comparable,"completed video benchmark",ocr_cache=cache)
            if ocr and (result.get("number_ocr_error") or result.get("table_observation",{}).get("ocr_warning") or result.get("seat_evidence",{}).get("ocr_warning")):
                errors.append({"frame":len(durations),"error":"OCR error"})
            for name,ms in result.get("timings_ms",{}).items():
                stages.setdefault(name,[]).append(ms)
            finished=time.perf_counter()
            overhead["decode_and_hash"].append((decoded-t)*1000)
            overhead["normalize"].append((normalized-decoded)*1000)
            overhead["recognition"].append((finished-normalized)*1000)
            durations.append((finished-t)*1000)
            previous=image
        if proc.wait()!=0: errors.append({"error":"FFmpeg decode failed"})
    except Exception as exc:
        errors.append({"frame":len(durations),"error":str(exc)})
    finally:
        proc.stdout.close()
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    report=summarize(len(stamps),durations,time.perf_counter()-start,source_ok,ocr,errors,target)
    report["source_fps"]=source_fps
    report["incremental_exact_region_cache"]=incremental
    report["ocr_backend"]=backend_name(exe) if incremental and exe else "CLI" if exe else "disabled"
    report["median_pipeline_ms"]={name:statistics.median(values) for name,values in overhead.items() if values}
    report["p95_pipeline_ms"]={name:sorted(values)[math.ceil(.95*len(values))-1] for name,values in overhead.items() if values}
    report["decoded_frame_sequence_sha256"]=sequence.hexdigest()
    report["consecutive_identical_pixel_frames"]=consecutive_identical
    report["source_geometry"]=[w,h]
    report["pixel_identity_note"]="Identical frames can be legitimate static content, not proof of a dropped frame."
    report["source_max_gap_ms"]=coverage["max_gap_ms"]
    report["median_stage_ms"]={name:statistics.median(ms) for name,ms in stages.items()}
    report["scope"]="Completed recording only; no live throughput or field accuracy claim"
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("recording",type=Path)
    p.add_argument("--ffmpeg",default="ffmpeg")
    p.add_argument("--ffprobe",default="ffprobe")
    p.add_argument("--target",type=float,default=60)
    p.add_argument("--incremental",action="store_true",help="Use exact-region cache as in the practice worker")
    p.add_argument("--no-ocr",action="store_true",help="Visual-only diagnostic, not full recognition")
    p.add_argument("--output",type=Path,default=Path("video-throughput.json"))
    a=p.parse_args()
    if not math.isfinite(a.target) or a.target<=0: p.error("Target must be positive and finite")
    report=benchmark(a.recording,ffmpeg=a.ffmpeg,ffprobe=a.ffprobe,ocr=not a.no_ocr,target=a.target,incremental=a.incremental)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report["throughput_pass"] and report["ocr_enabled"] else 1

if __name__=="__main__":
    raise SystemExit(main())
