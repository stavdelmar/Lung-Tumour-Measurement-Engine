"""Outline refinement after detection.

The nodule model outlines the dense core well but tends to leave out the faint ground-glass rim
(seen on the first RIDER scan: long axis 9.8 mm vs expert 15.0 mm). Daniel measures the WHOLE nodule,
rim included, so we test refiners on top of the model outline:

- `halo`: grow the model outline into connected voxels denser than -750 HU, at most `band_mm` away,
  then cut thin vessel bridges. Cheap, CPU-friendly.
- MedSAM 2 (box prompt from the detection) is tested in the Colab exam; it needs a GPU.
"""
import numpy as np
from scipy import ndimage as ndi


def halo(mask, hu, spacing, band_mm=4.0, hu_min=-750, lungs=None):
    if not mask.any():
        return mask
    pad = np.ceil(band_mm / np.asarray(spacing)).astype(int) + 2
    zs, ys, xs = np.nonzero(mask)
    sl = tuple(slice(max(int(a.min()) - p, 0), int(a.max()) + p + 1) for a, p in zip((zs, ys, xs), pad))
    m = mask[sl]
    dist = ndi.distance_transform_edt(~m, sampling=spacing)
    allowed = (hu[sl] > hu_min) & (dist <= band_mm)
    if lungs is not None:
        allowed &= ndi.binary_dilation(lungs[sl] > 0, iterations=2)
    grown = m.copy()
    for _ in range(int(np.ceil(band_mm / min(spacing))) + 1):  # geodesic growth from the core
        nxt = ndi.binary_dilation(grown, np.ones((3, 3, 3))) & allowed | m
        if (nxt == grown).all():
            break
        grown = nxt
    # cut vessel bridges: in-plane opening of the added rim only, keep what touches the core
    rim = ndi.binary_opening(grown & ~m, np.ones((1, 3, 3)))
    out = m | rim
    lab, _ = ndi.label(out, np.ones((3, 3, 3)))
    keep = np.unique(lab[m]); keep = keep[keep > 0]
    out = np.isin(lab, keep)
    full = mask.copy(); full[sl] = out
    return full


def halo_per_nodule(nod, hu, spacing, lungs=None, hu_min=-750, max_band=4.0, frac=0.25):
    """Halo applied to each model blob separately, with the growth band scaled to the blob's size
    (25% of its core diameter, 1-4 mm). The 59-scan exam only had tumours of 14-66 mm; a fixed 4 mm
    band would inflate 4-6 mm nodules (and push sub-4 mm specks over the 4 mm reporting line)."""
    lab, n = ndi.label(nod, np.ones((3, 3, 3)))
    out = np.zeros_like(nod)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        core = lab[sl] == i
        d = 2 * ((core.sum() * np.prod(spacing) * 3 / (4 * np.pi)) ** (1 / 3))  # equivalent diameter
        band = float(np.clip(frac * d, 1.0, max_band))
        pad = int(np.ceil(band / min(spacing))) + 3
        big = tuple(slice(max(s.start - pad, 0), s.stop + pad) for s in sl)
        m = np.zeros(nod[big].shape, bool)
        m[tuple(slice(s.start - b.start, s.stop - b.start) for s, b in zip(sl, big))] = core
        g = halo(m, hu[big], spacing, band, hu_min, None if lungs is None else lungs[big])
        out[big] |= g
    return out


def halo_adaptive(nod, hu, spacing, lungs=None, hu_min=-750, max_band=4.0, step=1.0, keep_frac=0.5, full_band_core_mm=16.0, speck_core_mm=3.5, rim_max_hu=None):
    """Halo per model blob, band chosen by the IMAGE, not by the blob's size: grow in `step` mm shells
    up to `max_band`, and stop when less than `keep_frac` of a new shell is tissue (> hu_min).
    A faint rim around the core keeps the growth going; air around a small solid nodule stops it early.
    Reason (16 Oct re-measure): the model sometimes marks only a 4-7 mm piece of a 13-20 mm part-solid
    tumour, so a band scaled to the core's size is far too small there.
    Cores >= `full_band_core_mm` (equivalent diameter) get the full band, as in the 59-scan exam
    (on large tumours the adaptive stop shortened the long axis by ~2 mm). Specks with cores < `speck_core_mm`
    keep a 1 mm band. Opt-in (ENGINE_OUTLINE=hybrid) since 17 Oct; see pipeline.py."""
    lab, n = ndi.label(nod, np.ones((3, 3, 3)))
    out = np.zeros_like(nod)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        pad = int(np.ceil(max_band / min(spacing))) + 3
        big = tuple(slice(max(s.start - pad, 0), s.stop + pad) for s in sl)
        core = lab[big] == i
        d = 2 * ((core.sum() * np.prod(spacing) * 3 / (4 * np.pi)) ** (1 / 3))
        if d < speck_core_mm:  # model speck: keep the old 1 mm band (else a vessel/pleura can grow it into a 'finding')
            out[big] |= halo(core, hu[big], spacing, step, hu_min, None if lungs is None else lungs[big])
            continue
        if d >= full_band_core_mm:
            out[big] |= halo(core, hu[big], spacing, max_band, hu_min, None if lungs is None else lungs[big])
            continue
        dist = ndi.distance_transform_edt(~core, sampling=spacing)
        tissue = hu[big] > hu_min
        if rim_max_hu is not None:  # count only faint (ground-glass-like) rim, not dense vessels
            tissue &= hu[big] < rim_max_hu
        inlung = (lungs[big] > 0) if lungs is not None else np.ones_like(core)
        band = step
        while band < max_band:
            # only lung voxels count: next to the pleura the chest wall is 'tissue' and would keep it growing
            shell = (dist > band) & (dist <= band + step) & inlung
            if shell.any() and (tissue & shell).sum() / shell.sum() < keep_frac:
                break
            band += step
        g = halo(core, hu[big], spacing, band, hu_min, None if lungs is None else lungs[big])
        out[big] |= g
    return out
