"""Fixed upright board-corner audit for normalized 1536x709 saved images."""
from functools import lru_cache
import numpy as np
from PIL import Image

RANK_DATA="""2 .4242 3f87fee0ee06e06f047003803c01e007007801c00effffff
2 .4062 3fc7fff0ff07f07f037807803c01e007003801e00f7effff
2 .4062 1fc3fef0ee06e00f007803801c01e007003c01c01e1ff3ff
2 .4375 1f87fe70ee06e06e047007803c01c00f007803c01e3fefff
3 .4242 3fc79ee0ee06e00f007803f0780e00e00e07e07e077fe3fc
3 .4412 0f83fe7ff78f7067807e07f07e0fc0f80f02f87f8f7ff3fe
3 .3871 1fc406c02c02c00c007807c0f80e00c00c00c02e03ffe7fe
3 .3939 1fc78f7077037007007803f07c0f00e00e00f03f077cf1fc
4 .4375 1c01f03f03f83b839c38c38e3873877c7ffffff380380380
4 .4667 1c01e01e01e01801081081001001003017ff7fc300100100
4 .4516 1c01e01f01f01f01c81cc18c1841843877ff7fe7c0180180
4 .4848 1e03f03f03f83fc3fc7fc39c39e3df7fffffffc3c0380180
5 .4545 7fc3fe00e00e00e1fe7fe70e70070070070270770f3fe1f8
5 .4375 3fc1fc01c00c01c1fc7fcf9ce00e00e00e00e00e077fe3fc
5 .4545 3fc03c00c00e00e1fe7fe70e700e0060060070770f3fe0f8
5 .4545 7fe7fe00e00e00e1fe7fe70e606e00e0060670770f3fe1fc
6 .4545 1fc3fe70e00600600e3fe78f607e06e06e07e0770e7fe1f8
6 .4062 1fc7fe40f0070070077fffffe07e07e07e07e07e07ffe7fe
6 .4242 1fc3ff7070070070073ff78f707607e07e077077877ff1fc
6 .3939 3fc7fff070070070077fff9ff07e07e07e07e07f0ffff3fc
7 .4062 fffffff007003801801c00e0060060070070030030038038
7 .3667 ffff00800000100100180180000010030078078078078038
7 .4375 ffffffe007003801c01c01c00e00f00f00f00f8078078078
7 .4194 ffcffc7803801801801800c0060060060030030030030030
8 .3939 3f870ee07e07e07e0779e7fefdee07e07e07e07f077de1f8
8 .3871 0fe603603c03e03e037ff7ff7ffe03e03e03e03e037ff7ff
8 .3871 7f8c06c07c03c03c02ffeffeffee07c03c03c03c07ffe7fe
8 .4545 3f870e70e60660670679e3fc7de706e07e07e0770f7fe1f8
9 .3939 3fcf9ee07e07e07e07e07e0fffeffce00e00e07e0f7fe3fc
9 .3871 1fe006c03c03c03c03c03e07ffff00e00c00c00e027fe3fe
9 .4062 1fe7ff707607607e07e07f07fffffef00e00e007037ff3fe
9 .4242 3fc7df707607607e07e07f07ffff7ce006006077077ff1fc
A .5312 0600f00f00f01f819819839c38c30e70e7fe7fe70ee07c03
A .5 0600f00f01f81f81fc39c39c30c30c70e7feffff0fe07c03
A .5312 0600f00f00f81f819819839c38c30e70e7fe7fe707e07e07
A .5312 0600f00f00f00f81f819839c38c30e70e7fe7fe70ee07c03
J .4545 e00e00e00e00e00e00e00e00e00e00e00e02e0770f7de1fc
J .4839 400c00c00c00c00c00c00c00c00c00c00e00e01f077fe3fc
J .4688 e00e00e00e00e00e00e00e00e00e00e00e03e0770f7fe1f8
J .4545 e00e00e00e00e00e00e00e00e00e00e00e07e0770f7df1fc
K .5 6067073873871c70ff07f0ff1ff1cf387387707707e07e07
K .5312 e077073871c70e706707f07f0ff1cf1c7387387707707f07
K .4667 4066067071871cf1ff0ff0ff1ff1ef38f387707e07e07e07
K .5152 e077073871c70e707707f0ff0ef1c71c7387387707707e03
Q .4571 3f871ee0ee07e07e07e07e07e07e07e07e07e0f79e3fc700
Q .4839 600400401403c03c03c03c03c0340340340340379e3c0380
Q .4545 70ce06c03c03c03c03c03c03c03e03e03e03e0778e3fc700
Q .4706 1f879c60ec06c07c07c03c07c07c03c03c07e0679e7f87c0
T .7879 3847c6c67c66c66c66c66c66c66c66c66c66c66c667c6380
T .7419 7e0c70c33c33c33c33c33c33c33c33c33c33c33e737e33c3
T .8125 780fc6cc7846846844844844844844844844844c44fc4780
T .7353 3807e2663c63c63c63c63c63c63c63c63c63c63e637e3380
6 .4667 79ce064070070073fff9ff07e07e07e07e07e07f0e7fe3f8
7 .3226 f80f807803c00e00e007007803c03c01e01e01f01f01f00f"""
SUIT_DATA="""c 1.0 0700f01f81f81f81f81f87feffffffffffff7ff3ee060060
c 1.05 0e00f00f01f81f81f81f83fc7feffefffffffff7fe3f8020
c 1.0455 0e01f01f81f81f81f01f87feffefffffffffffe7dc060060
c 1.087 0600f01f81f81f81f83fc7fe7fefffffffff7fe7fe3f8060
d .9 0600f00f01f83fc7fe7feffffff7ff7fe3fc1f80f00f0060
d .8636 0600600f01f01f87fc7feffffffffe7fc3f81f00f0060060
d .8947 0601f01f83fc7fc7feffeffffff7fe7fe3fc3f81f00e0000
d .9474 0600f00f81fc3fe7feffffff7ff7ff3fe1fc1f80f0070000
h 1.1053 1883fc7fe7fffffffffff7ff7fe7fe3fc1f80f00f0060060
h 1.2353 3fc7fe7feffeffffffffeffe7fe7fe3fc3f81f81f00e0060
h 1.1176 3fe7fefffffffffffffffffffff7fe3fc3fc1f80f00f0060
h 1.1053 1007fc7feffeffefffffeffe7fe7fc3fc3f81f00f00e0040
s .913 0600700f81f83fc7feffffffffffff7ff7fe1ec060060060
s 1.0 0700f81fc1fe3ff7ffffffffffffffffffff7ff3fe1f8030
s .8636 0300780f80fc1fe3ff7ff7ffffffff7ff7ff1a6030030070
s 1.1176 0f00f01f83fc3fc7feffefffffffffffffffffe3fc1f0020
c .8636 0780fc0fc0fe0fc0fc1fe7fffffffffffffffff332030030
c .9091 0780fc0fc0fc0fc0fc1fe7ff7ffffffff7ff7fe312030030"""
BOARD_X=(547,637,726,815,905)

