"""Click-to-correct: the researcher fixes the AI draft with clicks, not by redrawing.

- add_at_click: a nodule the AI missed. Take the model's own (lower-confidence) signal around the
  click; if there is none, grow a region from the click on CT density inside the lungs.
- grow / shrink: 'add' clicks pull a missing part into the outline; 'remove' clicks cut a wrong part
  away (e.g. a vessel stuck to the nodule) with a watershed split between the click and the rest.
- replace_slice: the researcher redraws the outline on one slice (polygon).
"""
import numpy as np
from scipy import ndimage as ndi
from skimage.draw import polygon as draw_polygon
from skimage.segmentation import watershed

LOW_PROB = 0.15       # model signal accepted around a user click
GROW_HU = -650        # density threshold for growing from a click (keeps ground-glass in)
BOX_MM = 40           # search box around a click


def _box(shape, c, spacing, mm=BOX_MM):
    r = np.ceil(mm / 2 / np.asarray(spacing)).astype(int)
    c = np.round(c).astype(int)
    return tuple(slice(max(int(ci - ri), 0), min(int(ci + ri + 1), s)) for ci, ri, s in zip(c, r, shape))


def region_at(c, prob, hu, lungs, spacing):
    """3D region at voxel c (z,y,x). Returns a full-size bool mask (empty if nothing there)."""
    sl = _box(hu.shape, c, spacing)
    lc = tuple(int(round(ci)) - s.start for ci, s in zip(c, sl))
    out = np.zeros(hu.shape, bool)
    # 1) the model's own signal, at a lower bar than the automatic pass
    if prob is not None:
        cand = prob[sl].astype(np.float32) > LOW_PROB
        lab, _ = ndi.label(cand, np.ones((3, 3, 3)))
        k = _label_near(lab, lc, spacing)
        if k:
            out[sl] = lab == k
            return out, "model"
    # 2) density growing from the click, inside the lungs (dilated so edge nodules are kept)
    lung = ndi.binary_dilation(lungs[sl] > 0, iterations=3) if lungs is not None else np.ones_like(hu[sl], bool)
    cand = (hu[sl] > GROW_HU) & lung
    cand = ndi.binary_opening(cand, np.ones((1, 3, 3)))  # cut thin vessel bridges in-plane
    lab, _ = ndi.label(cand, np.ones((3, 3, 3)))
    k = _label_near(lab, lc, spacing)
    if k:
        reg = lab == k
        # refuse "regions" that are really the chest wall / a large vessel tree (touch the box edge widely)
        edge = np.zeros_like(reg); edge[[0, -1]] = edge[:, [0, -1]] = edge[:, :, [0, -1]] = True
        if (reg & edge).sum() < 0.05 * reg.sum():
            out[sl] = reg
            return out, "density"
    return out, None


def _label_near(lab, lc, spacing, max_mm=3.0):
    if lab[lc]:
        return lab[lc]
    r = np.ceil(max_mm / np.asarray(spacing)).astype(int)
    sub = tuple(slice(max(c - k, 0), c + k + 1) for c, k in zip(lc, r))
    vals = lab[sub]
    if not vals.any():
        return 0
    return int(np.bincount(vals[vals > 0]).argmax())


def grow(mask, points, prob, hu, lungs, spacing):
    out = mask.copy()
    for p in points:
        reg, _ = region_at(p, prob, hu, lungs, spacing)
        if not reg.any():  # nothing found: add a small sphere (2 mm) so the click is never ignored
            sl = _box(hu.shape, p, spacing, 6)
            zz, yy, xx = np.ogrid[sl]
            d = (((zz - p[0]) * spacing[0]) ** 2 + ((yy - p[1]) * spacing[1]) ** 2 + ((xx - p[2]) * spacing[2]) ** 2)
            reg = np.zeros_like(mask); reg[sl] = d <= 4
        out |= reg
    return out


def shrink(mask, points, spacing):
    """Cut away the part of the outline at each 'remove' click (watershed split)."""
    if not points or not mask.any():
        return mask
    markers = np.zeros(mask.shape, np.int32)
    dist = ndi.distance_transform_edt(mask, sampling=spacing)
    # 'keep' seed = the deepest point of the outline that is not near a remove click
    d = dist.copy()
    for p in points:
        sl = _box(mask.shape, p, spacing, 8)
        d[sl] = 0
        markers[tuple(int(round(v)) for v in p)] = 2
    if d.max() == 0:
        return np.zeros_like(mask)
    markers[np.unravel_index(d.argmax(), d.shape)] = 1
    ws = watershed(-dist, markers, mask=mask)
    out = ws == 1
    # On a round blob the watershed cuts almost nothing; then act as an eraser around the click
    # (radius: 30% of the blob's size, at least 2 mm).
    size_mm = 2 * dist.max()
    r = max(2.0, 0.3 * size_mm)
    for p in points:
        sl = _box(mask.shape, p, spacing, 2 * r + 2)
        zz, yy, xx = np.ogrid[sl]
        ball = (((zz - p[0]) * spacing[0]) ** 2 + ((yy - p[1]) * spacing[1]) ** 2 + ((xx - p[2]) * spacing[2]) ** 2) <= r * r
        out[sl] &= ~ball
    lab, _ = ndi.label(out, np.ones((3, 3, 3)))  # keep the main piece
    if lab.max() > 1:
        out = lab == np.bincount(lab[lab > 0]).argmax()
    return out


def replace_slice(mask, z, polygon_yx):
    out = mask.copy()
    out[z] = False
    if polygon_yx:
        p = np.asarray(polygon_yx, float)
        rr, cc = draw_polygon(p[:, 0], p[:, 1], shape=mask.shape[1:])
        out[z, rr, cc] = True
    return out
