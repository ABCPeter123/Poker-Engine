"""Calibrated fixed-font amount candidates; original screenshots are not embedded."""
import base64,zlib
from functools import lru_cache
import numpy as np
from automatic_glyph_audit import GlyphBank
from offline_font_review import read_amount,STACKS,AMOUNTS
from amount_text import number_text

# Two representative templates per class from the initial 184-template
# library: medoid and farthest from medoid, quantized to two bits/pixel.
# Source library sha256: 85b3c63f5fc4aeb000a01ca40b7484cba106b682e8fe951b164cce56b22fd657
LABELS="..00112233445566778899KK"
ASPECTS=[1,1,11/15,3/4,5/14,3/7,2/3,3/5,8/13,9/14,11/14,5/7,9/14,7/13,5/7,9/13,9/14,9/14,9/13,9/14,5/7,2/3,11/14,5/7]
DATA="eNptlTGO4zYUhp8GsQbYabbIurAKH2GvwEmxTRoNMDIQq5gmSGEXvEHGR1BhVynSjAtTwLDOAjGv4CNMQRVWim08wIjAkvkfJe/ObmLggyWR/B/58/Fxpnb5XO1umYXaFapWhdJMu1Gm3arQqhAc8APhFedvLmKADm5XB7cd2BS1V2dmdYjMdVALDWENEcb8D31bO49jMF65noV6zY4WO0q0E2kIVea0nTblSVZpp1cXnRbJx71I9j30iv7bI0Afx/3fr9MuOy5PV95Y1koWO0GTB0qDz8d4L32w8qifdZV1RqTOU7L/HCHT9dx/R/zOfbjvHmM04kjMr8Q8J9DkOPlYu3dzEwrdmxp/DgZtZSiuZRC0DJSAkexJznz9JvCe478oevg9wu2T0KJrOwuhXYLah3ax1a64kQ46LXBsYP/P71+eX6HPfYd2ZqmIFtt58BV0K0zf1qruCpG5EaWOvgVWZA1RaYnkgRJT0dgLKjtIWRqdX50gzKwwTrEVnqH5lkZK5SX0ZQhduavdOE8DNEFiAD97okvEyRBHWnx+QnNFGURlR6l5wGNF0hewWXF6hfqfEJBCquznvy1bc5wUS9drJQM89+yYLOp1YpATJthE1Ue6HbshNqD4X4ixWWyWTrtwhBcPOE/iXVEQ9HPMuwJ2UshuRJnr53r2puySQkMX+mGI8VvNfvlXazT8XFAW1KZ2mH+ng1+DHMs/0AW4BBmYfjqQ1Af6vTwke9BND+nL9HBpp4fsaXqYVtODZDay0a1BpgUP3Fxp7M/08JWsIppUCI1DYCzCW+iDT5ZkbWlfNsn+zkLfpi+ZvTplFvoW2lauMrvPp41Xsj2ntFK8s3eNoOyJejjGIf2oWpwDx4y92mWduMUuvs1OaLW8o3HVIgthnanQjArkHs2/82bwp5i7hap5TY2O++oF8iYM+BIzWEIzsgbNLdXtVqBmresQjvMZ5pjMw3+1sb80C6rQnJNHSK0V9rfY3aIJFWUE3iDXvqRfhSwSdNX185/6j4JzQLfamoes21eoHyLxn4ca0teHC2e4PmzLbuq4BvkqNRBJ9jml+/zHiRdCHnFe1jFcPFHdLbJpB21fSYzRGIsa42J9Y02i+M91Tva15zkbtGN9G68JR4D9CibuUQ0PZ+e8b+JiSHIOrDAHEQ/ppOOUpRGO8g93tl+vfAAVFeBGrt7emFXOQ9garmaMw2UA93nWz73u/aALzXTwLnshem9fhR0I0EKXi6Fr5C/MckexPnMt5ZqK9fH6UfcvOimw3ip9zmxpY+UNgXOoKo9Ly33Yb/bmbxq8ytFrXXZ3Q21OsL80W1OqXTU24QHfO92UrOSH+8MMvrq76Kvme8OW3jR6O+c94N1D/ad7IGHqPfbchM0s6LZ2iNGkqCkj43LoVxnuHdks4/6Z1YXvx/fwM8eVzdxNUWGwji415kS/aBuNH3x8Cw9zeHcDz2KO/I30xP2IK6avn8g/XqOHN8g59yX/2Au+nzZx/d2bEE6Jgva7QXv0bW7zPiTwnn4lehTpy6O4OhmRWSPkQYv7lb7eC/2TJ/2hI/PzicyfljRKkkZJNihRGtK6PMX22A/9H8V9xeONmFotrqCZdo98JkTq+b6FPu7d9zGGuTaVufbCfPhM5g/EgB7K5lf42we0o88effdCPvVjWeOSNVFRkkclaPEvZWSLag=="
@lru_cache(maxsize=1)
def bank():
    packed=np.frombuffer(zlib.decompress(base64.b64decode(DATA)),dtype=np.uint8).reshape(len(LABELS),96)
    pixels=np.stack([(packed>>shift)&3 for shift in (6,4,2,0)],axis=-1).reshape(len(LABELS),24,16)/3
    return GlyphBank([(label,(p,aspect)) for label,p,aspect in zip(LABELS,pixels,ASPECTS)])

BET_KEYS={"hero":"bet_hero","left":"bet_left","upper_left":"bet_ul","upper_right":"bet_ur","right":"bet_right"}

def candidate(image,key,cache=None):
    if image.size!=(1536,709):return None,None
    if key in STACKS:
        x,y=STACKS[key];box=(x-60,y-10,x+65,y+10)
    else:box=AMOUNTS[key]
    signature=image.crop(box).tobytes()
    if cache is not None:
        if not hasattr(cache,"font_amounts"):cache.font_amounts={}
        prev=cache.font_amounts.get(key)
        if prev is not None and prev[0]==signature:return prev[1]
    text,bounds=read_amount(np.asarray(image),key,bank())
    value=number_text(text)
    if value:value={**value,"source":"fixed-font","glyph_candidate":True}
    result=(value,bounds)
    if cache is not None:cache.font_amounts[key]=(signature,result)
    return result

def combine(primary,glyph,bounds):
    """Retain both readers; never hide a genuine conflict."""
    if glyph is None:return primary
    result=dict(primary)
    result["font_candidate"]=glyph
    old=primary.get("candidate")
    if old is not None:
        if (old["value"],old.get("approximate"),old.get("display_step"))!=(glyph["value"],glyph.get("approximate"),glyph.get("display_step")):
            result["reader_conflict"]=True
            result["ocr_candidate"]=old
            result["candidate"]=None
            return result
        result["candidate"]={**old,"source":"OCR + fixed-font"}
    else:
        result["candidate"]=glyph
        result["text_bounds"]=bounds
    return result
