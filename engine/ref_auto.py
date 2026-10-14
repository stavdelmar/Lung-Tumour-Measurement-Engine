"""Reference: Dice of the dataset's own in-house auto-segmentation vs the expert."""
import csv, glob, os, sys
import pydicom, SimpleITK as sitk
from data import seg_files, find_ct_dir, load_ct, expert_mask
from metrics import dice
data, out = sys.argv[1], sys.argv[2]
root = glob.glob(f"{data}/RIDER-Lung-CT-RTSTRUCTS*/rider_lung_ct")[0]
done = {(r["patient"], r["scan"]) for r in csv.DictReader(open(out))} if os.path.exists(out) else set()
with open(out, "a", newline="") as fh:
    w = csv.writer(fh)
    if not done: w.writerow(["patient", "scan", "dice_auto_vs_expert"])
    for pid in sorted(os.listdir(root)):
        for scan, f in seg_files(data, pid).items():
            if (pid, scan) in done: continue
            uid = pydicom.dcmread(f, stop_before_pixels=True).ReferencedSeriesSequence[0].SeriesInstanceUID
            ct = load_ct(find_ct_dir(data, pid, uid))
            m, _ = expert_mask(f, ct, "MANUAL")
            try:
                a, _ = expert_mask(f, ct, "AUTOMATIC"); d = round(dice(a, m), 3)
            except StopIteration:
                d = ""
            w.writerow([pid, scan, d]); fh.flush()
