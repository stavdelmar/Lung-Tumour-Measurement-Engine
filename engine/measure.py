"""Measure nodules the way Daniel does.

- Long axis: longest edge-to-edge diameter on the axial slice where the nodule is largest.
- Short axis: longest diameter perpendicular to the long axis, on that same slice.
- Mean diameter = (long + short) / 2   (his sheet's formula).
- Volume (mm3) from the 3D outline, for every nodule (today he only has it for ~1 in 5).
- Lobe from the lobe map; Type (Solid / Part-solid / Ground-glass) from CT density - a draft he confirms.
Distances use pixel corners (edge to edge, like a caliper), not pixel centres.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import ConvexHull

SOLID_HU = -300  # voxels denser than this count as solid tissue (= looks solid on the lung window)


def _corners(ys, xs, sy, sx):
    c = []
    for dy in (-0.5, 0.5):
        for dx in (-0.5, 0.5):
            c.append(np.stack([(ys + dy) * sy, (xs + dx) * sx], 1))
    return np.concatenate(c)


def axes_2d(m2d, sy, sx):
    """Long axis, short axis (mm) and the two segments' endpoints [(y,x) px] for one slice."""
    ys, xs = np.nonzero(m2d)
    if len(ys) == 0:
        return 0.0, 0.0, None, None
    pts = _corners(ys.astype(float), xs.astype(float), sy, sx)
    try:
        hull = pts[ConvexHull(pts).vertices]
    except Exception:
        hull = pts
    d = np.sqrt(((hull[:, None] - hull[None]) ** 2).sum(-1))
    i, j = np.unravel_index(d.argmax(), d.shape)
    long_mm = float(d[i, j])
    u = (hull[j] - hull[i]) / max(long_mm, 1e-6)
    v = np.array([-u[1], u[0]])
    # short axis: longest chord perpendicular to u. Bin pixels by position along u.
    cen = np.stack([ys * sy, xs * sx], 1).astype(float)
    a, b = cen @ u, cen @ v
    w = min(sy, sx)
    bins = np.floor((a - a.min()) / w).astype(int)
    half = 0.5 * (abs(v[0]) * sy + abs(v[1]) * sx)  # pixel half-extent along v
    best, seg = 0.0, None
    for k in np.unique(bins):
        sel = bins == k
        lo, hi = b[sel].min() - half, b[sel].max() + half
        if hi - lo > best:
            best = hi - lo
            am = a[sel].mean()
            p0, p1 = am * u + lo * v, am * u + hi * v
            seg = (p0 / [sy, sx], p1 / [sy, sx])
    long_seg = (hull[i] / [sy, sx], hull[j] / [sy, sx])
    return long_mm, float(best), long_seg, seg


def measure_nodule(mask, ct_hu, spacing_zyx, lobe_map=None, instance_numbers=None):
    """mask: bool (z,y,x) for ONE nodule. Returns the sheet fields + geometry for the viewer."""
    sz, sy, sx = spacing_zyx
    zs = np.nonzero(mask.any(axis=(1, 2)))[0]
    best = (-1, 0, 0, None, None)
    for z in zs:
        L, S, ls, ss = axes_2d(mask[z], sy, sx)
        if L > best[1]:
            best = (int(z), L, S, ls, ss)
    z, L, S, ls, ss = best
    vox = mask.sum()
    vol = float(vox * sz * sy * sx)
    hu = ct_hu[mask]
    solid = mask & (ct_hu > SOLID_HU)
    # judge density on the core (edge voxels are blurred with air and look falsely 'ground-glass')
    core = ndi.binary_erosion(mask, np.ones((1, 3, 3)))
    if core.sum() < 0.3 * vox:
        core = mask
    solid_frac = float((core & (ct_hu > SOLID_HU)).sum() / max(core.sum(), 1))
    if solid_frac >= 0.8:
        typ, solid_mm = "Solid", None
    elif solid_frac < 0.1:
        typ, solid_mm = "Ground-glass", None
    else:
        typ = "Part-solid"
        # Daniel's SOP: solid component = long axis of the solid core, measured on the lung window, on the
        # key slice (where the nodule's long axis is measured). "Solid on the lung window" = denser than
        # SOLID_HU (-300 HU), the tissue that stays white like vessels; the faint ground-glass rim does not.
        solid_mm = round(axes_2d(solid[z], sy, sx)[0], 1) if solid[z].any() else 0.0
    lobe, touches = None, False
    if lobe_map is not None:
        lab = lobe_map[mask]
        touches = bool((lab == 0).mean() > 0.2)
        lab = lab[lab > 0]
        if len(lab) == 0:  # nodule on the lung edge: take the nearest lobe
            sub = tuple(slice(max(int(np.min(i)) - 15, 0), int(np.max(i)) + 16) for i in np.nonzero(mask))
            lm = lobe_map[sub]
            if lm.any():
                _, idx = ndi.distance_transform_edt(lm == 0, sampling=spacing_zyx, return_indices=True)
                c = tuple(int(np.mean(i)) for i in np.nonzero(mask[sub]))
                lab = np.array([lm[idx[0][c], idx[1][c], idx[2][c]]])
        if len(lab):
            from .detect import LOBE_CODE
            lobe = LOBE_CODE[int(np.bincount(lab).argmax())]
    cz, cy, cx = [float(np.mean(i)) for i in np.nonzero(mask)]
    r = lambda x: None if x is None else round(float(x), 1)
    return dict(
        lobe=lobe, slice_index=z,
        slice_number=int(instance_numbers[z]) if instance_numbers is not None else z + 1,
        type=typ, long_axis_mm=r(L), short_axis_mm=r(S), mean_diameter_mm=r((L + S) / 2),
        solid_component_mm=solid_mm, volume_mm3=round(vol), mean_hu=round(float(hu.mean())),
        solid_fraction=round(solid_frac, 2), center_voxel=[round(cz, 1), round(cy, 1), round(cx, 1)],
        long_axis_px=[[round(float(p[0]), 1), round(float(p[1]), 1)] for p in ls] if ls else None,
        short_axis_px=[[round(float(p[0]), 1), round(float(p[1]), 1)] for p in ss] if ss else None,
        n_slices=int(len(zs)), touches_pleura=touches)


