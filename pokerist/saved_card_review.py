"""Optional multi-view enhancement for offline saved-image review only."""
from collections import Counter
from copy import deepcopy
from PIL import ImageEnhance, ImageFilter, ImageChops

GROUPS = ("hole_slots", "board_slots")
MIN_AGREEMENT = 3
ALIGNMENT_OFFSETS = ((-3,0),(3,0),(0,-3),(0,3),(-3,-3),(3,3),(-3,3),(3,-3))


def views(image):
    yield image.filter(ImageFilter.UnsharpMask(radius=1.5,percent=150,threshold=2))
    yield image.filter(ImageFilter.UnsharpMask(radius=2.0,percent=220,threshold=3))
    yield ImageEnhance.Contrast(image).enhance(1.25)
    yield ImageEnhance.Contrast(image).enhance(1.20).filter(ImageFilter.UnsharpMask(radius=1.5,percent=120,threshold=2))


def identity(slot):
    label = slot.get("candidate") if isinstance(slot,dict) else None
    return label if isinstance(label,str) and len(label)==2 and label[0] in "23456789TJQKA" and label[1] in "cdhs" else None


def reconcile(primary, alternatives, *, source="saved-image enhancement", count_key="enhanced_card_candidates"):
    """Only recover a visible unknown slot; never overwrite a raw identity or empty slot."""
    result=deepcopy(primary)
    known=[identity(slot) for group in GROUPS for slot in primary[group] if identity(slot)]
    if len(set(known))!=len(known):
        return result
    proposals=[]
    for group in GROUPS:
        for index,slot in enumerate(primary[group]):
            if not isinstance(slot,dict) or identity(slot) is not None:
                continue
            votes=[]
            for reading in alternatives:
                if group in reading and index<len(reading[group]):
                    label=identity(reading[group][index])
                    if label:
                        votes.append(label)
            if len(votes)>=MIN_AGREEMENT and len(set(votes))==1 and votes[0] not in known:
                proposals.append((group,index,votes[0],len(votes)))
    counts=Counter(p[2] for p in proposals)
    # Conflicting recovery proposals invalidate the entire recovery pass.
    if not proposals or any(n>1 for n in counts.values()):
        return result
    for group,index,label,votes in proposals:
        result[group][index].update(candidate=label,rank_candidate=label[0],suit_candidate=label[1],
            rank_distance=None,suit_distance=None,verified=False,source=source,enhancement_votes=votes)
    result.setdefault("quality",{})["unrecognized_visible_cards"]=sum(
        slot is not None and identity(slot) is None for group in GROUPS for slot in result[group])
    result["quality"][count_key]=len(proposals)
    return result


def read_enhanced(image, reader):
    primary=reader(image)
    if not any(isinstance(slot,dict) and identity(slot) is None for group in GROUPS for slot in primary[group]):
        return primary
    return reconcile(primary,[reader(view) for view in views(image)])


def has_unreadable(reading):
    return any(isinstance(slot,dict) and identity(slot) is None
               for group in GROUPS for slot in reading[group])

def read_deep(image, reader):
    """Additional offline alignment study, after the standard enhancement."""
    primary=read_enhanced(image,reader)
    if not has_unreadable(primary):
        return primary
    # Offsets are in normalized-image pixels. Only central card regions
    # are read; wrapped edge pixels are outside those regions.
    alternatives=[reader(ImageChops.offset(image,dx,dy)) for dx,dy in ALIGNMENT_OFFSETS]
    return reconcile(primary,alternatives,source="saved-image alignment",
                     count_key="alignment_card_candidates")
