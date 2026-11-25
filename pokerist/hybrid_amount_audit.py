"""Compare independent numeric readers on completed, manually labelled crops.

No live capture, decision engine integration, model downloads or external API.
An optional local vision server is queried only for this offline evaluation.
"""
import argparse
import base64
from collections import Counter
import http.client
import io
import json
import math
from pathlib import Path
import statistics
import time
from urllib.parse import urlsplit

import numpy as np
from PIL import Image, ImageOps
from amount_text import number_text
from automatic_glyph_audit import fit_amount, predict_amount, GlyphBank
from glyph_audit import read_samples
from native_ocr import recognize_tsv
from ocr_runtime import resolve_tesseract

def identity(text):
    parsed=number_text(text)
    return None if parsed is None else (parsed["value"],parsed["approximate"],parsed.get("display_step"))

def consensus(readings):
    """Require at least two readers agreeing, without a contradictory reading."""
    valid={name:identity(text) for name,text in readings.items() if identity(text) is not None}
    choices=set(valid.values())
    if len(choices)>1:
        return {"status":"conflict","candidate":None,"support":sorted(valid)}
    if len(valid)<2:
        return {"status":"insufficient independent readings","candidate":None,"support":sorted(valid)}
    return {"status":"agreement candidate","candidate":next(iter(valid.values())),"support":sorted(valid)}

def crop_image(patch):
    a=np.asarray(patch,dtype=float)
    if a.ndim!=2 or not a.size or not np.isfinite(a).all() or max(a.shape)>4096:
        raise ValueError("Invalid crop")
    im=Image.fromarray(np.uint8(np.clip(a,0,255)))
    im=ImageOps.autocontrast(im)
    return ImageOps.expand(im.resize((im.width*3,im.height*3),Image.Resampling.LANCZOS),border=12,fill=0)

def ocr_reader(patch,exe):
    # Text is light on a dark background; use dark ink for Tesseract.
    im=ImageOps.invert(crop_image(patch))
    tsv=recognize_tsv(im,exe,7,"0123456789.KkMm,",persistent=True)
    words=[]
    for line in tsv.splitlines()[1:]:
        cols=line.split("\t",11)
        if len(cols)==12 and cols[0]=="5" and cols[11].strip():
            confidence=float(cols[10])
            if not math.isfinite(confidence) or confidence<75:return None
            words.append((int(cols[6]),cols[11].strip()))
    raw=" ".join(v for _,v in sorted(words))
    return raw if identity(raw) is not None else None

def endpoint_parts(endpoint):
    u=urlsplit(endpoint)
    if (u.scheme!="http" or u.hostname not in ("127.0.0.1","localhost","::1")
        or u.username is not None or u.password is not None or u.query or u.fragment
        or u.path!="/v1/chat/completions" or u.port is None):
        raise ValueError("Use an explicit loopback HTTP /v1/chat/completions endpoint")
    return u

def parse_vision_response(content):
    try:
        obj=json.loads(content)
        if not isinstance(obj,dict) or set(obj)!={"text"}:return None
        text=obj["text"]
        return text if isinstance(text,str) and identity(text) is not None else None
    except (ValueError,TypeError):
        return None

def vision_reader(patch,endpoint,model,timeout=10):
    u=endpoint_parts(endpoint)
    im=crop_image(patch)
    b=io.BytesIO();im.save(b,format="PNG")
    uri="data:image/png;base64,"+base64.b64encode(b.getvalue()).decode("ascii")
    body=json.dumps({"model":model,"temperature":0,"max_tokens":64,"stream":False,
        "messages":[{"role":"user","content":[
            {"type":"text","text":"Transcribe the single visible numeric label exactly, including any decimal or K/M suffix. Do not infer missing characters. Return only JSON with one key text, containing a string, or null if unreadable."},
            {"type":"image_url","image_url":{"url":uri}}]}]})
    # Direct connection to numeric loopback, no proxy, DNS or redirects.
    host="::1" if u.hostname=="::1" else "127.0.0.1"
    conn=http.client.HTTPConnection(host,u.port,timeout=timeout)
    try:
        conn.request("POST",u.path,body=body,headers={"Content-Type":"application/json"})
        res=conn.getresponse()
        if res.status!=200:raise RuntimeError("Local vision HTTP "+str(res.status))
        raw=res.read(1024*1024+1)
        if len(raw)>1024*1024:raise ValueError("Oversized response")
        obj=json.loads(raw)
        return parse_vision_response(obj["choices"][0]["message"]["content"])
    finally:conn.close()

