"""Evaluate every expert-outlined RIDER scan; resumable, stops after a time budget.
Usage: python3 run_all.py <data_dir> <out_csv> <seconds_budget>"""
import csv, glob, os, sys, time
import pydicom, SimpleITK as sitk
from data import load_case
from classic import segment_box_v5, box_from_expert
from metrics import dice, volume_ml, longest_diameter_mm
data, out, budget = sys.argv[1], sys.argv[2], float(sys.argv[3])
start = time.time()
root = glob.glob(f"{data}/RIDER-Lung-CT-RTSTRUCTS*/rider_lung_ct")[0]
cases = []
for pid in sorted(os.listdir(root)):
    for f in glob.glob(f"{root}/{pid}/*/*/*.dcm"):
        ds = pydicom.dcmread(f, stop_before_pixels=True)
        if ds.Modality == "SEG":
            cases.append((pid, "RETEST" if "RETEST" in ds.SeriesDescription else "TEST"))
done = set()
if os.path.exists(out):
    done = {(r["patient"], r["scan"]) for r in csv.DictReader(open(out))}
todo = [c for c in sorted(cases) if c not in done]
print(f"{len(cases)} cases, {len(done)} done, {len(todo)} to go", flush=True)
new = not os.path.exists(out)
with open(out, "a", newline="") as fh:
    w = csv.writer(fh)
    if new:
        w.writerow(["patient", "scan", "dice", "expert_ml", "tool_ml", "expert_mm", "tool_mm", "seconds"])
    for pid, scan in todo:
        if time.time() - start > budget:
            break
        ct, m = load_case(data, pid, scan)
        a = sitk.GetArrayFromImage(ct); sp = ct.GetSpacing()
        z, box = box_from_expert(m)
        t = time.time()
        p = segment_box_v5(ct, a, sp, z, box, key=f"{pid}_{scan}", cache_dir="../../cache")
        secs = time.time() - t
        w.writerow([pid, scan, round(dice(p, m), 3), round(volume_ml(m, sp), 2), round(volume_ml(p, sp), 2),
                    round(longest_diameter_mm(m, sp), 1), round(longest_diameter_mm(p, sp), 1), round(secs, 2)])
        fh.flush(); print(pid, scan, round(dice(p, m), 3), flush=True)
