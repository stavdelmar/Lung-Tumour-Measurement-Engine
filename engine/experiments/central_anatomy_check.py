"""Central-mass check v2 (anatomy subtraction), development script.
Soft tissue inside the hull of both lungs that the 3 mm TotalSegmentator model does NOT explain as an
organ (heart, aorta, veins, oesophagus, trachea, bone, muscle) and that touches the lung.
Saves the 3 mm anatomy map so the run can be repeated with other thresholds."""
import os, sys, json, time
import numpy as np, SimpleITK as sitk
from scipy import ndimage as ndi
from skimage.morphology import convex_hull_image
sys.path.insert(0, "/home/claude/lung-tumour-measurement-tool")

U = "/mnt/user-data/uploads/lung-tumour-project/work.nosync/nii"
OUT = "/home/claude/cc/anat"
os.makedirs(OUT, exist_ok=True)


def anatomy(sid):
    f = f"{OUT}/{sid}.npz"
    if os.path.exists(f):
        z = np.load(f); return z["seg"], z["hu"], z["ex"], tuple(z["sp"])
    from engine import detect
    ref = sitk.ReadImage(f"{U}/{sid}_ct.nii.gz")
    size3 = [int(round(s * p / 3.0)) for s, p in zip(ref.GetSize(), ref.GetSpacing())]
    small = sitk.Resample(ref, size3, sitk.Transform(), sitk.sitkLinear, ref.GetOrigin(), [3.0] * 3,
                          ref.GetDirection(), -1024, sitk.sitkInt16)
    seg, _ = detect._run(detect.LOBE_MODEL, small)
    ex = sitk.ReadImage(f"{U}/{sid}_expert.nii.gz")
    ex3 = sitk.GetArrayFromImage(sitk.Resample(ex, small, sitk.Transform(), sitk.sitkNearestNeighbor, 0)) > 0
    hu = sitk.GetArrayFromImage(small)
    np.savez_compressed(f, seg=seg.astype(np.uint8), hu=hu, ex=ex3, sp=(3.0, 3.0, 3.0))
    return seg, hu, ex3, (3.0, 3.0, 3.0)


def flags(seg, hu, soft=-20, min_ml=3.0, open_r=1):
    lung = np.isin(seg, (10, 11, 12, 13, 14))
    organ = (seg > 0) & ~lung
    hull = np.zeros_like(lung)
    for k in np.nonzero(lung.any(axis=(1, 2)))[0]:
        hull[k] = convex_hull_image(lung[k])
    near_lung = ndi.binary_dilation(lung, iterations=1)
    cand = (hu > soft) & ~organ & ~lung & hull
    cand = ndi.binary_opening(cand, ndi.generate_binary_structure(3, 1), iterations=open_r)
    lab, n = ndi.label(cand)
    out = np.zeros(lab.shape, np.int16); regs = []
    for i, s in enumerate(ndi.find_objects(lab), 1):
        m = lab[s] == i
        ml = m.sum() * 27 / 1000
        if ml < min_ml or not (near_lung[s] & m).any():
            continue
        regs.append(dict(ml=round(ml, 1), touch=round(float((near_lung[s] & m).sum() / m.sum()), 2)))
        out[s][m] = len(regs)
    return regs, out


if __name__ == "__main__":
    for sid in sys.argv[1:]:
        t = time.time()
        seg, hu, ex, sp = anatomy(sid)
        regs, lab = flags(seg, hu)
        hit = set(np.unique(lab[ndi.binary_dilation(ex, iterations=1)])) - {0}
        print(sid, f"tumour {ex.sum()*27/1000:.1f} ml, organ-labelled {((seg[ex]>0)&~np.isin(seg[ex],(10,11,12,13,14))).mean():.2f}",
              "| flags:", [(r["ml"], r["touch"], "TUMOUR" if i + 1 in hit else "") for i, r in enumerate(regs)],
              f"{time.time()-t:.0f}s", flush=True)
