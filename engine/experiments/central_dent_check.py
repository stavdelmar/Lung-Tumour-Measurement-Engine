"""'Check here' flag for central masses the nodule model misses (hilum / mediastinum).

Idea (as in classic engine v5's convex-hull check): a solid tumour lying against the mediastinum or
the hilum is left OUT of the lung mask, so the lung outline gets a dent there. Per axial slice we close
each lung with a large disk (fills dents narrower than ~2 x CLOSE_MM), keep the soft tissue that the
closing adds, cut thin structures (vessels, bronchial walls) with an opening, and keep compact 3D
blobs above a size limit that no AI finding already covers. They are reported as REGIONS TO CHECK,
never as findings, and never measured or exported.

Usage (evaluation): python -m engine.central_check NII_DIR CACHE_DIR OUT_CSV
"""
import json, os, sys, time
import numpy as np
import SimpleITK as sitk
from scipy import ndimage as ndi

CLOSE_MM = 15.0     # dents narrower than ~30 mm are closed
SOFT_HU = -150      # tumour / soft tissue
OPEN_MM = 4.0       # removes structures thinner than ~8 mm (most vessels outside the hilum)
MIN_ML = float(os.environ.get("CC_MIN_ML", 2.0))       # smallest region worth a flag (~18 mm sphere)
MIN_Z_MM = 10.0
BLOB_MM = float(os.environ.get("CC_BLOB_MM", 5.0))   # ball radius for the 'compact lump' test
EDGE_MM = 4.0       # include tissue this close to the lung edge (tumours pushed out of the lung mask)


def _disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def candidates(hu, lobes, spacing_zyx, findings_mask=None, step=2):
    """Return list of dicts (one per region to check) and the region label map (z,y,x).
    Works at half in-plane resolution (~1.4 mm pixels) for speed; the map is returned at that grid
    (`step` tells the caller); centres/bboxes are given on the full grid."""
    hu, lobes = hu[:, ::step, ::step], lobes[:, ::step, ::step]
    if findings_mask is not None:
        findings_mask = findings_mask[:, ::step, ::step]
    sz, sy, sx = spacing_zyx[0], spacing_zyx[1] * step, spacing_zyx[2] * step
    mode = os.environ.get("CC_MODE", "blob")
    dent = np.zeros(hu.shape, bool)
    if mode in ("dent", "both"):
        rc = max(1, int(round(CLOSE_MM / sy)))
        ro = max(1, int(round(OPEN_MM / sy)))
        pad = rc + 2
        d = np.zeros(hu.shape, bool)
        for side in ((1, 2, 3), (4, 5)):           # right lung, left lung separately
            lung = np.isin(lobes, side)
            for k in np.nonzero(lung.any(axis=(1, 2)))[0]:
                sl = np.pad(lung[k], pad)
                closed = ndi.binary_closing(sl, _disk(rc))[pad:-pad, pad:-pad]
                d[k] |= closed & ~lung[k]
        d &= (hu > SOFT_HU) & ~(lobes > 0)
        dent |= ndi.binary_opening(d, _disk(ro)[None])
    if mode in ("blob", "both"):
        # compact solid tissue inside (or touching) the lungs: a 3D opening with a ball of BLOB_MM radius
        # removes vessels and bronchial walls (thinner than ~2 x BLOB_MM) but keeps tumour-sized lumps
        lung = ndi.binary_dilation(lobes > 0, _disk(max(1, int(round(EDGE_MM / sy))))[None])
        solid = (hu > SOFT_HU) & lung
        r = max(1, int(round(BLOB_MM / sy))); rz = max(1, int(round(BLOB_MM / sz)))
        zz, yy, xx = np.ogrid[-rz:rz + 1, -r:r + 1, -r:r + 1]
        ball = (zz * sz) ** 2 + (yy * sy) ** 2 + (xx * sx) ** 2 <= BLOB_MM ** 2
        dent |= ndi.binary_opening(solid, ball)
    lab, n = ndi.label(dent, np.ones((3, 3, 3)))
    out, keep = [], np.zeros(lab.shape, np.int16)
    for i, s in enumerate(ndi.find_objects(lab), 1):
        m = lab[s] == i
        ml = m.sum() * sz * sy * sx / 1000
        zext = (s[0].stop - s[0].start) * sz
        if ml < MIN_ML or zext < MIN_Z_MM:
            continue
        if findings_mask is not None and (findings_mask[s] & m).sum() > 0.3 * m.sum():
            continue                                 # already an AI finding
        keep[s][m] = len(out) + 1
        zz, yy, xx = np.nonzero(m)
        out.append(dict(region_id=f"C{len(out) + 1}", volume_ml=round(float(ml), 1),
                        z_extent_mm=round(float(zext), 1),
                        center_voxel=[round(float(zz.mean() + s[0].start), 1),
                                      round(float((yy.mean() + s[1].start) * step), 1),
                                      round(float((xx.mean() + s[2].start) * step), 1)],
                        bbox=[[int(s[0].start), int(s[0].stop)]] + [[int(a.start) * step, int(a.stop) * step] for a in s[1:]],
                        label="possible central mass, please check"))
    return out, keep


def main():
    nii, cache, out_csv = sys.argv[1:4]
    import csv
    done = set()
    if os.path.exists(out_csv):
        done = {r["scan"] for r in csv.DictReader(open(out_csv))}
    f = open(out_csv, "a", newline="")
    w = csv.writer(f)
    if not done:
        w.writerow(["scan", "n_flags", "flag_on_tumour", "tumour_ml", "flag_ml", "other_flags_ml", "seconds"])
    t0 = time.time()
    for npz in sorted(os.listdir(cache)):
        sid = npz[:-4]
        if sid in done or not npz.endswith(".npz"):
            continue
        if time.time() - t0 > float(os.environ.get("MAX_S", "1e9")):
            break
        t = time.time()
        z = np.load(f"{cache}/{npz}")
        img = sitk.ReadImage(f"{nii}/{sid}_ct.nii.gz")
        hu = sitk.GetArrayFromImage(img)
        sp = tuple(np.array(img.GetSpacing())[::-1])
        expert = sitk.GetArrayFromImage(sitk.ReadImage(f"{nii}/{sid}_expert.nii.gz")) > 0
        regs, lab = candidates(hu, z["lobes"], sp, z["nod"])
        near = ndi.binary_dilation(expert[:, ::2, ::2], iterations=3)
        on = [r for i, r in enumerate(regs, 1) if (lab == i)[near].any()]
        other = [r for r in regs if r not in on]
        w.writerow([sid, len(regs), bool(on), round(expert.sum() * np.prod(sp) / 1000, 1),
                    sum(r["volume_ml"] for r in on), round(sum(r["volume_ml"] for r in other), 1),
                    round(time.time() - t, 1)])
        f.flush()
        print(sid, len(regs), "on tumour" if on else "", round(time.time() - t, 1), flush=True)


if __name__ == "__main__":
    main()
