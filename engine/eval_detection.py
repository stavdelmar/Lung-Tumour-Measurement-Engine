"""Exam for nodule FINDING, measuring and MATCHING on RIDER (test + retest, 15 minutes apart).

What RIDER can tell us, and what it can't:
- Each scan has ONE expert-outlined tumour. So we can check: did the tool find it? how close are its
  long/short axis and volume to the expert outline (measured the same way)?
- Other nodules in the scan are NOT marked. So we cannot count false alarms against ground truth.
  Proxy: the two scans are 15 minutes apart, so a real nodule should be found in BOTH. A candidate seen
  in only one of the two is suspicious (or a miss in the other). We report that "repeatability".
- Matching: the expert tumour in TEST and RETEST is the same lesion -> the pair must be matched.

Usage: python -m engine.eval_detection NII_DIR CACHE_DIR OUT_CSV [patient ...]
NII_DIR holds <pid>_<scan>_ct.nii.gz, _expert.nii.gz, _meta.json (made by to_nii.py).
"""
import json, os, sys, time
import numpy as np
import SimpleITK as sitk

from . import measure, match, outline
from .pipeline import run_scan


# "Too long because of a vessel tail" = long axis > expert + 2.3 mm (expert repeat noise) AND spur_mm > 2.
TAIL_RULE = dict(over_mm=2.3, spur_mm=2.0)

# Outline refiners compared on the found tumour: name -> fn(component_mask, hu, spacing, lobes) -> mask
REFINERS = {"halo": lambda c, hu, sp, lobes: outline.halo(c, hu, sp, 4.0, -750, lobes)}


def expert_measure(nii_dir, pid, scan, lobes):
    ct = sitk.ReadImage(f"{nii_dir}/{pid}_{scan}_ct.nii.gz")
    m = sitk.GetArrayFromImage(sitk.ReadImage(f"{nii_dir}/{pid}_{scan}_expert.nii.gz")) > 0
    meta = json.load(open(f"{nii_dir}/{pid}_{scan}_meta.json"))
    sp = tuple(np.array(ct.GetSpacing())[::-1])
    e = measure.measure_nodule(m, sitk.GetArrayFromImage(ct), sp, lobes, meta["instance_numbers"])
    return e, m, ct, meta


def eval_scan(nii_dir, cache_dir, pid, scan):
    meta = json.load(open(f"{nii_dir}/{pid}_{scan}_meta.json"))
    nods, labels, lobes, prob, tim = run_scan(f"{nii_dir}/{pid}_{scan}_ct.nii.gz", meta,
                                              cache_npz=f"{cache_dir}/{pid}_{scan}.npz")
    e, m, ct, _ = expert_measure(nii_dir, pid, scan, lobes)
    hits = [i for i in range(len(nods)) if (labels[m] == i + 1).any()]
    row = dict(patient=pid, scan=scan, n_candidates=len(nods), found=bool(hits),
               expert_long=e["long_axis_mm"], expert_short=e["short_axis_mm"], expert_vol=e["volume_mm3"],
               expert_lobe=e["lobe"], expert_type=e["type"], expert_slice=e["slice_number"])
    if hits:
        i = max(hits, key=lambda k: (labels[m] == k + 1).sum())
        n = nods[i]
        pm = labels == i + 1
        row.update(tool_id=n["nodule_id"], tool_long=n["long_axis_mm"], tool_short=n["short_axis_mm"],
                   tool_vol=n["volume_mm3"], tool_lobe=n["lobe"], tool_type=n["type"], tool_slice=n["slice_number"],
                   confidence=n["confidence"],
                   dice=round(2 * (pm & m).sum() / (pm.sum() + m.sum()), 3))
        hu = sitk.GetArrayFromImage(ct)
        sp = tuple(np.array(ct.GetSpacing())[::-1])
        sl = tuple(slice(max(a.min() - 5, 0), a.max() + 6) for a in np.nonzero(pm | m))
        row.update(tool_spur_mm=measure.spur_mm(pm[sl], sp), expert_spur_mm=measure.spur_mm(m[sl], sp))
        for name, fn in REFINERS.items():
            try:
                t = time.time()
                rm = fn(pm, hu, sp, lobes)
                r = measure.measure_nodule(rm, hu, sp)
                slr = tuple(slice(max(a.min() - 5, 0), a.max() + 6) for a in np.nonzero(rm | m))
                row[f"{name}_spur_mm"] = measure.spur_mm(rm[slr], sp)
                row.update({f"{name}_dice": round(2 * (rm & m).sum() / (rm.sum() + m.sum()), 3),
                            f"{name}_long": r["long_axis_mm"], f"{name}_short": r["short_axis_mm"],
                            f"{name}_vol": r["volume_mm3"], f"{name}_s": round(time.time() - t, 1)})
            except Exception as ex:
                row[f"{name}_error"] = str(ex)[:200]
    else:
        # how strong was the model's signal inside the expert tumour?
        row.update(max_prob_in_tumour=round(float(prob[m].max()), 3))
    row.update(tim)
    return row, nods, lobes, ct


