"""Remove receiver window chrome and letterboxing without stretching content."""
import numpy as np

TARGET = 1536 / 709
TOLERANCE = .06


def aligned(w, h):
    return w > 0 and h > 0 and abs(w / h - TARGET) <= TOLERANCE


def game_bounds(image):
    a = np.asarray(image.convert('RGB'), dtype=np.int16)
    h, w = a.shape[:2]
    if min(h, w) < 100:
        raise ValueError('Frame too small for review.')
    # Strip only near-black, nearly uniform outer padding. Keep dark game content.
    dark = a.max(axis=2) <= 16
    rows = dark.mean(axis=1) >= .985
    cols = dark.mean(axis=0) >= .985
    def limits(mask):
        good = np.flatnonzero(~mask)
        return (int(good[0]), int(good[-1]) + 1) if good.size else (0, 0)
    y0, y1 = limits(rows)
    x0, x1 = limits(cols)
    if x1-x0 < 100 or y1-y0 < 100:
        raise ValueError('No visible video content in frame.')
    # A light Windows title bar is neutral and bright across most of the width.
    # Require a sustained band followed by non-neutral content, and geometry
    # consistent with the calibrated layout after cropping.
    sub = a[y0:y1, x0:x1]
    hh, ww = sub.shape[:2]
    middle = sub[:, int(ww*.08):int(ww*.92)]
    light = ((middle.min(axis=2) >= 165) & (np.ptp(middle, axis=2) <= 32)).mean(axis=1) >= .80
    header = 0
    for start in range(min(4, hh)):
        if not light[start]:
            continue
        end = start
        while end < min(hh, int(hh*.15)) and light[end]:
            end += 1
        if end-start >= max(5, int(hh*.012)) and end+3 <= hh and not light[end:end+3].any() and aligned(ww, hh-end):
            header = end
            break
    y0 += header
    if not aligned(x1-x0, y1-y0):
        raise ValueError(f'Unsupported frame geometry: {w}x{h}, visible {x1-x0}x{y1-y0}. Share the landscape receiver window without extra panels or use a saved cropped image.')
    return (x0, y0, x1, y1)
