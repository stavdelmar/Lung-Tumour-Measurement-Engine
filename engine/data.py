"""Load a RIDER CT scan and the expert outline on the same voxel grid."""
import glob, os
import numpy as np
import pydicom
import SimpleITK as sitk

def find_ct_dir(data_dir, pid, series_uid):
    for d in glob.glob(f"{data_dir}/RIDER-Lung-CT-Original*/rider_lung_ct/{pid}/*/*"):
        f = glob.glob(d + "/*.dcm")
        if f and pydicom.dcmread(f[0], stop_before_pixels=True).SeriesInstanceUID == series_uid:
            return d
    raise FileNotFoundError(series_uid)

def load_ct(ct_dir):
    r = sitk.ImageSeriesReader()
    r.SetFileNames(r.GetGDCMSeriesFileNames(ct_dir))
    img = r.Execute()
    return img  # HU, z-y-x array via GetArrayFromImage

def seg_files(data_dir, pid):
    out = {}
    for f in glob.glob(f"{data_dir}/RIDER-Lung-CT-RTSTRUCTS*/rider_lung_ct/{pid}/*/*/*.dcm"):
        ds = pydicom.dcmread(f, stop_before_pixels=True)
        if ds.Modality == "SEG":
            out["RETEST" if "RETEST" in ds.SeriesDescription else "TEST"] = f
    return out

def expert_mask(seg_path, ct_img, label="MANUAL"):
    """Rasterise the SEG segment onto the CT grid (z,y,x bool array)."""
    ds = pydicom.dcmread(seg_path)
    seg_no = next(s.SegmentNumber for s in ds.SegmentSequence if s.SegmentAlgorithmType == label)
    frames = ds.pixel_array
    if frames.ndim == 2:
        frames = frames[None]
    nz = ct_img.GetSize()[2]
    zs = np.array([ct_img.TransformIndexToPhysicalPoint((0, 0, k))[2] for k in range(nz)])
    mask = np.zeros((nz, ct_img.GetSize()[1], ct_img.GetSize()[0]), bool)
    for i, fg in enumerate(ds.PerFrameFunctionalGroupsSequence):
        if fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber != seg_no:
            continue
        z = float(fg.PlanePositionSequence[0].ImagePositionPatient[2])
        k = int(np.argmin(np.abs(zs - z)))
        if abs(zs[k] - z) < 0.5:
            mask[k] |= frames[i] > 0
    return mask, ds.ReferencedSeriesSequence[0].SeriesInstanceUID

def load_case(data_dir, pid, scan):
    seg = seg_files(data_dir, pid)[scan]
    uid = pydicom.dcmread(seg, stop_before_pixels=True).ReferencedSeriesSequence[0].SeriesInstanceUID
    ct = load_ct(find_ct_dir(data_dir, pid, uid))
    mask, _ = expert_mask(seg, ct)
    return ct, mask
