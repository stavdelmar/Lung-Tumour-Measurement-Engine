"""Turn the RIDER DICOM download into the engine's scan folder.

For every expert-outlined scan in results/cases.json it writes:
  <pid>_<TEST|RETEST>_ct.nii.gz      the CT (HU)
  <pid>_<TEST|RETEST>_expert.nii.gz  the expert outline (for the exam only; the app never sees it)
  <pid>_<TEST|RETEST>_meta.json      series number, slice thickness, date, DICOM image numbers per slice
Resumable: skips scans already done.  Usage: python -m engine.prepare_data DATA_DIR OUT_DIR [max_seconds]
"""
import glob, json, os, sys, time
import numpy as np
import pydicom
import SimpleITK as sitk

from .data import find_ct_dir, load_ct, expert_mask, seg_files

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    data, out = sys.argv[1], sys.argv[2]
    limit = float(sys.argv[3]) if len(sys.argv) > 3 else 1e9
    os.makedirs(out, exist_ok=True)
    cases = json.load(open(f"{HERE}/../results/cases.json"))
    t0 = time.time()
    for pid, scan, seg_uid, ct_uid in cases:
        if os.path.exists(f"{out}/{pid}_{scan}_meta.json"):
            continue
        if time.time() - t0 > limit:
            print("time limit reached; run again to continue"); break
        d = find_ct_dir(data, pid, ct_uid)
        ct = load_ct(d)
        m, _ = expert_mask(seg_files(data, pid)[scan], ct)
        sitk.WriteImage(ct, f"{out}/{pid}_{scan}_ct.nii.gz", useCompression=True)
        mi = sitk.GetImageFromArray(m.astype(np.uint8)); mi.CopyInformation(ct)
        sitk.WriteImage(mi, f"{out}/{pid}_{scan}_expert.nii.gz", useCompression=True)
        files = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(d)
        ds = pydicom.dcmread(files[0], stop_before_pixels=True)
        inst = [int(pydicom.dcmread(f, stop_before_pixels=True).InstanceNumber) for f in files]
        json.dump(dict(patient=pid, scan=scan, series_number=int(ds.SeriesNumber),
                       slice_thickness=float(ds.SliceThickness), study_date=str(ds.StudyDate),
                       series_desc=str(getattr(ds, "SeriesDescription", "")), instance_numbers=inst,
                       spacing=ct.GetSpacing(), size=ct.GetSize()), open(f"{out}/{pid}_{scan}_meta.json", "w"))
        print(pid, scan, ct.GetSize(), round(time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
