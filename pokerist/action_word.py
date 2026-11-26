"""Fixed-font observation fallback calibrated on saved right-seat crops.

Not a general OCR system. Other seat geometries have not been validated.
"""
import numpy as np
from PIL import Image
DATA="""Call 2.000000 60c000000000,f0e00000ff80,f0e00001fff0,f0e00001fff8,f0f80000007e,f0e01fc0003e,f0e07fe0001e,f0f0f1c0000f,f0f1f000000f,f070ffc0001f,f1f8fff0003e,f1f8f070007e,f1f8f87c00fe,f1f8fffdfff8,f0e0fff1fff0,000041e0ff80
Call 2.000000 600000000000,f0e000003f80,f1f80001fff0,f1f80001fff8,f1f8000000fe,f1f81fc0007e,f1f87fe0003f,f1f9ffc0003f,f1f8ff00003f,f1f8ffc0003f,f1f8fff0003f,f1f8fff800fe,f1f8fefffffe,f1f8fffffff8,f1f8fff1fff0,00007fe1ffc0
Fold 2.294118 600000000000,7000f00003fe,f000f00007ff,f000f00003ff,f000f000000f,f7c0f01e000f,fff0f0ffc00f,fff8f1ffe00f,f07cf3c0f3ff,f03cf3c0f00f,f03cf3c0f00f,f03cf3c0f00f,f87cf3e1f00f,fff0f1ffe00f,fff0f07f800f,37c0001f0000
Fold 2.500000 7000e00003f0,f000e00007fe,f800e00007ff,f800e000001f,ffc0e03c001f,fff0e0ff001f,fff3e1ffc03f,f8fbe3f3e3ff,f83ff381e7ff,f83ff381f0ff,f83ff381f01f,f8fff3c3e01f,fffff3f7e01f,fff3e1ffe01f,7ff0e0ff001f,3fe0007f0000
Raise 3.062500 00000300003e,0000030001fe,0000030003fe,000000000386,0e010007c786,3f8fe31fc786,7f8ff31fc38e,f3c0f33c03fe,f1c1f33e01fe,ffc7e33fc0ff,ffcfc33fe0ef,01cf033871ef,03ce033c73cf,3f8ff33ff38f,3f0ff33fe78e,1e03c003c306
Raise 3.062500 00000000003c,0000030001fe,0000030003ff,0000000003cf,0e030007878f,3f07e31f878f,7f87f71fc78f,ffc3f73f03ff,ffe1f73f01ff,ffe7e73fe1ff,ffefc73fe1ff,7fff873ff1ff,07ff07bef3cf,1fcfc73ff7cf,3f87e73fe78f,1e07e01fc306
Check 3.411765 020000000000,0600000031e0,0600000033fc,0600000033fc,06000000301e,06180e03b00e,e63e1f87f006,773f3fcff007,7f03b9cc7007,3f037fdc3006,1f03bfdc3006,3f0381cc700e,770781dc701c,e73f1fde33fc,e73f3f9c33f8,001c0e0c01e0
Check 3.625000 0600000031e0,0700000033fc,0700000071fc,07000000701c,071c0603f00e,673f1f8ff00e,773f3fcff007,7f07ffce7007,3f03fbde7007,3f03ffdc7007,3f03ffde700f,7f079fde701e,7f0f83de717e,e71f0fde73fc,e73f1f9c33fc,401e1f0c03f0"""
BANK=tuple((label,float(aspect),int(mask.replace(",",""),16)) for label,aspect,mask in (line.split() for line in DATA.splitlines()))

def action_feature(image,box):
    a=np.asarray(image.crop(box).convert("RGB"),dtype=np.int16)
    r,g,b=np.moveaxis(a,-1,0)
    mask=(r>100)&(g>65)&(b<np.minimum(r,g)-18)&(r>=g)
    y,x=np.where(mask)
    if len(x)<30:return None
    m=mask[y.min():y.max()+1,x.min():x.max()+1]
    h,w=m.shape
    if h<8 or w<12:return None
    q=np.asarray(Image.fromarray(np.uint8(m*255)).resize((48,16)))>=128
    packed=0
    for row in q:packed=(packed<<48)|sum(int(v)<<i for i,v in enumerate(row))
    return packed,w/h

def match_action(feature):
    if feature is None:return None
    p,aspect=feature
    scores={}
    for label,a,m in BANK:
        d=(p^m).bit_count()/768+.1*abs(aspect-a)
        scores[label]=min(scores.get(label,1),d)
    ranked=sorted((d,label) for label,d in scores.items())
    d,label=ranked[0]
    if d>.24 or ranked[1][0]-d<.08:return None
    return {"candidate":label,"distance":round(d,4),"source":"saved right-seat word template"}

def right_action(image,box):
    return match_action(action_feature(image,box))