@lru_cache(maxsize=2)
def compiled(data):
    return tuple((label,float(aspect),int(mask,16)) for label,aspect,mask in (line.split() for line in data.splitlines()))

def feature(mask,gap):
    cols=np.flatnonzero(mask.any(0))
    if not len(cols):return None
    end=cols[0]
    for col in cols[1:]:
        if col-end>gap:break
        end=col
    y,x=np.where(mask[:,:end+1])
    if len(y)<15:return None
    m=mask[y.min():y.max()+1,x.min():x.max()+1]
    h,w=m.shape
    q=np.asarray(Image.fromarray(np.uint8(m*255)).resize((12,16)))>=128
    packed=0
    for row in q:
        packed=(packed<<12)|sum(int(v)<<j for j,v in enumerate(row))
    return packed,w/h

def nearest(q,data,allowed=None):
    if q is None:return None,None
    mask,aspect=q;distances={}
    for label,a,p in compiled(data):
        if allowed is not None and label not in allowed:continue
        d=(mask^p).bit_count()/192+.15*abs(aspect-a)
        distances[label]=min(d,distances.get(label,1.0))
    scores=sorted((d,label) for label,d in distances.items())
    if not scores:return None,None
    d,label=scores[0]
    if d>.18 or len(scores)>1 and scores[1][0]-d<.025:return None,round(d,3)
    return label,round(d,3)

def upright_board_card(image,index):
    if image.size!=(1536,709):return None
    x=BOARD_X[index]
    a=np.asarray(image.crop((x,240,x+84,354)),dtype=np.int16)
    lo=a.min(2);hi=a.max(2)
    face=(lo>132)&(hi-lo<40)
    if face.mean()<.30 or (face.mean(0)>.25).sum()<50:return None
    r,g,b=np.moveaxis(a,-1,0)
    red=(r>95)&(r-g>45)&(r-b>35)&(g<r*.63)
    black=(hi<115)&(hi-lo<45)
    is_red=red[3:41,4:29].sum()>black[3:41,4:29].sum()
    mask=red if is_red else black
    rank,rd=nearest(feature(mask[3:41,4:33],7),RANK_DATA)
    suit,sd=nearest(feature(mask[42:69,3:30],2),SUIT_DATA,"dh" if is_red else "cs")
    return {"candidate":rank+suit if rank and suit else None,"rank_candidate":rank,"suit_candidate":suit,
            "rank_distance":rd,"suit_distance":sd,"verified":False,"source":"upright board corner"}