def components(nod_mask, prob=None, spacing_zyx=(1, 1, 1), min_long_mm=4.0, ct_hu=None, **kw):
    """Split the nodule mask into separate nodules, measure each, drop those < min_long_mm.
    Returns (list of dicts sorted by size, label map)."""
    lab, n = ndi.label(nod_mask, structure=np.ones((3, 3, 3)))
    out, keep = [], np.zeros_like(lab, dtype=np.int16)
    objs = ndi.find_objects(lab)
    k = 0
    for i, sl in enumerate(objs, 1):
        m = lab == i
        m_sl = m[sl]
        meas = measure_nodule(m_sl, ct_hu[sl], spacing_zyx, kw.get("lobe_map")[sl] if kw.get("lobe_map") is not None else None, None)
        if meas["long_axis_mm"] < min_long_mm:
            continue
        # translate crop-relative coordinates back to the full scan
        off = np.array([s.start for s in sl], float)
        meas["slice_index"] += int(off[0])
        inst = kw.get("instance_numbers")
        meas["slice_number"] = int(inst[meas["slice_index"]]) if inst is not None else meas["slice_index"] + 1
        meas["center_voxel"] = [round(c + o, 1) for c, o in zip(meas["center_voxel"], off)]
        for key in ("long_axis_px", "short_axis_px"):
            if meas[key]:
                meas[key] = [[p[0] + off[1], p[1] + off[2]] for p in meas[key]]
        # The model's MAX probability saturates at 1.0 for every finding, so it says nothing. Instead:
        # confidence = mean model probability over the drawn outline = how much of the outline the
        # model itself marked (low = the outline was mostly extended by the rim step -> check the edges).
        meas["confidence"] = round(float(prob[m].astype(np.float32).mean()), 2) if prob is not None else None
        meas["detection_max_prob"] = round(float(prob[m].max()), 2) if prob is not None else None
        meas["bbox"] = [[int(s.start), int(s.stop)] for s in sl]
        k += 1
        keep[m] = k
        out.append(meas)
    order = np.argsort([-o["volume_mm3"] for o in out])
    out = [out[i] for i in order]
    remap = np.zeros(k + 1, np.int16)
    for new, old in enumerate(order, 1):
        remap[old + 1] = new
        out[new - 1]["nodule_id"] = f"N{new}"
    return out, remap[keep]


def spur_mm(mask, spacing_zyx, open_mm=1.5):
    """How much of the long axis comes from a thin protrusion (e.g. a vessel tail stuck to the outline).
    = long axis of the outline minus long axis after an in-plane opening that removes parts thinner
    than ~2 x open_mm. Same slice-search as Daniel's measurement. 0 = no tail."""
    sz, sy, sx = spacing_zyx
    r = max(1, int(round(open_mm / sy)))
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    opened = ndi.binary_opening(mask, (yy ** 2 + xx ** 2 <= r * r)[None])
    if not opened.any():
        return 0.0
    L = lambda m: max(axes_2d(m[z], sy, sx)[0] for z in np.nonzero(m.any(axis=(1, 2)))[0])
    return round(max(0.0, L(mask) - L(opened)), 1)
