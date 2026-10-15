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
