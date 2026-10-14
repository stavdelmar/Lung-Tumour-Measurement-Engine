"""Classic (non-AI) box-prompted 3D tumour outline.

The researcher draws a box around the tumour on one slice. We grow the tumour
in 3D inside that box: keep tissue denser than lung (HU threshold), cut thin
vessel bridges with a morphological opening, and keep only the blob that holds
the box centre. No training, runs in seconds on a laptop CPU.
"""
import numpy as np
import SimpleITK as sitk
from scipy import ndimage as ndi

def segment_box(ct_arr, spacing, z, box, hu_min=-500, open_mm=2.0, margin=0.15):
    """ct_arr: z,y,x HU. box: (y0, y1, x0, x1) on slice z. Returns bool mask."""
    y0, y1, x0, x1 = box
    h, w = y1 - y0, x1 - x0
    my, mx = int(h * margin), int(w * margin)
    y0, y1 = max(0, y0 - my), min(ct_arr.shape[1], y1 + my)
    x0, x1 = max(0, x0 - mx), min(ct_arr.shape[2], x1 + mx)
    size_mm = max(h, w) * spacing[0]
    dz = int(np.ceil(0.75 * size_mm / spacing[2])) + 2
    z0, z1 = max(0, z - dz), min(ct_arr.shape[0], z + dz + 1)
    roi = ct_arr[z0:z1, y0:y1, x0:x1].astype(np.float32)
    roi = ndi.median_filter(roi, size=(1, 3, 3))
    fg = roi > hu_min
    r = max(1, int(round(open_mm / spacing[0])))
    st = np.zeros((1, 2 * r + 1, 2 * r + 1), bool)
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    st[0] = yy ** 2 + xx ** 2 <= r * r
    fg = ndi.binary_opening(fg, structure=st)
    lab, n = ndi.label(fg)
    if n == 0:
        return np.zeros(ct_arr.shape, bool)
    cz, cy, cx = z - z0, (box[0] + box[1]) // 2 - y0, (box[2] + box[3]) // 2 - x0
    seed = lab[cz, cy, cx]
    if seed == 0:  # centre fell on lung: take the biggest blob on the prompt slice
        ids, cnt = np.unique(lab[cz][lab[cz] > 0], return_counts=True)
        if len(ids) == 0:
            return np.zeros(ct_arr.shape, bool)
        seed = ids[np.argmax(cnt)]
    keep = lab == seed
    keep = np.stack([ndi.binary_fill_holes(s) for s in keep])
    out = np.zeros(ct_arr.shape, bool)
    out[z0:z1, y0:y1, x0:x1] = keep
    return out

def box_from_expert(mask):
    """Simulate the researcher's box: the expert's widest slice, tight bounding box."""
    areas = mask.sum(axis=(1, 2))
    z = int(np.argmax(areas))
    ys, xs = np.nonzero(mask[z])
    return z, (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1)


def _disk(r):
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    return yy ** 2 + xx ** 2 <= r * r

def segment_box_v2(ct_arr, spacing, z, box, hu_min=-450, open_mm=2.5, grow_mm=2.5, max_growth=1.25, z_frac=0.8, max_area_frac=1.3):
    """Slice-by-slice version: start on the prompted slice, then walk up and down.
    Each new slice may only extend a little beyond the previous one (no leaks into
    chest wall or vessels), and must stay inside an ellipse fitted to the box."""
    y0, y1, x0, x1 = box
    H, W = ct_arr.shape[1:]
    cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
    ry, rx = (y1 - y0) / 2 * 1.2 + 2, (x1 - x0) / 2 * 1.2 + 2
    yy, xx = np.ogrid[:H, :W]
    ellipse = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1
    ro = max(1, int(round(open_mm / spacing[0])))
    rg = max(1, int(round(grow_mm / spacing[0])))
    so, sg = _disk(ro), _disk(rg)

    def slice_fg(k):
        s = ndi.median_filter(ct_arr[k].astype(np.float32), size=3)
        fg = (s > hu_min) & ellipse
        return ndi.binary_opening(fg, structure=so)

    out = np.zeros(ct_arr.shape, bool)
    fg = slice_fg(z)
    lab, n = ndi.label(fg)
    seed = lab[int(cy), int(cx)]
    if seed == 0:
        ids, cnt = np.unique(lab[lab > 0], return_counts=True)
        if len(ids) == 0:
            return out
        seed = ids[np.argmax(cnt)]
    out[z] = ndi.binary_fill_holes(lab == seed)
    ref_area = out[z].sum()
    size_mm = max(y1 - y0, x1 - x0) * spacing[0]
    max_dz = int(np.ceil(z_frac * size_mm / spacing[2]))
    for step in (1, -1):
        prev = out[z]
        k = z + step
        while 0 <= k < ct_arr.shape[0] and prev.sum() > 3 and abs(k - z) <= max_dz:
            allowed = ndi.binary_dilation(prev, structure=sg)
            fg = slice_fg(k) & allowed
            lab, n = ndi.label(fg)
            if n == 0:
                break
            ids = np.unique(lab[prev & (lab > 0)])
            cur = ndi.binary_fill_holes(np.isin(lab, ids)) if len(ids) else np.zeros_like(prev)
            if cur.sum() == 0:
                break
            if cur.sum() > max_growth * prev.sum() or cur.sum() > max_area_frac * ref_area:
                cur = cur & ndi.binary_erosion(prev, structure=sg)  # leaking: shrink, so a leak dies out
            out[k] = cur
            prev = cur
            k += step
    return out


