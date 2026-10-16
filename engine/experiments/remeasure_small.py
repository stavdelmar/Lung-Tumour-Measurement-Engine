"""Re-measure tumours whose model core is < 16 mm with the size-scaled halo (16 Oct), vs the exam's fixed 4 mm halo.

Usage: python -m engine.experiments.remeasure_small NII_DIR CACHE_DIR EXAM_CSV OUT_CSV pid_scan ...
Also counts, on the same scans, how many OTHER candidates >= 4 mm each outline method reports
(the fixed band can push sub-4 mm specks over the 4 mm reporting line).
"""
import csv, json, sys
import numpy as np
import SimpleITK as sitk
from scipy import ndimage as ndi
from engine import measure, outline
from engine.pipeline import run_scan


def main():
    nii, cache, exam_csv, out = sys.argv[1:5]
    exam = {(r["patient"], r["scan"]): r for r in csv.DictReader(open(exam_csv))}
    rows = []
    for key in sys.argv[5:]:
        pid, scan = key.rsplit("_", 1)
        meta = json.load(open(f"{nii}/{pid}_{scan}_meta.json"))
        ct = sitk.ReadImage(f"{nii}/{pid}_{scan}_ct.nii.gz")
        hu = sitk.GetArrayFromImage(ct); sp = tuple(np.array(ct.GetSpacing())[::-1])
        m = sitk.GetArrayFromImage(sitk.ReadImage(f"{nii}/{pid}_{scan}_expert.nii.gz")) > 0
        nods, labels, lobes, prob, _ = run_scan(f"{nii}/{pid}_{scan}_ct.nii.gz", meta, f"{cache}/{pid}_{scan}.npz")
        z = np.load(f"{cache}/{pid}_{scan}.npz"); core = z["nod"]
        lab, _ = ndi.label(core, np.ones((3, 3, 3)))
        ids, c = np.unique(lab[m & (lab > 0)], return_counts=True)
        cm = lab == ids[c.argmax()]
        d = 2 * (cm.sum() * np.prod(sp) * 3 / (4 * np.pi)) ** (1 / 3)
        hits = [i for i in range(len(nods)) if (labels[m] == i + 1).any()]
        i = max(hits, key=lambda k: (labels[m] == k + 1).sum()); n = nods[i]; pm = labels == i + 1
        # other candidates >= 4 mm: scaled (pipeline) vs fixed 4 mm halo
        fixed = outline.halo(core, hu, sp, 4.0, -750, lobes)
        nf, lf = measure.components(fixed, prob, sp, ct_hu=hu, lobe_map=lobes)
        e = exam[(pid, scan)]
        rows.append(dict(patient=pid, scan=scan, expert_long=float(e["expert_long"]), expert_vol=float(e["expert_vol"]),
                         core_diam_mm=round(d, 1), band_mm=round(float(np.clip(.25 * d, 1, 4)), 2),
                         model_long=float(e["tool_long"]), model_vol=float(e["tool_vol"]),
                         fixed_long=float(e["halo_long"]), fixed_vol=float(e["halo_vol"]), fixed_dice=float(e["halo_dice"]),
                         scaled_long=n["long_axis_mm"], scaled_short=n["short_axis_mm"], scaled_vol=n["volume_mm3"],
                         scaled_dice=round(2 * (pm & m).sum() / (pm.sum() + m.sum()), 3), scaled_type=n["type"],
                         n_cand_scaled=len(nods), n_cand_fixed=len(nf)))
        print(rows[-1], flush=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
