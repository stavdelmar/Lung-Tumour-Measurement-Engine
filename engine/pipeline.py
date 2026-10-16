"""Full AI draft for one scan: lobes -> nodules -> measurements. Used by the API and the evaluation."""
import json, os, time
import numpy as np
import SimpleITK as sitk

from . import detect, measure, outline

ENGINE_VERSION = "0.1.0"


def run_scan(ct_path, meta=None, cache_npz=None, min_long_mm=4.0, patch=None, step=0.5):
    """patch=None = the model's own patch (128x192x192). Smaller patches save memory but MISS nodules
    (tested 15 Oct: a 14 mm tumour went from found to probability 0.0), so do not shrink it.
    Returns (nodules list, label map (z,y,x) int16 with values = index in list + 1, lobes, prob, timings)."""
    t0 = time.time()
    ct = sitk.ReadImage(ct_path)
    hu = sitk.GetArrayFromImage(ct)
    sp = tuple(np.array(ct.GetSpacing())[::-1])
    tim = {}
    if cache_npz and os.path.exists(cache_npz):
        z = np.load(cache_npz)
        lobes, nod, prob = z["lobes"], z["nod"], z["prob"].astype(np.float32)
    else:
        t = time.time(); lobes = detect.lobes(ct_path); tim["lobes_s"] = round(time.time() - t, 1)
        t = time.time(); nod, prob = detect.nodules(ct_path, lobes, patch=patch, step=step)
        tim["nodules_s"] = round(time.time() - t, 1)
        if cache_npz:
            np.savez_compressed(cache_npz, lobes=lobes, nod=nod, prob=prob.astype(np.float16))
    inst = meta.get("instance_numbers") if meta else None
    t = time.time()
    # Outline = model outline + 'halo' (pulls in the faint rim the model leaves out). Chosen from the
    # 59-scan exam (16 Oct): long axis error median 2.8 mm vs 6.0 mm for the bare model, MedSAM 2 10.7 mm.
    # Band per nodule (16 Oct evening): image-driven for cores < 16 mm, 4 mm for larger ones
    # (results/halo_variants_found52.csv: long axis within 2.3 mm 24/52 vs 19/52 fixed, no failures on small tumours).
    if os.environ.get("ENGINE_OUTLINE", "halo") == "halo" and nod.any():
        core = nod
        nod = outline.halo_adaptive(nod, hu, sp, lobes)
    else:
        core = nod
    nodules, labels = measure.components(nod, prob, sp, min_long_mm=min_long_mm, ct_hu=hu,
                                         lobe_map=lobes, instance_numbers=inst)
    # Type is judged on the model's core (the halo rim is faint by design and would make every
    # nodule look 'Part-solid'). The solid component is then measured on the FINAL outline's key slice
    # (Daniel's SOP: long axis of the solid core on the slice where the nodule is measured).
    for i, n in enumerate(nodules):
        c = core & (labels == i + 1)
        if not c.any():
            continue
        n["type"] = measure.measure_nodule(c, hu, sp)["type"]
        n["solid_component_mm"] = None
        if n["type"] == "Part-solid":
            z = n["slice_index"]
            sol = (labels[z] == i + 1) & (hu[z] > measure.SOLID_HU)
            n["solid_component_mm"] = round(measure.axes_2d(sol, sp[1], sp[2])[0], 1) if sol.any() else 0.0
    for n in nodules:
        n["source"] = "ai"
        n["match_to_prior"] = None
    tim["measure_s"] = round(time.time() - t, 1)
    tim["total_s"] = round(time.time() - t0, 1)
    return nodules, labels, lobes, prob, tim
