"""Expert baseline for every RIDER patient: manual vs automatic outline, test vs retest.
Writes results/baseline.csv (one row per patient x scan x outline type).
Usage: python3 baseline_all.py <data_dir> [patient ids...]   (no ids = all; appends)"""
import csv, glob, os, sys
import pydicom
from measure_expert import measure

data = sys.argv[1]
root = glob.glob(f"{data}/RIDER-Lung-CT-RTSTRUCTS*/rider_lung_ct")[0]
pids = sys.argv[2:] or sorted(os.listdir(root))
os.makedirs("results", exist_ok=True)
out = "results/baseline.csv"
new = not os.path.exists(out)
with open(out, "a", newline="") as fh:
    w = csv.writer(fh)
    if new:
        w.writerow(["patient", "scan", "outline", "volume_ml", "longest_diameter_mm", "slices"])
    for pid in pids:
        for f in sorted(glob.glob(f"{root}/{pid}/*/*/*.dcm")):
            ds = pydicom.dcmread(f, stop_before_pixels=True)
            if ds.Modality != "SEG":
                continue
            scan = "RETEST" if "RETEST" in ds.SeriesDescription else "TEST"
            for label in ("MANUAL", "AUTOMATIC"):
                try:
                    v, d, s = measure(f, label)
                    w.writerow([pid, scan, label, round(v, 2), round(d, 1), s])
                except StopIteration:
                    pass
        fh.flush()
        print("done", pid, flush=True)
