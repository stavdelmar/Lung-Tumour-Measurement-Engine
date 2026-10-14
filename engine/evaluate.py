"""Evaluate the classic box method against the expert on RIDER cases.
Usage: python3 evaluate.py <data_dir> <out_csv> <pid:scan> ..."""
import csv, os, sys, time
import numpy as np
import SimpleITK as sitk
from data import load_case
from classic import segment_box_v5, box_from_expert
from metrics import dice, volume_ml, longest_diameter_mm

data, out = sys.argv[1], sys.argv[2]
new = not os.path.exists(out)
with open(out, "a", newline="") as fh:
    w = csv.writer(fh)
    if new:
        w.writerow(["patient", "scan", "dice", "expert_ml", "tool_ml", "expert_mm", "tool_mm", "seconds"])
    for item in sys.argv[3:]:
        pid, scan = item.split(":")
        ct, m = load_case(data, pid, scan)
        a = sitk.GetArrayFromImage(ct)
        sp = ct.GetSpacing()
        z, box = box_from_expert(m)
        t = time.time()
        p = segment_box_v5(ct, a, sp, z, box, key=f'{pid}_{scan}', cache_dir='../../cache')
        secs = time.time() - t
        row = [pid, scan, round(dice(p, m), 3), round(volume_ml(m, sp), 2), round(volume_ml(p, sp), 2),
               round(longest_diameter_mm(m, sp), 1), round(longest_diameter_mm(p, sp), 1), round(secs, 2)]
        w.writerow(row); fh.flush()
        print(*row, flush=True)
