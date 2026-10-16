"""Small nodules have no expert outline in RIDER, so use repeatability instead: the TEST and RETEST scans
are 15 minutes apart, so the same small nodule should measure the same in both. For each outline variant,
match candidates retest -> test (the engine's own matching) and report the size difference of paired
nodules < 16 mm. Smaller difference = steadier outline. Reference: expert test-retest noise 2.3 mm / 17%.

Usage: python -m engine.experiments.small_repeat NII_DIR CACHE_DIR OUT_CSV pid ...
"""
import sys, csv
import numpy as np, SimpleITK as sitk
from engine import measure, outline, match

VARIANTS = {"fixed": lambda c, hu, sp, lb: outline.halo(c, hu, sp, 4.0, -750, lb),
            "scaled": lambda c, hu, sp, lb: outline.halo_per_nodule(c, hu, sp, lb),
            "adaptive": lambda c, hu, sp, lb: outline.halo_adaptive(c, hu, sp, lb, full_band_core_mm=1e9, speck_core_mm=0),
            "hybrid": lambda c, hu, sp, lb: outline.halo_adaptive(c, hu, sp, lb)}


def load(nii, cache, pid, scan):
    ct = sitk.ReadImage(f"{nii}/{pid}_{scan}_ct.nii.gz")
    z = np.load(f"{cache}/{pid}_{scan}.npz")
    return ct, sitk.GetArrayFromImage(ct), tuple(np.array(ct.GetSpacing())[::-1]), z["nod"], z["lobes"], z["prob"].astype(np.float32)


def main():
    import os
    nii, cache, out = sys.argv[1:4]
    rows = list(csv.DictReader(open(out))) if os.path.exists(out) else []  # append (run one patient per process: memory)
    for pid in sys.argv[4:]:
        if any(r["patient"] == pid for r in rows):
            continue
        try:
            T = load(nii, cache, pid, "TEST"); R = load(nii, cache, pid, "RETEST")
        except Exception as ex:
            print(pid, "skip", ex); continue
        tx, _ = match.register(R[0], T[0], R[4], T[4])
        for v, fn in VARIANTS.items():
            nods = {}
            for name, (ct, hu, sp, core, lobes, prob) in (("T", T), ("R", R)):
                nods[name], _ = measure.components(fn(core, hu, sp, lobes), prob, sp, ct_hu=hu, lobe_map=lobes)
            res = match.match(nods["R"], nods["T"], tx, R[0], T[0])
            bt = {n["nodule_id"]: n for n in nods["T"]}; br = {n["nodule_id"]: n for n in nods["R"]}
            for p in res["pairs"]:
                a, b = br[p["current"]], bt[p["prior"]]
                if max(a["long_axis_mm"], b["long_axis_mm"]) >= 16:
                    continue
                rows.append(dict(patient=pid, variant=v, long_t=b["long_axis_mm"], long_r=a["long_axis_mm"],
                                 vol_t=b["volume_mm3"], vol_r=a["volume_mm3"],
                                 d_long=round(abs(a["long_axis_mm"] - b["long_axis_mm"]), 1),
                                 d_vol_pct=round(100 * abs(a["volume_mm3"] - b["volume_mm3"]) / (0.5 * (a["volume_mm3"] + b["volume_mm3"])))))
            n = [r for r in rows if r["patient"] == pid and r["variant"] == v]
            print(pid, v, len(n), "pairs <16mm", flush=True)
        if not any(r["patient"] == pid for r in rows):
            rows.append(dict(patient=pid, variant="none", long_t="", long_r="", vol_t="", vol_r="", d_long="", d_vol_pct=""))
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
