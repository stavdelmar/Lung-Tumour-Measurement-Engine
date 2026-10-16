# LungMarker — AI-assisted lung nodule measurement

Home assignment, Forward Deployed Engineer (Base44), Stav Delmar.
**For research use only. Not for clinical use. No clinical claims.**

LungMarker cuts the time a researcher spends finding, outlining and measuring lung nodules on CT.
The AI finds nodules ahead of time and drafts the outline, axes, volume, lobe and the match to the prior scan.
The researcher reviews each one, fixes what's wrong, checks the central areas the AI misses, approves,
and exports straight into the lab's Excel master sheet with an edit trail.

- **Live app:** https://lung-marker-scan.base44.app (Google sign-in)
- **Results (what works, what fails, time saved):** [RESULTS.md](RESULTS.md)
- **App code (Base44):** https://github.com/stavdelmar/lungmarker
- **Demo data (public RIDER images + AI drafts):** https://github.com/stavdelmar/lungmarker-demo-data

## How it fits together

```
 RIDER CT scans ──► Engine (Python, this repo) ──► static API files ──► LungMarker app (Base44)
                    find · outline · measure        scans, slices,       worklist · review · approve
                    lobe · match to prior           findings (JSON/PNG)  edit trail · Excel export
                    (batch, Colab GPU)                                   results view for the director
```

- **Engine (this repo).** Finds nodules with TotalSegmentator `lung_nodules`, assigns lobes with TotalSegmentator `total`,
  outlines and measures each nodule like the researcher does (long axis on the slice where it is largest, perpendicular
  short axis, volume from the 3D outline), and pairs nodules between baseline and follow-up (lung registration + matching).
  The model needs a GPU at full settings, so it runs **in batch on Google Colab** and writes its output as static files.
- **App ([lungmarker](https://github.com/stavdelmar/lungmarker), Base44).** Reads the engine's files over HTTP. Stores only
  review data: the researcher's edits, approvals, time spent. All corrections (erase, redraw, add a missed nodule) run in the browser.
- **Why no live AI server:** free hosting can't run the model at full settings, and the review needs no live AI.
  In a real deployment the engine would run on the hospital's own server, fed by its image archive (PACS); scans never leave the hospital.
- **API contract:** [docs/engine_api.md](docs/engine_api.md).

## Repo map

| Path | What it is |
|---|---|
| `engine/` | Engine code: `detect.py` (finding + lobes), `measure.py`, `match.py`, `correct.py` (click-to-correct, live mode only), `api.py` (FastAPI), `export_static.py` / `build_demo.py` (static API for the app), `eval_detection.py` + `summarize_exam.py` (the 59-scan exam) |
| `notebooks/` | Colab notebooks: `nodule_finding_exam.ipynb` (whole pipeline on all 59 scans), `medsam2_vs_our_engine.ipynb` (outline comparison) |
| `results/` | Raw results CSVs, `make_figures.py`, `figures/` |
| `demo/` | The static API tree the app reads (also published in the demo-data repo) |
| `space/` | Docker files for a future live engine (not deployed) |
| `docs/` | Engine API contract |

## How to run

### 1. Use the app (no install)
Open https://lung-marker-scan.base44.app, sign in with Google. Settings → *Engine base URL* points at the demo data
(`https://raw.githubusercontent.com/stavdelmar/lungmarker-demo-data/main/demo` — **TBD: confirm once the repo is live**).
The Worklist fills itself with the demo scans. Open one, review, approve, then *Results → Export to Excel*.
A reviewer role is needed to edit (ask the owner); everyone else sees results read-only.

### 2. Re-run the AI on the RIDER scans (Colab, free GPU)
1. Open `notebooks/nodule_finding_exam.ipynb` in Google Colab, runtime **T4 GPU**.
2. Run all. It downloads RIDER Lung CT and the expert outlines from TCIA's public API, runs the whole pipeline
   (~1 min per scan) and saves `finding_results.zip` (the exam CSVs) and `engine_cache.zip` (the AI drafts).
3. Locally: `pip install -r requirements-engine.txt`, then build the static API for the app:
   ```
   python -m engine.build_demo <nii_dir> <cache_dir> <state_dir> <out_dir> RIDER-1225316081 RIDER-1500037140 ...
   ```
   `<nii_dir>` = scans converted with `engine/prepare_data.py`; `<cache_dir>` = unzipped `engine_cache.zip`.
   Serve `<out_dir>` from any static host and point the app's *Engine base URL* at it.

### 3. Reproduce the results and figures
```
pip install pandas matplotlib
python results/make_figures.py
```
Prints the headline numbers and rewrites `results/figures/*.png`. See [RESULTS.md](RESULTS.md).

### 4. Live engine (optional, not deployed)
```
pip install -r requirements-engine.txt
ENGINE_DATA=/data/scans ENGINE_STATE=/data/state uvicorn engine.api:app --port 7860
```
Needs ~8+ GB RAM on CPU (or a GPU) to process new scans. Adds `refine` (click-to-correct on the server).

## Data and credits

- RIDER Lung CT: Zhao, B. et al. (2015). *Coffee-break lung CT collection with scan images reconstructed at multiple imaging parameters.* The Cancer Imaging Archive. https://doi.org/10.7937/k9/tcia.2015.u1x8a5nr (CC BY 3.0)
- RIDER-LungCT-Seg: Wee, L., Aerts, H., Kalendralis, P., & Dekker, A. (2020). *RIDER Lung CT Segmentation Labels from: Decoding tumour phenotype by noninvasive imaging using a quantitative radiomics approach.* The Cancer Imaging Archive. https://doi.org/10.7937/tcia.2020.jit9grk8
- TotalSegmentator (Wasserthal, J. et al., 2023), incl. the `lung_nodules` model by BlueMind AI. Apache-2.0. https://github.com/wasserth/TotalSegmentator
- MedSAM 2: Ma, J. et al. (2025). arXiv:2504.03600. Apache-2.0 (compared, not used).
- lungmask: Hofmanninger, J. et al. (2020). https://github.com/JoHof/lungmask (earlier engine version).

All data used is public. The lab's own scans were never used.
