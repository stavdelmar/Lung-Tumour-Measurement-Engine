"""Match nodules between a follow-up scan and its prior.

1. Line up the two scans: affine registration of the lungs (SimpleITK, Mattes mutual information,
   lungs only, 4 mm then 2 mm), started from the lung-mask centres. This absorbs breathing/position
   shifts, so slice numbers no longer need to agree.
2. Move each prior nodule centre into the follow-up scan, then pair nodules with the Hungarian
   method on centre distance. A pair is accepted only if the distance is below
   max(10 mm, 0.75 x the larger long axis).
Unpaired follow-up nodules are reported as 'new', unpaired prior ones as 'not found'.
"""
import numpy as np
import SimpleITK as sitk
from scipy.optimize import linear_sum_assignment


def register(fixed_ct, moving_ct, fixed_lungs, moving_lungs):
    """Returns a transform mapping FIXED physical points -> MOVING physical points."""
    f = sitk.Cast(fixed_ct, sitk.sitkFloat32)
    m = sitk.Cast(moving_ct, sitk.sitkFloat32)
    fl = sitk.GetImageFromArray((fixed_lungs > 0).astype(np.uint8)); fl.CopyInformation(fixed_ct)
    ml = sitk.GetImageFromArray((moving_lungs > 0).astype(np.uint8)); ml.CopyInformation(moving_ct)
    init = sitk.CenteredTransformInitializer(fl, ml, sitk.AffineTransform(3),
                                             sitk.CenteredTransformInitializerFilter.MOMENTS)
    fmask = sitk.BinaryDilate(fl, [3, 3, 3])
    R = sitk.ImageRegistrationMethod()
    R.SetMetricAsMattesMutualInformation(32)
    R.SetMetricFixedMask(fmask)
    R.SetMetricSamplingStrategy(R.RANDOM)
    R.SetMetricSamplingPercentage(0.05, seed=1)
    R.SetInterpolator(sitk.sitkLinear)
    R.SetOptimizerAsRegularStepGradientDescent(1.0, 1e-4, 150, relaxationFactor=0.6)
    R.SetOptimizerScalesFromPhysicalShift()
    R.SetShrinkFactorsPerLevel([4, 2])
    R.SetSmoothingSigmasPerLevel([2, 1])
    R.SetInitialTransform(init, inPlace=False)
    tx = R.Execute(f, m)
    return tx, R.GetMetricValue()


def vox_to_phys(img, zyx):
    return np.array(img.TransformContinuousIndexToPhysicalPoint([float(zyx[2]), float(zyx[1]), float(zyx[0])]))


def phys_to_vox(img, p):
    x, y, z = img.TransformPhysicalPointToContinuousIndex([float(v) for v in p])
    return [z, y, x]


def map_point(tx, fixed_img, moving_img, zyx_fixed):
    """A voxel in the fixed (current) scan -> the matching voxel in the moving (prior) scan."""
    return phys_to_vox(moving_img, tx.TransformPoint(tuple(vox_to_phys(fixed_img, zyx_fixed))))


def match(cur_nodules, prior_nodules, tx, cur_img, prior_img, min_gate_mm=10.0):
    inv = tx.GetInverse()  # prior physical -> current physical
    cur_p = np.array([vox_to_phys(cur_img, n["center_voxel"]) for n in cur_nodules]).reshape(-1, 3)
    pri_p = np.array([inv.TransformPoint(tuple(vox_to_phys(prior_img, n["center_voxel"])))
                      for n in prior_nodules]).reshape(-1, 3)
    pairs, used_c, used_p = [], set(), set()
    if len(cur_p) and len(pri_p):
        d = np.sqrt(((cur_p[:, None] - pri_p[None]) ** 2).sum(-1))
        r, c = linear_sum_assignment(d)
        for i, j in zip(r, c):
            gate = max(min_gate_mm, 0.75 * max(cur_nodules[i]["long_axis_mm"], prior_nodules[j]["long_axis_mm"]))
            if d[i, j] <= gate:
                pairs.append(dict(current=cur_nodules[i]["nodule_id"], prior=prior_nodules[j]["nodule_id"],
                                  distance_mm=round(float(d[i, j]), 1)))
                used_c.add(i); used_p.add(j)
    new = [n["nodule_id"] for i, n in enumerate(cur_nodules) if i not in used_c]
    gone = [n["nodule_id"] for j, n in enumerate(prior_nodules) if j not in used_p]
    return dict(pairs=pairs, new_in_current=new, not_found_in_current=gone)
