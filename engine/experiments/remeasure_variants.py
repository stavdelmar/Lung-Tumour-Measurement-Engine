"""Compare halo variants on the expert tumour for the given scans (from the Colab cache)."""
import json, sys, csv
import numpy as np, SimpleITK as sitk
from scipy import ndimage as ndi
from engine import measure, outline

def run(nii, cache, keys, frac):
    rows = []
    for key in keys:
        pid, scan = key.rsplit("_", 1)
        ct = sitk.ReadImage(f"{nii}/{pid}_{scan}_ct.nii.gz"); hu = sitk.GetArrayFromImage(ct)
        sp = tuple(np.array(ct.GetSpacing())[::-1])
        m = sitk.GetArrayFromImage(sitk.ReadImage(f"{nii}/{pid}_{scan}_expert.nii.gz")) > 0
        z = np.load(f"{cache}/{pid}_{scan}.npz"); core, lobes = z["nod"], z["lobes"]
        e = measure.measure_nodule(m, hu, sp)
        r = dict(key=key, exp_L=e["long_axis_mm"], exp_V=e["volume_mm3"])
        for name, fn in (("fixed", lambda: outline.halo(core, hu, sp, 4.0, -750, lobes)),
                         ("scaled", lambda: outline.halo_per_nodule(core, hu, sp, lobes)),
                         ("adaptive", lambda: outline.halo_adaptive(core, hu, sp, lobes, keep_frac=frac))):
            o = fn(); lab, _ = ndi.label(o, np.ones((3, 3, 3)))
            ids, c = np.unique(lab[m & (lab > 0)], return_counts=True); pm = lab == ids[c.argmax()]
            q = measure.measure_nodule(pm, hu, sp)
            r[f"{name}_dL"] = round(q["long_axis_mm"] - e["long_axis_mm"], 1)
            r[f"{name}_dV%"] = round(100 * (q["volume_mm3"] / e["volume_mm3"] - 1))
            r[f"{name}_dice"] = round(2 * (pm & m).sum() / (pm.sum() + m.sum()), 2)
            # other candidates >= 4 mm (long axis) besides the tumour
            n = 0
            for j, s in enumerate(ndi.find_objects(lab), 1):
                if j in ids: continue
                if measure.axes_2d((lab[s] == j).max(0), sp[1], sp[2])[0] >= 4: n += 1
            r[f"{name}_others"] = n
        rows.append(r); print(r, flush=True)
    return rows

if __name__ == "__main__":
    nii, cache, frac, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
    rows = run(nii, cache, sys.argv[5:], frac)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
