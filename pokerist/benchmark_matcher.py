"""Offline matcher equivalence and microbenchmark on real glyph templates."""
import argparse
import json
import statistics
import time
import numpy as np
from review import decode, match, RANKS, SUITS

def match(m, templates, threshold=.18):
    if m is None:
        return None, None
    grouped={}
    for key,value in templates.items():
        label=key.split("_")[0]
        distance=float(np.mean(m!=decode(value)))
        grouped[label]=min(grouped.get(label,1.0),distance)
    scores=sorted((distance,label) for label,distance in grouped.items())
    distance, label=scores[0]
    margin=scores[1][0]-distance if len(scores)>1 else 1.0
    return (label if distance<=threshold and margin>=.025 else None), round(distance,3)


reference_match=match
# Keep the reference independent from the production implementation.
from review import match as optimized_match

def samples():
    rng=np.random.default_rng(20261124)
    for templates,threshold in ((RANKS,.18),(SUITS,.25),
          ({k:v for k,v in SUITS.items() if k[0] in "dh"},.25),
          ({k:v for k,v in SUITS.items() if k[0] in "cs"},.25)):
        for value in templates.values():
            mask=decode(value)
            yield mask,templates,threshold
            for flips in (1,4,12,24,40):
                perturbed=mask.copy().reshape(-1)
                perturbed[rng.choice(192,flips,replace=False)]^=True
                yield perturbed.reshape(16,12),templates,threshold
        for _ in range(20):
            yield rng.random((16,12))<.5,templates,threshold

def measure(fn,queries,repeats):
    times=[]
    for _ in range(repeats):
        started=time.perf_counter()
        for mask,templates,threshold in queries:
            fn(mask,templates,threshold)
        times.append(1000*(time.perf_counter()-started))
    return statistics.median(times)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats",type=int,default=5)
    args=parser.parse_args()
    if not 1<=args.repeats<=50:
        parser.error("repeats must be 1 to 50")
    queries=list(samples())
    for query in queries:
        if reference_match(*query)!=optimized_match(*query):
            raise SystemExit("Matcher mismatch")
    a=measure(reference_match,queries,args.repeats)
    b=measure(optimized_match,queries,args.repeats)
    print(json.dumps({"queries":len(queries),"identical_results":len(queries),
        "reference_median_ms":round(a,3),"optimized_median_ms":round(b,3),
        "speedup":round(a/max(b,1e-9),2),
        "scope":"glyph matching only; excludes capture, image crops, OCR and rendering"},indent=2))
if __name__=="__main__":
    main()
