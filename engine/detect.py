"""Nodule finding + lobes, with two free, open models (TotalSegmentator family, nnU-Net).

Step 1  lobes: TotalSegmentator 'total' 3 mm model (5 lobe labels used).
Step 2  nodules: TotalSegmentator 'lung_nodules' model (nnU-Net ResEnc, trained on 1352 CTs by
        BlueMind AI, no licence needed), run on the lung crop at the scan's own resolution.

Both models are called directly through nnU-Net in ONE process (no worker processes): the free CPU
machines we may use have 6-16 GB RAM, and TotalSegmentator's default runner needs more.
Everything returns arrays on the original CT grid (z, y, x), so measurements stay in CT space.
"""
import os, tempfile
import numpy as np
import SimpleITK as sitk
import torch

TS_HOME = os.path.expanduser(os.environ.get("TOTALSEG_HOME_DIR", "~/.totalsegmentator"))
LOBE_MODEL = f"{TS_HOME}/nnunet/results/Dataset297_TotalSegmentator_total_3mm_1559subj/nnUNetTrainer_4000epochs_NoMirroring__nnUNetPlans__3d_fullres"
NODULE_MODEL = f"{TS_HOME}/nnunet/results/Dataset913_lung_nodules/nnUNetTrainer_MOSAIC_1k_QuarterLR_NoMirroring__nnUNetPlans__3d_fullres"
# total-model label -> our lobe code index
LOBE_LABELS = {12: 1, 13: 2, 14: 3, 10: 4, 11: 5}
LOBE_CODE = {1: "RUL", 2: "RML", 3: "RLL", 4: "LUL", 5: "LLL"}

_predictors = {}


def _threads():
    torch.set_num_threads(int(os.environ.get("ENGINE_THREADS", os.cpu_count() or 2)))


def _device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _predictor(model_dir, patch=None, step=0.5):
    key = (model_dir, patch, step)
    if key not in _predictors:
        import totalsegmentator.nnunet  # noqa: F401  registers TotalSegmentator's trainer classes
        from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
        dev = _device()
        p = nnUNetPredictor(tile_step_size=step, use_gaussian=True, use_mirroring=False,
                            perform_everything_on_device=dev.type == "cuda", device=dev, allow_tqdm=False)
        folds = ("0",) if os.path.isdir(f"{model_dir}/fold_0") else ("all",)
        p.initialize_from_trained_model_folder(model_dir, use_folds=folds)
        if patch:
            p.configuration_manager.configuration["patch_size"] = list(patch)
        _predictors[key] = p
    return _predictors[key]


def _run(model_dir, img, patch=None, step=0.5, prob_label=None):
    """Run an nnU-Net model on a SimpleITK image. Returns (label array, prob array or None) on img's grid."""
    _threads()
    pred = _predictor(model_dir, patch, step)
    rw = pred.plans_manager.image_reader_writer_class()  # same reader as in training (reorients)
    with tempfile.TemporaryDirectory() as d:
        sitk.WriteImage(img, f"{d}/x_0000.nii.gz")
        arr, props = rw.read_images([f"{d}/x_0000.nii.gz"])
        with torch.inference_mode():
            out = pred.predict_single_npy_array(arr, props, None, None, prob_label is not None)
        seg, prob = out if prob_label is not None else (out, None)
        rw.write_seg(seg.astype(np.uint8), f"{d}/seg.nii.gz", props)
        seg = sitk.GetArrayFromImage(sitk.ReadImage(f"{d}/seg.nii.gz"))
        if prob is not None:
            rw.write_seg(np.round(prob[prob_label] * 1000).astype(np.int16), f"{d}/p.nii.gz", props)
            prob = sitk.GetArrayFromImage(sitk.ReadImage(f"{d}/p.nii.gz")).astype(np.float32) / 1000
    return seg, prob


def lobes(ct):
    """Lobe label map (0 = outside, 1..5 = RUL, RML, RLL, LUL, LLL) on the CT grid. ct: path or image."""
    ref = sitk.ReadImage(ct) if isinstance(ct, str) else ct
    sp3 = [3.0, 3.0, 3.0]
    size3 = [int(round(s * p / 3.0)) for s, p in zip(ref.GetSize(), ref.GetSpacing())]
    small = sitk.Resample(ref, size3, sitk.Transform(), sitk.sitkLinear, ref.GetOrigin(), sp3,
                          ref.GetDirection(), -1024, sitk.sitkInt16)
    seg, _ = _run(LOBE_MODEL, small)
    lab3 = np.zeros(seg.shape, np.uint8)
    for k, v in LOBE_LABELS.items():
        lab3[seg == k] = v
    li = sitk.GetImageFromArray(lab3); li.CopyInformation(small)
    return sitk.GetArrayFromImage(sitk.Resample(li, ref, sitk.Transform(), sitk.sitkNearestNeighbor, 0, sitk.sitkUInt8))


def lung_crop(lobe_map, spacing_zyx, margin_mm=10):
    zz, yy, xx = np.nonzero(lobe_map)
    mg = np.ceil(margin_mm / np.asarray(spacing_zyx)).astype(int)
    lo = np.maximum([zz.min(), yy.min(), xx.min()] - mg, 0)
    hi = np.minimum(np.array([zz.max(), yy.max(), xx.max()]) + mg + 1, lobe_map.shape)
    return lo, hi


def nodules(ct, lobe_map, patch=None, step=0.5):
    """Nodule mask (bool) and nodule probability (float16) on the full CT grid."""
    ref = sitk.ReadImage(ct) if isinstance(ct, str) else ct
    sp = np.array(ref.GetSpacing())[::-1]
    m = np.zeros(lobe_map.shape, bool)
    p = np.zeros(lobe_map.shape, np.float16)
    # One lung at a time keeps peak memory under ~5 GB on CPU (both at once needs more).
    parts = [np.isin(lobe_map, (1, 2, 3)), np.isin(lobe_map, (4, 5))]
    if os.environ.get("ENGINE_SPLIT_LUNGS", "1") == "0" or not all(x.any() for x in parts):
        parts = [lobe_map > 0]
    for part in parts:
        lo, hi = lung_crop(part, sp, margin_mm=15)
        crop = ref[int(lo[2]):int(hi[2]), int(lo[1]):int(hi[1]), int(lo[0]):int(hi[0])]
        seg, prob = _run(NODULE_MODEL, crop, patch, step, prob_label=2)
        sl = tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))
        m[sl] |= seg == 2
        p[sl] = np.maximum(p[sl], prob.astype(np.float16))
        del seg, prob
    return m, p
