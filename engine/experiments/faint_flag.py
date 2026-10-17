"""How often would the 'faint rim' warning fire on ALL candidates (not only the expert tumour)?
Usage: python -m engine.experiments.faint_flag NII CACHE OUT_CSV key ..."""
import sys, csv, os
import numpy as np, SimpleITK as sitk
from engine import outline, measure

def main():
    nii, cache, out = sys.argv[1:4]
    rows = list(csv.DictReader(open(out))) if os.path.exists(out) else []
    done = {r["key"] for r in rows}
    for key in sys.argv[4:]:
        if key in done: continue
        ct = sitk.ReadImage(f"{nii}/{key}_ct.nii.gz"); hu = sitk.GetArrayFromImage(ct); sp = tuple(np.array(ct.GetSpacing())[::-1])
        z = np.load(f"{cache}/{key}.npz"); core, lobes, prob = z["nod"], z["lobes"], z["prob"].astype(np.float32)
        g, blab = outline.faint_rim_growth(core, hu, sp, lobes)
        dflt = outline.halo_per_nodule(core, hu, sp, lobes)
        nods, labels = measure.components(dflt, prob, sp, ct_hu=hu, lobe_map=lobes)
        m = sitk.GetArrayFromImage(sitk.ReadImage(f"{nii}/{key}_expert.nii.gz")) > 0 if os.path.exists(f"{nii}/{key}_expert.nii.gz") else None
        for i, n in enumerate(nods):
            ids = np.unique(blab[(labels == i + 1) & (blab > 0)])
            gr = max([g[int(j)] for j in ids], default=0.0)
            rows.append(dict(key=key, nodule=n["nodule_id"], long_mm=n["long_axis_mm"], growth_mm=gr,
                             confidence=n["confidence"], expert=bool(m is not None and (m & (labels == i + 1)).any())))
        print(key, len(nods), [r["growth_mm"] for r in rows if r["key"] == key], flush=True)
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

if __name__ == "__main__":
    main()
