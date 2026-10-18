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
- **Demo data (public RIDER images + AI drafts):** `https://lungmarker-demo-data-sd.s3.eu-north-1.amazonaws.com/api/v1` (public, read-only)

## From the lab's words to the product

Built for a simulated research lab (Harbor Thoracic Oncology Lab): **Naomi Hart**, Research Director, and **Daniel Reyes**,
Research Fellow, who measures every scan by hand. Their study has ~390 scans waiting; today a scan takes Daniel
~39 min (baseline) or ~55 min (follow-up), and two-thirds of incoming scans are follow-ups.

> "In practice, if I'm still scrolling through every slice to find the nodules, the volume tool doesn't save me much overall time."
> — Daniel, on our first proposal (which put outlining first)

> "Since those central nodules are common for us, having a robust way to review those cases—or knowing exactly when the tool is unsure—will be key to saving me time without sacrificing our data quality."
> — Daniel, on the first results

> "Remember that I'll want to see the honesty you promised about the misses and failures."
> — Naomi, approving the plan

### What we heard → what we built

| # | What we heard | Who | What we built | Status |
|---|---|---|---|---|
| 1 | Find nodules across the whole scan, ≥ 4 mm, including faint ground-glass ones. Searching (two full passes over 250–400 images) is the biggest time sink. | Daniel | The AI finds nodules **before** Daniel opens the scan and marks them on the image and the slice bar. He does one quick check pass instead of two full searches, rejects false marks, adds missed ones. | ⚠️ Partial: found 52 of 59 tumours; **ground-glass not tested yet** (none in the test data) |
| 2 | Draft the outline and the long and short axis; let me correct them myself. Accept or reject alone is not enough. | Daniel | Outline, long and short axis drafted on the slice where the nodule is largest (his method). Drag, add or delete outline points, Erase, Draw, Undo; axes and volume update at once. | ✅ Built |
| 3 | On follow-ups, match each nodule to the prior scan, as a suggestion I confirm. A prior nodule I can't see is "Not found" plus a note. | Daniel | The AI suggests the match (never fills it in); prior and current shown side by side. "Not found" rows with the prior's ID and his note. Approve stays blocked until every prior nodule is matched or confirmed not found. | ✅ Built: 24 of 24 tumour pairs matched correctly |
| 4 | Export straight into my Excel format, with a record of what the AI drafted and what I changed. The sheet stays "the single source of truth". | Daniel, Naomi | One-click Excel export: his 18 columns in his order and formats, an Edit trail sheet (AI draft vs final value, who, when), only new rows each day. No new database to maintain. | ✅ Built: 30 automated checks pass |
| 5 | I must be able to open the tool myself and see results Daniel can defend. | Naomi | Results view: each nodule's final outline next to the AI's original, the full edit history, who approved, and change per patient over time. Read-only role for her. | ✅ Built |
| 6 | Volume for every tumour is the real goal (today only ~1 in 5 has one) — but recorded only after I have checked the edges. | Naomi, Daniel | Volume drafted for every nodule; written to the sheet only after Daniel presses **Confirm outline**. Any later edit un-confirms it. | ✅ Built; small-nodule (< 8 mm) volumes vary ~30% between repeat scans |
| 7 | Central tumours near the hilum and mediastinum are "common enough" in our cohort. | Daniel | Every AI miss in our test was central, so Approve requires **"I checked the hilum and mediastinum"**, with a one-click switch to the mediastinal window and Add nodule. An automatic "check here" flag was tried and dropped (too many false alarms). | ✅ Built (manual check) |
| 8 | Show me clearly when the AI is unsure. | Daniel | "AI unsure about the edges" label, amber colour, a count at the top of the list, and "may be larger than drawn" when the outline is likely too small. | ✅ Built; the signal is about edges, not "is this a nodule" |
| 9 | I work patient by patient, and I look up the prior scan in my sheet by hand. | Daniel | Worklist grouped by patient (baseline, then follow-ups), prior already linked, "Next scan for this patient". | ✅ Built |
| 10 | Halve my time per scan, with no drop in quality. "Minutes on scan" = the whole process, without long breaks. | Naomi, Daniel | Built-in timer fills "Minutes on scan" with active minutes; before vs after in [RESULTS.md](RESULTS.md). | ⏳ Timer built; time saved estimated from Daniel's step-by-step manual breakdown + Stav's timed runs in the tool |

### What we assumed → what we learned

Before talking to the lab we wrote down five assumptions to check (plan doc, 15 Oct). Their answers changed the product.

| We assumed | What we learned | What changed |
|---|---|---|
| **Outlining is the biggest time sink.** Our first proposal put "outline and measure" first and finding second. | **Searching is.** Daniel spends 10–20 min per scan scrolling every slice twice, for fear of missing a faint nodule; matching follow-ups comes second. | Priorities swapped: **find → outline → match → export**. Most new engine work went into finding. |
| **The researcher points at the tumour** and the AI outlines it ("click to outline" was the recommended option). | That keeps the search, which is the expensive part. | The AI finds every candidate ahead of time; Daniel reviews instead of searching. |
| **They record the longest diameter and the volume.** | Long and short axis on the slice where the nodule looks largest; volume only for the ~1 in 5 nodules he fully outlines. For Naomi, volume for every tumour is the real goal. | Measurements copy his method; volume drafted for every nodule, recorded once he confirms the outline; export = his exact 18 columns. |
| **Researchers want the final say on every tumour.** | Confirmed, and stronger: approving isn't enough, he must be able to **edit** the outline and values himself, and the study record needs to show what he changed. | Full editing tools, a Confirm outline step and an append-only edit trail in the export. |
| **The tool must run inside the hospital.** | Confirmed: real scans never leave the hospital network. | Built and tested on public data only (RIDER). The engine runs in batch, as it would on a hospital server fed by the image archive. |
| **Each scan has several tumours.** | Confirmed: 1–3 per scan, anything ≥ 4 mm. | Detection is needed, not just outlining. |
| *(Not on our list)* The director would want a **progress dashboard**. | Naomi reads the master sheet herself; it is "the single source of truth". | No dashboard. The tool feeds the sheet; the Results view is for checking outlines, not tracking progress. |
| *(Not on our list)* Scans come in **one by one**, and the AI's misses are an edge case. | Daniel works **patient by patient**, two-thirds of scans are follow-ups, and central tumours (all of the AI's misses) are common for them. | Worklist grouped by patient; time saved weighted by the real scan mix; a required central check before Approve. |
| *(Not on our list)* "Minutes on scan" = time in our review screen. | It covers his **whole process** (loading to typing into the sheet), without long breaks. | The timer runs from opening to approving and pauses when idle; the export uses active minutes. |

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
(`https://lungmarker-demo-data-sd.s3.eu-north-1.amazonaws.com/api/v1`).
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
   Serve `<out_dir>` from any static host (we use Amazon S3) and point the app's *Engine base URL* at it.

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
