"""Benchmark the offline recognition pipeline with controlled synthetic changes.

Not a Pokerist screenshot corpus, not a capture benchmark, and not evidence
that live observations are accurate or that 60 FPS is guaranteed.
"""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import time

os.environ.setdefault("OMP_THREAD_LIMIT","1")
from PIL import Image,ImageDraw,ImageFont
from adaptive_labels import RegionOCRCache
from native_ocr import backend_name
from ocr_runtime import resolve_tesseract
from review import WIDTH,HEIGHT,NUMBERS,normalize,review_image
from table_observation import REGIONS,SEAT_ORDER

def synthetic_frame(index,change_every=12):
    image=Image.new("RGB",(WIDTH,HEIGHT),(32,72,86))
    draw=ImageDraw.Draw(image)
    font=ImageFont.load_default(size=18)
    epoch=index//change_every
    expected={}
    for pos,(key,box) in enumerate(NUMBERS.items()):
        value=str(10000+pos*1000+(epoch%100)*13)
        expected[key]=int(value)
        draw.text((box[0]+25,box[1]+3),value,font=font,fill=(250,250,250))
    for pos,seat in enumerate(SEAT_ORDER):
        box=REGIONS[seat]["bet"]
        value=100+pos*20+epoch%100
        expected["bet:"+seat]=value
        draw.text((box[0]+35,box[1]+3),str(value),font=font,fill=(250,250,250))
    # Every frame contains changing pixels away from calibrated text boxes.
    draw.rectangle((40,40,80,65),fill=(index%256,50,100))
    return image,expected

def measure(exe,frames=180,change_every=12):
    cache=RegionOCRCache()
    previous=None
    times=[]
    errors=0
    field_count=0
    correct=0
    stages={}
    per_field={}
    backend=backend_name(exe)
    start=time.perf_counter()
    for i in range(frames):
        image,expected=synthetic_frame(i,change_every)
        t=time.perf_counter()
        image=normalize(image)
        result=review_image(image,exe,previous,"synthetic offline",ocr_cache=cache)
        times.append((time.perf_counter()-t)*1000)
        previous=image
        errors+=bool(result.get("number_ocr_error") or result["table_observation"].get("ocr_warning") or result["seat_evidence"].get("ocr_warning"))
        for key,value in expected.items():
            candidate=(result["table_observation"]["seats"][key.split(":",1)[1]].get("bet") if key.startswith("bet:") else result["number_candidates"][key].get("candidate"))
            field_count+=1
            passed=bool(candidate and candidate.get("value")==value and not candidate.get("approximate"))
            correct+=passed
            entry=per_field.setdefault(key,{"correct":0,"incorrect":0,"unknown":0})
            entry["correct" if passed else "incorrect" if candidate is not None else "unknown"]+=1
        for key,value in result["timings_ms"].items():
            stages.setdefault(key,[]).append(value)
    wall=time.perf_counter()-start
    return {
        "frames":frames,"change_every_frames":change_every,"ocr_backend":backend_name(exe),
        "initial_ocr_backend":backend,
        "exact_raw_cache_hits":cache.raw_hits,"ocr_cache_hits":cache.hits,"ocr_cache_misses":cache.misses,
        "recognition_plus_normalization_fps":frames*1000/sum(times),
        "wall_fps_including_synthetic_generation":frames/wall,
        "median_frame_ms":statistics.median(times),
        "p95_frame_ms":sorted(times)[math.ceil(.95*frames)-1],
        "max_frame_ms":max(times),"frames_over_16_67_ms":sum(x>1000/60 for x in times),
        "ocr_error_frames":errors,"synthetic_number_fields":field_count,
        "synthetic_number_fields_correct":correct,"synthetic_fields_by_name":per_field,
        "median_stage_ms":{k:statistics.median(v) for k,v in stages.items()},
        "real_frame_accuracy_verified":False,"live_throughput_verified":False
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames",type=int,default=180)
    parser.add_argument("--change-every",type=int,default=12)
    parser.add_argument("--output",type=Path,default=Path("synthetic-throughput.json"))
    args=parser.parse_args()
    if args.frames<2 or args.change_every<1:parser.error("Invalid frame or change count")
    exe,error=resolve_tesseract()
    if not exe:parser.error(error)
    result=measure(exe,args.frames,args.change_every)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(result,indent=2,allow_nan=False))

if __name__=="__main__":
    main()