def lung_field(ct_slice, spacing, close_mm=15.0):
    """Lung region on one slice, including tumours stuck to the chest wall.
    Air inside the body = lung; a large 'rolling ball' closing then pulls in
    dense blobs sitting on the lung edge, while the chest wall stays out."""
    air = ct_slice < -400
    lab, n = ndi.label(air)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    lung = air & ~np.isin(lab, border)
    lab, n = ndi.label(lung)
    if n:
        sizes = ndi.sum(lung, lab, range(1, n + 1))
        lung = np.isin(lab, 1 + np.nonzero(sizes > 2000)[0])
    r = max(1, int(round(close_mm / spacing[0])))
    pad = r + 1
    big = np.pad(lung, pad)
    big = ndi.binary_closing(big, structure=_disk(r))
    return ndi.binary_fill_holes(big[pad:-pad, pad:-pad])

def segment_box_v3(ct_arr, spacing, z, box, **kw):
    """v2 restricted to the lung field (so it cannot spill into the chest wall)."""
    y0, y1, x0, x1 = box
    m = 40
    Y0, Y1, X0, X1 = max(0, y0 - m * 4), min(ct_arr.shape[1], y1 + m * 4), max(0, x0 - m * 4), min(ct_arr.shape[2], x1 + m * 4)
    masked = ct_arr.copy()
    size_mm = max(y1 - y0, x1 - x0) * spacing[0]
    dz = int(np.ceil(0.9 * size_mm / spacing[2])) + 2
    for k in range(max(0, z - dz), min(ct_arr.shape[0], z + dz + 1)):
        lf = lung_field(ct_arr[k], spacing)
        masked[k][~lf] = -1000
    return segment_box_v2(masked, spacing, z, box, **kw)


_INFERER = None

def ai_lung_field(ct_img, z0, z1):
    """Lung mask from the lungmask R231 deep-learning model (trained to keep tumours
    inside the lung). Runs only on slices z0..z1 to stay fast on a laptop CPU."""
    global _INFERER
    if _INFERER is None:
        from lungmask import LMInferer
        _INFERER = LMInferer(modelname="R231", force_cpu=True, tqdm_disable=True, batch_size=2)
    sub = ct_img[:, :, z0:z1]
    return _INFERER.apply(sub) > 0  # z,y,x

def segment_box_v4(ct_img, ct_arr, spacing, z, box, **kw):
    """Hybrid: AI finds the lung (tumours included), the box method outlines the tumour inside it."""
    y0, y1, x0, x1 = box
    size_mm = max(y1 - y0, x1 - x0) * spacing[0]
    dz = int(np.ceil(0.9 * size_mm / spacing[2])) + 2
    z0, z1 = max(0, z - dz), min(ct_arr.shape[0], z + dz + 1)
    lung = ai_lung_field(ct_img, z0, z1)
    masked = np.full(ct_arr.shape, -1000, ct_arr.dtype)
    masked[z0:z1][lung] = ct_arr[z0:z1][lung]
    return segment_box_v2(masked, spacing, z, box, **kw)


import os
from skimage.morphology import convex_hull_image

def cached_lung(ct_img, z0, z1, key, cache_dir):
    """lungmask output for slices z0..z1, saved to disk so repeated runs are instant."""
    os.makedirs(cache_dir, exist_ok=True)
    f = os.path.join(cache_dir, f"{key}_{z0}_{z1}.npz")
    if os.path.exists(f):
        return np.load(f)["m"]
    m = ai_lung_field(ct_img, z0, z1)
    np.savez_compressed(f, m=m)
    return m

def hull_field(lung2d):
    """Each lung's convex hull: adds the inner 'bay' by the mediastinum where central tumours sit."""
    lab, n = ndi.label(lung2d)
    out = lung2d.copy()
    for i in range(1, n + 1):
        comp = lab == i
        if comp.sum() > 2000:
            out |= convex_hull_image(comp)
    return out

def segment_box_v5(ct_img, ct_arr, spacing, z, box, key="case", cache_dir="/tmp/lungcache", **kw):
    y0, y1, x0, x1 = box
    size_mm = max(y1 - y0, x1 - x0) * spacing[0]
    dz = int(np.ceil(0.9 * size_mm / spacing[2])) + 2
    z0, z1 = max(0, z - dz), min(ct_arr.shape[0], z + dz + 1)
    lung = cached_lung(ct_img, z0, z1, key, cache_dir)
    field = np.stack([hull_field(s) for s in lung])
    masked = np.full(ct_arr.shape, -1000, ct_arr.dtype)
    masked[z0:z1][field] = ct_arr[z0:z1][field]
    p = segment_box_v2(masked, spacing, z, box, **kw)
    if p.sum() * spacing[0] * spacing[1] * spacing[2] < 0.25 * _box_volume_mm3(box, spacing):
        q = segment_box_v2(masked, spacing, z, box, **{**kw, "open_mm": 0.8})  # thin tumour: gentler clean-up
        if q.sum() > p.sum():
            p = q
    return p

def _box_volume_mm3(box, spacing):
    """Rough volume of an ellipsoid fitted in the box (for 'did we lose the tumour?' checks)."""
    h = (box[1] - box[0]) * spacing[1]; w = (box[3] - box[2]) * spacing[0]
    return 4 / 3 * np.pi * (h / 2) * (w / 2) * (min(h, w) / 2) * 0.15
