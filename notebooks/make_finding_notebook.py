"""Builds notebooks/nodule_finding_exam.ipynb with the engine code embedded (repo may be private)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ENG = os.path.join(HERE, "..", "engine")
cases = json.load(open(os.path.join(HERE, "..", "results", "cases.json")))


def md(s):
    return {"cell_type": "markdown", "metadata": {}, "source": s}


def code(s):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s}


cells = [md("""# Nodule finding exam (GPU) — find, measure, match on RIDER

**What this does:** runs the engine's nodule finder (free TotalSegmentator *lung_nodules* model + lobes) on all
59 expert-outlined RIDER scans, measures each nodule the way Daniel does (long + perpendicular axis on the
largest slice, volume from the outline), pairs nodules between the test and retest scan, and checks:
1. was the expert-outlined tumour found? 2. how close are the measurements? 3. was the tumour paired correctly?
4. how many other candidates appear, and are they seen in both scans (15 min apart)?

**How to run:** `Runtime → Change runtime type → T4 GPU`, then `Runtime → Run all` (≈ 30–45 min, mostly downloads).
At the end two files download: `finding_results.zip` (CSVs) and `engine_cache.zip` (AI masks, so the free server
doesn't need to recompute). *Research use only. Public, de-identified data.*"""),
         code("""N_CASES = 59   # use e.g. 6 for a quick first run
import os; os.environ["ENGINE_SPLIT_LUNGS"] = "0"   # GPU has the memory to see both lungs at once
import torch; print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NONE - switch to T4 GPU!")
!pip -q install totalsegmentator pydicom SimpleITK scikit-image pandas
!totalseg_download_weights -t lung_nodules > /dev/null && totalseg_download_weights -t total_fast > /dev/null && echo weights ok""")]

cells.append(md("## 1. Engine code (same files as `engine/` in the repo)"))
cells.append(code("!mkdir -p /content/engine /content/cache"))
for f in ["__init__.py", "detect.py", "measure.py", "match.py", "outline.py", "pipeline.py", "eval_detection.py"]:
    cells.append(code(f"%%writefile /content/engine/{f}\n" + open(os.path.join(ENG, f)).read()))

