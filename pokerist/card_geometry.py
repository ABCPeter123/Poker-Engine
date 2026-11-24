"""Corner geometry for saved-card review and permitted practice.

Keep the card-presence check separate from character classification.
The body region is a search window, not a whole-card template.
"""
import numpy as np

def gold_mask(a):
    a=np.asarray(a,dtype=np.int16)
    r,g,b=np.moveaxis(a,-1,0)
    return (r>140)&(g>95)&(b<120)&(r-g>-10)&(r-g<130)

def face_bounds(image,box):
    a=np.asarray(image.crop(box).convert("RGB"),dtype=np.int16)
    neutral=(a.min(2)>170)&(np.ptp(a,axis=2)<45)&~gold_mask(a)
    h,w=neutral.shape
    if h<20 or w<8:
        return None
    rows=np.flatnonzero(neutral.mean(1)>=.15)
    cols=np.flatnonzero(neutral.mean(0)>=.18)
    if len(rows)<max(18,.48*h) or len(cols)<max(7,.24*w):
        return None
    if neutral.mean()<.18:
        return None
    x0,x1=int(cols[0]),int(cols[-1])+1
    y0,y1=int(rows[0]),int(rows[-1])+1
    if x1-x0<7 or y1-y0<20:
        return None
    return box[0]+x0,box[1]+y0,box[0]+x1,box[1]+y1

def corner_regions(image,spec):
    rank,suit,body=spec
    # A narrow overlapping hole-card body cannot establish the full card
    # width. Translate its existing corner windows from the visible face
    # anchor instead of treating the exposed strip as a complete card.
    x0,y0,x1,y1=body
    search=(max(0,x0-4),max(0,y0-6),min(image.width,x1+4),min(image.height,y1+6))
    bounds=face_bounds(image,search)
    if bounds is None:
        return []
    fx,fy,_,_=bounds
    dx=max(-6,min(8,fx-x0))
    dy=max(-6,min(10,fy-y0))
    def shift(box,x,y):
        return (box[0]+x,box[1]+y,box[2]+x,box[3]+y)
    options=[(rank,suit),(shift(rank,dx,dy),shift(suit,dx,dy))]
    if x1-x0>=60:
        # Board cards have an upright, full face. The corner occupies
        # a small strip, independent of the highlighted outer frame.
        options.append(((fx+4,fy+2,fx+29,fy+38),(fx+3,fy+40,fx+29,fy+65)))
    else:
        # A slightly shifted overlapping card often loses its suit at the
        # right edge. Keep rank and suit crops independent.
        options.append((shift(rank,dx,dy),shift(suit,dx-2,dy+3)))
    return list(dict.fromkeys(options))