def main():
    nii_dir, cache_dir, out_csv = sys.argv[1:4]
    os.makedirs(cache_dir, exist_ok=True)
    pids = sys.argv[4:] or sorted({f.split("_")[0] for f in os.listdir(nii_dir) if f.endswith("_meta.json")})
    import pandas as pd
    rows, pairs = [], []
    for pid in pids:
        per = {}
        for scan in ("TEST", "RETEST"):
            if not os.path.exists(f"{nii_dir}/{pid}_{scan}_meta.json"):
                continue
            t = time.time()
            row, nods, lobes, ct = eval_scan(nii_dir, cache_dir, pid, scan)
            rows.append(row); per[scan] = (row, nods, lobes, ct)
            print(pid, scan, {k: row.get(k) for k in ("found", "n_candidates", "expert_long", "tool_long", "dice")},
                  f"{time.time() - t:.0f}s", flush=True)
        if len(per) == 2:  # matching RETEST (current) -> TEST (prior)
            (rc, nc, lc, cc), (rp, np_, lp, cp) = per["RETEST"], per["TEST"]
            t = time.time()
            tx, metric = match.register(cc, cp, lc, lp)
            res = match.match(nc, np_, tx, cc, cp)
            ok = None
            if rc.get("tool_id") and rp.get("tool_id"):
                ok = {"current": rc["tool_id"], "prior": rp["tool_id"]} in [
                    {"current": p["current"], "prior": p["prior"]} for p in res["pairs"]]
            # where does the expert tumour centre land after registration? (registration error)
            e_c = np.array(match.vox_to_phys(cc, measure_center(nii_dir, pid, "RETEST")))
            e_p = np.array(match.vox_to_phys(cp, measure_center(nii_dir, pid, "TEST")))
            reg_err = float(np.linalg.norm(np.array(tx.TransformPoint(tuple(e_c))) - e_p))
            pairs.append(dict(patient=pid, tumour_matched=ok, registration_error_mm=round(reg_err, 1),
                              n_current=len(nc), n_prior=len(np_), n_pairs=len(res["pairs"]),
                              unpaired_current=len(res["new_in_current"]), unpaired_prior=len(res["not_found_in_current"]),
                              match_s=round(time.time() - t, 1)))
            print("  match:", pairs[-1], flush=True)
        pd.DataFrame(rows).to_csv(out_csv, index=False)
        pd.DataFrame(pairs).to_csv(out_csv.replace(".csv", "_matching.csv"), index=False)


def measure_center(nii_dir, pid, scan):
    m = sitk.GetArrayFromImage(sitk.ReadImage(f"{nii_dir}/{pid}_{scan}_expert.nii.gz")) > 0
    return [float(np.mean(i)) for i in np.nonzero(m)]


if __name__ == "__main__":
    main()