cells += [md("## 2. Download the scans + expert outlines from TCIA and convert them"),
          code("cases = " + json.dumps(cases) + "[:N_CASES]\n" + r'''
import os, io, zipfile, requests, glob, json, concurrent.futures as cf
import numpy as np, pydicom, SimpleITK as sitk
API = "https://services.cancerimagingarchive.net/nbia-api/services/v1/getImage?SeriesInstanceUID="
DATA, NII = "/content/rider", "/content/nii"
os.makedirs(NII, exist_ok=True)

def fetch(uid):
    out = f"{DATA}/{uid}"
    if os.path.isdir(out) and os.listdir(out): return uid, "cached"
    for _ in range(4):
        try:
            r = requests.get(API + uid, timeout=600); r.raise_for_status()
            os.makedirs(out, exist_ok=True); zipfile.ZipFile(io.BytesIO(r.content)).extractall(out); return uid, "ok"
        except Exception as e: err = e
    return uid, f"FAILED {err}"

uids = sorted({c[2] for c in cases} | {c[3] for c in cases})
with cf.ThreadPoolExecutor(6) as ex:
    for i, (u, st) in enumerate(ex.map(fetch, uids), 1):
        if st != "cached": print(i, len(uids), st)

def expert_mask(seg_uid, ct):
    ds = pydicom.dcmread(glob.glob(f"{DATA}/{seg_uid}/*.dcm")[0])
    no = next(s.SegmentNumber for s in ds.SegmentSequence if s.SegmentAlgorithmType == "MANUAL")
    fr = ds.pixel_array; fr = fr[None] if fr.ndim == 2 else fr
    nz = ct.GetSize()[2]; zs = np.array([ct.TransformIndexToPhysicalPoint((0, 0, k))[2] for k in range(nz)])
    m = np.zeros((nz, ct.GetSize()[1], ct.GetSize()[0]), bool)
    for i, fg in enumerate(ds.PerFrameFunctionalGroupsSequence):
        if fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber != no: continue
        z = float(fg.PlanePositionSequence[0].ImagePositionPatient[2]); k = int(np.argmin(np.abs(zs - z)))
        if abs(zs[k] - z) < 0.5: m[k] |= fr[i] > 0
    return m

for pid, scan, seg_uid, ct_uid in cases:
    if os.path.exists(f"{NII}/{pid}_{scan}_meta.json"): continue
    d = f"{DATA}/{ct_uid}"; files = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(d)
    r = sitk.ImageSeriesReader(); r.SetFileNames(files); ct = r.Execute()
    m = expert_mask(seg_uid, ct)
    sitk.WriteImage(ct, f"{NII}/{pid}_{scan}_ct.nii.gz", useCompression=True)
    mi = sitk.GetImageFromArray(m.astype(np.uint8)); mi.CopyInformation(ct)
    sitk.WriteImage(mi, f"{NII}/{pid}_{scan}_expert.nii.gz", useCompression=True)
    ds = pydicom.dcmread(files[0], stop_before_pixels=True)
    inst = [int(pydicom.dcmread(f, stop_before_pixels=True).InstanceNumber) for f in files]
    json.dump(dict(patient=pid, scan=scan, series_number=int(ds.SeriesNumber), slice_thickness=float(ds.SliceThickness),
                   study_date=str(ds.StudyDate), instance_numbers=inst, spacing=ct.GetSpacing(), size=ct.GetSize()),
              open(f"{NII}/{pid}_{scan}_meta.json", "w"))
print("converted:", len(glob.glob(f"{NII}/*_meta.json")))'''),
          md("## 3. MedSAM 2 (tested as an outline refiner on top of the detection)"),
          code('# MedSAM 2 as an outline refiner: box from the DETECTED nodule (enlarged), on its largest slice\n%cd /content\n!git clone -q --depth 1 https://github.com/bowang-lab/MedSAM2.git\n%cd /content/MedSAM2\n!SAM2_BUILD_CUDA=0 pip install -q --no-deps -e . && pip install -q hydra-core iopath\n!mkdir -p checkpoints && wget -q -nc -P checkpoints https://huggingface.co/wanglab/MedSAM2/resolve/main/MedSAM2_CTLesion.pt\n%cd /content\nimport sys, numpy as np, torch\nsys.path.insert(0, "/content/MedSAM2")\nfrom PIL import Image\nfrom skimage import measure as skm\nfrom sam2.build_sam import build_sam2_video_predictor_npz\nWINDOW = (-1350, 150)\nAMP = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16\nMEAN = torch.tensor((0.485, 0.456, 0.406))[:, None, None].cuda(); STD = torch.tensor((0.229, 0.224, 0.225))[:, None, None].cuda()\nPRED = build_sam2_video_predictor_npz("configs/sam2.1_hiera_t512.yaml", "/content/MedSAM2/checkpoints/MedSAM2_CTLesion.pt")\n\ndef to_frames(vol_u8, size=512):\n    out = np.zeros((len(vol_u8), 3, size, size), np.float32)\n    for i, s in enumerate(vol_u8):\n        out[i] = np.array(Image.fromarray(s).convert("RGB").resize((size, size))).transpose(2, 0, 1)\n    return (torch.from_numpy(out / 255.0).cuda() - MEAN) / STD\n\ndef medsam2_box(ct_arr, z, box, half=60):\n    z0, z1 = max(0, z - half), min(len(ct_arr), z + half + 1)\n    sub = np.clip(ct_arr[z0:z1], *WINDOW).astype(np.float32)\n    sub = np.uint8((sub - sub.min()) / max(1e-6, sub.max() - sub.min()) * 255)\n    H, W = sub.shape[1:]; y0, y1, x0, x1 = box\n    seg = np.zeros(sub.shape, np.uint8); frames = to_frames(sub)\n    with torch.inference_mode(), torch.autocast("cuda", dtype=AMP):\n        for rev in (False, True):\n            st = PRED.init_state(frames, H, W)\n            PRED.add_new_points_or_box(inference_state=st, frame_idx=z - z0, obj_id=1, box=np.array([x0, y0, x1 - 1, y1 - 1]))\n            for fi, _, lg in PRED.propagate_in_video(st, reverse=rev):\n                seg[fi, (lg[0] > 0.0).cpu().numpy()[0]] = 1\n            PRED.reset_state(st)\n    out = np.zeros(ct_arr.shape, bool)\n    if seg.any():\n        lab = skm.label(seg); out[z0:z1] = lab == np.argmax(np.bincount(lab.flat)[1:]) + 1\n    return out\n\ndef medsam2_refiner(c, hu, sp, lobes, grow=0.25):\n    z = int(np.argmax(c.sum(axis=(1, 2)))); ys, xs = np.nonzero(c[z])\n    h, w = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1\n    py, px = max(3, int(grow * h)), max(3, int(grow * w))\n    box = (max(ys.min() - py, 0), ys.max() + py + 1, max(xs.min() - px, 0), xs.max() + px + 1)\n    return medsam2_box(hu, z, box)\nprint("MedSAM 2 ready")'),
          md("## 4. Run the exam (GPU: full model patch, ~20–40 s per scan incl. measuring)"),
          code(r'''import sys; sys.path.insert(0, "/content")
import engine.eval_detection as ev
ev.REFINERS["medsam2"] = medsam2_refiner
pids = sorted({c[0] for c in cases})
sys.argv = ["x", "/content/nii", "/content/cache", "/content/finding_results.csv"] + pids
ev.main()'''),
          md("## 5. Summary"),
          code(r'''import pandas as pd
r = pd.read_csv("/content/finding_results.csv"); mt = pd.read_csv("/content/finding_results_matching.csv")
f = r[r.found]
print(f"Expert tumour found: {r.found.sum()}/{len(r)} scans")
print(f"Long axis  |tool - expert| median {(f.tool_long - f.expert_long).abs().median():.1f} mm")
print(f"Short axis |tool - expert| median {(f.tool_short - f.expert_short).abs().median():.1f} mm")
print(f"Volume error median {((f.tool_vol - f.expert_vol).abs() / f.expert_vol * 100).median():.0f} %")
print(f"Dice median {f.dice.median():.3f}")
for v in ["halo", "medsam2"]:
    if f"{v}_dice" in f:
        print(f"  {v}: Dice {f[v+'_dice'].median():.3f} | long err {(f[v+'_long']-f.expert_long).abs().median():.1f} mm | short err {(f[v+'_short']-f.expert_short).abs().median():.1f} mm | vol err {((f[v+'_vol']-f.expert_vol).abs()/f.expert_vol*100).median():.0f} %")
print("By expert type:"); print(r.groupby("expert_type").agg(scans=("found", "size"), found=("found", "sum")))
print(f"Lobe agrees with lobe of expert outline: {(f.tool_lobe == f.expert_lobe).mean()*100:.0f} %")
print(f"Candidates per scan (>=4 mm): median {r.n_candidates.median():.0f}, max {r.n_candidates.max()}")
print(f"Tumour paired correctly test<->retest: {mt.tumour_matched.sum()}/{mt.tumour_matched.notna().sum()}")
print(f"Registration error at the tumour: median {mt.registration_error_mm.median():.1f} mm")
print(f"Other candidates seen in both scans: {mt.n_pairs.sum()}/{mt.n_current.sum()} (retest side)")
print(f"GPU seconds per scan (find): median {r.nodules_s.median():.0f}")
r[~r.found]'''),
          md("## 6. Download results (send both files back)"),
          code(r'''!cd /content && zip -q -r finding_results.zip finding_results*.csv && zip -q -r -0 engine_cache.zip cache
from google.colab import files
files.download("/content/finding_results.zip"); files.download("/content/engine_cache.zip")''')]

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
                                   "kernelspec": {"name": "python3", "display_name": "Python 3"}},
      "nbformat": 4, "nbformat_minor": 0}
json.dump(nb, open(os.path.join(HERE, "nodule_finding_exam.ipynb"), "w"), indent=1)
print("written")
