"""Measure the expert (manual) tumour outline for one RIDER patient.

Reads the DICOM SEG files and reports, for the TEST and RETEST scans:
volume (mL), longest in-slice diameter (mm) and number of slices the tumour spans.
Usage: python3 measure_expert.py <data_dir> <patient_id>
"""
import glob, sys
import numpy as np
import pydicom

def longest_diameter_mm(mask2d, spacing):
    ys, xs = np.nonzero(mask2d)
    if len(xs) < 2:
        return 0.0
    pts = np.stack([ys * spacing[0], xs * spacing[1]], axis=1)
    if len(pts) > 3000:  # keep it fast: sample points
        pts = pts[np.random.default_rng(0).choice(len(pts), 3000, replace=False)]
    d = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))
    return float(d.max())

def measure(seg_path, label="MANUAL"):
    ds = pydicom.dcmread(seg_path)
    seg_no = next(s.SegmentNumber for s in ds.SegmentSequence if s.SegmentAlgorithmType == label)
    pm = ds.SharedFunctionalGroupsSequence[0].PixelMeasuresSequence[0]
    spacing = [float(v) for v in pm.PixelSpacing]
    thick = float(pm.get("SpacingBetweenSlices") or pm.SliceThickness)
    frames = ds.pixel_array
    if frames.ndim == 2:
        frames = frames[None]
    voxels, slices, best = 0, 0, 0.0
    for i, fg in enumerate(ds.PerFrameFunctionalGroupsSequence):
        if fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber != seg_no:
            continue
        m = frames[i] > 0
        n = int(m.sum())
        if n:
            voxels += n; slices += 1
            best = max(best, longest_diameter_mm(m, spacing))
    vol_ml = voxels * spacing[0] * spacing[1] * thick / 1000
    return vol_ml, best, slices

if __name__ == "__main__":
    data, pid = sys.argv[1], sys.argv[2]
    for f in sorted(glob.glob(f"{data}/RIDER-Lung-CT-RTSTRUCTS*/rider_lung_ct/{pid}/*/*/*.dcm")):
        ds = pydicom.dcmread(f, stop_before_pixels=True)
        if ds.Modality != "SEG":
            continue
        which = "RETEST" if "RETEST" in ds.SeriesDescription else "TEST"
        v, d, s = measure(f)
        print(f"{pid} {which:6s}  volume {v:6.2f} mL   longest diameter {d:5.1f} mm   spans {s} slices")
