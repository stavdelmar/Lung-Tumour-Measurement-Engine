# Results — LungMarker

**Research use only. No clinical claims.**
Status: draft, 16 Oct 2026. Engine numbers are final for the 59-scan exam; time numbers come after the pilot (marked **TBD**).
All figures are made by `python results/make_figures.py` from the CSVs in `results/`, so they update when the results change.

## The question

The lab's measure of success (Naomi, Research Director): **cut Daniel's time per scan roughly in half, with no drop in measurement quality**, and results Naomi can open and defend.
Daniel's log: **~39 min per baseline scan, ~55 per follow-up**. His biggest time sink is **searching** for nodules (10–20 min, two full passes over 250–400 images), then matching follow-ups to the prior scan.
So the tool attacks searching first, then outlining/measuring, matching and typing into his sheet.

## Summary

| | Result | Verdict |
|---|---|---|
| Finding the tumour | 52 / 59 scans (88%) | Works, with a known blind spot |
| Blind spot | all 7 misses are central tumours touching the hilum / mediastinum | Fails → mandatory "check the central areas" step in the app |
| Outline + measurements | long axis error median 2.8 mm, volume 20%; ~40–50% within the expert's own repeat noise | Partial → a draft Daniel confirms, not a final value |
| Lobe | 100% agree with the expert outline's lobe | Works |
| Matching to the prior scan | 24 / 24 tumour pairs correct | Works (small sample) |
| Export to Daniel's sheet | 18 columns, exact order and formats; edit trail sheet; 23/23 automated checks | Works (tested on synthetic data; real-file check **TBD**) |
| Time saved | **TBD** (pilot) | **TBD** |

## 1. What works

### Finding
![Found vs missed](results/figures/finding_found_vs_missed.png)

- The AI found the expert-marked tumour in **52 of 59 scans (88%)**: 48/53 solid, 4/6 part-solid. It runs ahead of review (batch), ~49 s per scan on a free Colab GPU.
- Other candidates: median 3 per scan. **82% of them are found again in the repeat scan** taken 15 min later (a proxy for "not random noise").

### Matching follow-ups
- In every pair where the tumour was found in both scans, it was **paired correctly (24 / 24)**. Lung alignment error at the tumour: median 2.9 mm.
- The app shows the match as a **suggestion**; Daniel records it only when certain (his rule).

### Review and export
- Daniel sees every AI mark on the image, can accept / reject, erase part of an outline (e.g. a vessel tail), redraw it, or add a missed nodule. Volume is recorded **only after he confirms the outline**.
- The export is his master sheet's 18 columns, plus an **edit trail** (AI draft vs his final value, who approved, when) and a read-me sheet with the research-use statement.
- Naomi can open Results and see each nodule's final outline next to the AI's original, with the full edit history.

## 2. What fails (and what we did about it)

### Central tumours are missed
All 7 misses (4 patients) are **central tumours touching the hilum or mediastinum**, 14–52 mm, with model probability ~0 inside the tumour. This is a limit of the model, not of our settings. Daniel told us central tumours are common in their cohort, so this matters.
→ **The app does not let a scan be approved until Daniel ticks "I checked the hilum and mediastinum"**, with a one-click switch to the mediastinal window and an "Add nodule" button. *(Planned: an engine "possible central mass" flag — result TBD.)*

### Outlines are not yet as precise as an expert
![Error vs expert](results/figures/outline_error_vs_expert.png)

- The bar is the expert's own variation between two scans 15 min apart: **2.3 mm long axis, 17% volume** (median, 28 patients).
- AI draft: **long axis median error 2.8 mm (no bias, +0.8), volume 20% (+5%)**. 38% of tumours are within the expert's noise on the long axis, 48% on volume. A few are far off (vessel tails, irregular tumours).
- → The draft saves drawing time, but **Daniel must check every outline**. That is how the app is built: confirm-before-record.

![Methods tried](results/figures/outline_methods.png)

We tried three outline methods on the same 52 tumours and kept the best ("model + halo"). The model alone draws too tight; MedSAM 2 with a box from the detection overshoots.

### Other known weak spots
- **Vessel tails** make 4 long axes too long → one stroke of the Erase brush fixes it in the app.
- **Key slice** within 2 slices of the expert's choice in 62% of cases (often two near-equal slices). Daniel picks the sharpest one anyway.

## 3. How we measured time saved

**TBD — protocol, to be run Sat/Sun:**
- **Before:** Daniel's own log, column "Minutes on scan" (whole process: loading, finding, measuring, typing). Last 5 rows: 38, 49, 30, 37 (baseline), 55 (follow-up). *Full column requested.*
- **After:** the app's built-in timer, same definition (scan opened → approved, total wall-clock), plus "active" time without idle. Logged per scan in `results/time_log.csv`.
- **Who:** a pilot by the developer on RIDER scans (baseline + follow-up), and Daniel when he tries the first version. Results are reported separately and labelled — a developer is not Daniel.
- **Target:** half → ~20 min baseline, ~27 min follow-up.

![Time](results/figures/time_before_after.png)

| Scan | Before (Daniel's log) | After (app timer) | Who | Notes |
|---|---|---|---|---|
| Baseline | 39 min | TBD | | |
| Follow-up | 55 min | TBD | | |

## 4. Limits — said out loud

- **RIDER marks one tumour per scan**, so false alarms can't be counted directly; the 82% repeat-scan agreement is only a proxy.
- **No ground-glass tumours in RIDER** — Daniel's hardest cases. A test on the public LNDb set (27 GGO + 46 part-solid ≥ 4 mm) is planned; its licence only allows sharing numbers, not images. *(TBD)*
- RIDER is a practice set (large, mostly solid tumours); the lab's real cohort may differ.
- The follow-up in RIDER is a repeat scan 15 min later: it tests matching, not growth.
- Time "after" comes from a small pilot, not a study.
- The detector (TotalSegmentator `lung_nodules`) was partly trained on LIDC-IDRI, not RIDER, so RIDER is unseen data for it.

## Raw data
`results/finding_exam_all59.csv` (one row per scan), `results/finding_exam_matching.csv` (one row per patient pair), `results/expert_baseline.csv` (expert test-retest), `results/finding_exam_summary.txt`.