def measure(samples,exe,vision=None):
    groups={s[0] for s in samples}
    if len(groups)<2:raise ValueError("At least two separate source groups required")
    libraries={g:GlyphBank(fit_amount([s for s in samples if s[0]!=g])) for g in groups}
    rows=[]
    for group,label,patch,name in samples:
        readers={};timings={};errors={}
        def run(key,fn):
            t=time.perf_counter()
            try:readers[key]=fn()
            except (OSError,ValueError,RuntimeError,KeyError,TypeError,IndexError,http.client.HTTPException) as e:
                readers[key]=None;errors[key]=str(e)[:200]
            timings[key]=round((time.perf_counter()-t)*1000,3)
        run("glyph",lambda:predict_amount(patch,libraries[group])["candidate"])
        run("ocr",lambda:ocr_reader(patch,exe))
        initial=consensus(readers)
        if vision is not None:run("vision",lambda:vision(patch))
        final=consensus(readers)
        # Counterfactual selective fallback: skip vision on existing agreement.
        selective=initial if initial["candidate"] is not None else final
        rows.append({"group":group,"name":name,"expected":label,"readers":readers,
            "timings_ms":timings,"errors":errors,"two_reader":initial,"ensemble":final,"selective":selective})
    def score(get):
        counts=Counter()
        for row in rows:
            predicted=get(row)
            counts["unknown" if predicted is None else "correct" if predicted==identity(row["expected"]) else "incorrect"]+=1
        return {k:counts[k] for k in ("correct","incorrect","unknown")}
    names=["glyph","ocr"]+(["vision"] if vision is not None else [])
    scores={name:score(lambda row,n=name:identity(row["readers"].get(n))) for name in names}
    scores["two_reader"]=score(lambda row:row["two_reader"]["candidate"])
    scores["ensemble"]=score(lambda row:row["ensemble"]["candidate"])
    scores["selective"]=score(lambda row:row["selective"]["candidate"])
    return {"scope":"Completed-image manually localized crops; group-held-out glyph training; no live performance claim",
        "samples":len(rows),"groups":len(groups),"scores":scores,
        "median_reader_ms":{n:statistics.median(row["timings_ms"][n] for row in rows) for n in names},
        "vision_calls":len(rows) if vision is not None else 0,
        "selective_vision_calls":sum(row["two_reader"]["candidate"] is None for row in rows) if vision is not None else 0,
        "selective_vision_note":"Counterfactual from the same offline predictions; skips vision when two readers already agree.",
        "automatic_accuracy_verified":False,"details":rows}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("images",type=Path)
    p.add_argument("--manifest",type=Path,default=Path(__file__).parent/"fixtures"/"glyph_amount_crops.json")
    p.add_argument("--vision-endpoint")
    p.add_argument("--vision-model")
    p.add_argument("--output",type=Path,default=Path("hybrid-amount-validation.json"))
    a=p.parse_args()
    if bool(a.vision_endpoint)!=bool(a.vision_model):p.error("Specify both vision endpoint and model")
    if a.vision_endpoint:endpoint_parts(a.vision_endpoint)
    exe,err=resolve_tesseract()
    if not exe:p.error(err)
    samples=read_samples(a.images,json.loads(a.manifest.read_text(encoding="utf-8")))
    vision=(lambda patch:vision_reader(patch,a.vision_endpoint,a.vision_model)) if a.vision_endpoint else None
    report=measure(samples,exe,vision)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="details"},indent=2))

if __name__=="__main__":main()
