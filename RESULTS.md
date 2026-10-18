# Results — LungMarker

**Research use only. Not for clinical use. No clinical claims.**
Status: draft, 18 Oct 2026. Quality and failure numbers come from a test on public data (RIDER Lung CT). Timing is an estimate (Daniel's manual breakdown vs Stav's runs in the tool), still being collected (marked **TBD**).
Figures are made by `python results/make_figures.py` from the CSVs in `results/`, so they update when the numbers change.

The lab asked for three things for its lab meeting and grant panel: **an honest timing comparison, a quality comparison, and clear failure cases.** They come first, in that order. Details follow below in the same order.

---

## 1. Timing comparison

> **Takeaway: an estimate, not a measurement of Daniel using the tool. By Daniel's own account a follow-up scan takes 40–55 min today (a baseline about 39 min, from his log); the average incoming scan is about 45 min and the lab's target is about half. The "with the tool" figure is TBD.**

| | Share of incoming scans | Before: Daniel's manual review | With the tool: Stav's timed runs | Saved (estimate) |
|---|---|---|---|---|
| Baseline | ⅓ | ~39 min (log, 4 scans; no step breakdown yet) | TBD (n runs) | TBD |
| Follow-up | ⅔ | 40–55 min, midpoint ~48 (Daniel's own breakdown, 18 Oct); log: 55 min (1 scan) | TBD (n runs) | TBD |
| **Per incoming scan (weighted)** | | **~45 min** (~50 with the log figure) | **TBD** | **TBD** |

- **How it is built:** Daniel can't use the tool on his own scans (they never leave the hospital), so the comparison combines **Daniel's step-by-step account of his manual review** with **Stav's timed runs in the tool on public scans**. Everything here is an estimate. Method agreed with Base44's FDE lead (Sam) on 18 Oct; full method and step table in [section 4](#4-timing-details).
- **We use the lower "before" (~45 min) for the headline,** so the saving is not overstated; the log-based ~50 min is shown next to it.
- **Small samples:** 5 log rows, Daniel's breakdown is for follow-ups only, and the ⅔ follow-up share is his estimate.

## 2. Quality comparison

> **Takeaway: on 52 tumours from 28 patients (public data), the AI's first draft is close to the expert on average but not as precise per tumour, so every measurement is checked and confirmed by the reviewer before it is recorded.**

| What we compared | Sample | Result |
|---|---|---|
| **Finding:** was the expert-marked tumour found, with no hint? | 59 scans, 31 patients | **52 / 59 scans (88%)** |
| **Long axis:** AI draft vs expert outline | 52 tumours, 28 patients | median error **3.0 mm**, no systematic bias (−0.3 mm); **20 / 52** within the expert's own repeat variation (2.3 mm) |
| **Volume:** AI draft vs expert outline | 52 tumours, 28 patients | median error **14%**, no systematic bias (+0.5%); **27 / 52** within the expert's own repeat variation (17%) |
| **Matching** a tumour to the earlier scan | 24 patient pairs | **24 / 24** paired correctly |
| **Lobe** | 52 tumours | agrees with the expert outline's lobe in **52 / 52** |
| **Small nodules (< 8 mm), same nodule on two scans 15 min apart** (no expert outline) | 84 nodule pairs, 22 patients | diameter differs by a median **0.5 mm**; volume by **~30%** |

- **Yardstick:** the expert's own variation between two scans of the same patient taken 15 minutes apart (median 2.3 mm long axis, 17% volume; 28 patients).
- **What this measures:** the AI's *first draft*. What goes into the lab's sheet is the reviewer's *confirmed* value; its quality was not measured here. The edit trail records every change, so it can be measured on real use.
- **The test tumours are large** (13–93 mm, median 43 mm). The lab measures nodules from 4 mm, so small-nodule accuracy is not established by this test.

## 3. Failure cases

> **Takeaway: the AI misses some central tumours and draws some outlines far off; the app is built so the reviewer catches these, and some cases have not been tested at all.**

| Failure | How often (sample) | What the app does about it |
|---|---|---|
| **Central tumours touching the hilum or mediastinum are missed**, even large ones (14–52 mm) | 7 / 59 scans, 4 / 31 patients; all of the AI's misses | Approve is blocked until the reviewer ticks "I checked the hilum and mediastinum" (one click to the mediastinal window, quick Add nodule). An automatic "check here" flag was tried and dropped: it caught 4 of the 7 but also flagged 49 of the other 52 scans. |
| **Outline far off:** long axis more than 5 mm from the expert | 19 / 52 tumours (14 patients): 13 drawn too small, 6 too large | Nothing is recorded until the reviewer confirms the outline; Erase / Draw / move points to fix it. The 4 small faint tumours drawn much too small now show "AI unsure about the edges"; the larger misses are not flagged. |
| **Small-nodule volume is approximate** | ~30% difference between repeat scans for nodules < 8 mm (84 pairs) | Diameters are the reliable number for small nodules; volume is recorded only after the reviewer confirms the outline. |
| **A wrong follow-up match** would also misalign the side-by-side view | Not seen in the test (24 / 24 correct), but possible | The match is only a suggestion the reviewer picks; a "Check this match" warning flags a different lobe, a > 50% size change or disagreement with the alignment. |
| **Not tested** | — | **Ground-glass nodules** (none in this data set; planned on the public LNDb set). **False alarms** (the data marks one tumour per scan; only a proxy: 82% of AI marks reappear on the repeat scan). **The lab's own scans** (development used public data only). |

## Why this differs from last year's tool

Naomi told us why the vendor tool the lab tried last year failed. Each reason, and what we did about it:

| Why last year's tool failed | What LungMarker does | Honest caveat |
|---|---|---|
| **1. Accept / reject only, no editing of outlines** | The reviewer edits the outline directly (move, add or delete points, Erase, Draw); axes and volume update at once. Volume is recorded only after they press Confirm outline. Every change is kept in an **edit trail**: AI draft, final value, who, when. | Editing has been tested by us, not yet by Daniel on his own scans. |
| **2. No export to their sheet** | One-click Excel export in the lab's exact format: the same 18 columns, order and formats as the master sheet, only new rows each day, plus the edit trail as a second sheet. The sheet stays the single source of truth. | Checked on real exports from the live app and by 30 automated checks, on public test scans. |
| **3. Needed hospital IT to install it** | The app runs in the browser: **nothing is installed on Daniel's or Naomi's computer.** | **Some IT involvement remains for real use.** Real scans can't leave the hospital, so the AI engine has to run **inside the hospital on one server**, processing scans in batch (e.g. overnight) from the image archive. IT would set up that server, connect it to the archive, and approve where data is stored: the app is a cloud service that keeps study IDs, measurements and the edit trail (not images; the browser loads the images straight from the hospital server). That is one server and a data-governance review, much less than installing software on every workstation, but not zero. |
| **4. Too expensive for a research budget** | Built on a low-cost stack: **open-source AI models** (Apache-2.0, no licence or per-scan fees), the app on a Base44 subscription, and a free Colab GPU plus a public storage bucket for the demo. | Not yet costed for real use. Running it adds a Base44 plan, one hospital server and some IT time; the exact yearly cost still has to be written down (see next steps). |

---

## 4. Timing details

### 4.1 How the comparison was built (method)

**Why an estimate.** The honest measurement would be Daniel timing his own work with and without the tool on the lab's scans. That isn't possible here: the lab's scans never leave the hospital, and the tool runs on public data only. So the comparison combines two sources that can be collected now. Method agreed with Sam (Base44 FDE lead), 18 Oct.

**Step 1: "Before" = Daniel's manual review, step by step.** Daniel described his usual follow-up review step by step, with minutes per step (Slack, 18 Oct; table in 4.2). Some steps are per nodule, so the per-scan "before" is **his own stated total, 40–55 min** (midpoint ~48), not a sum we calculated. It is cross-checked against his log (one follow-up row: 55 min; −14%, within the 20% we set for reporting a mismatch). He has not given a baseline breakdown yet, so the baseline uses his log (~39 min, 4 scans).

**Step 2: "With the tool" = Stav's timed runs only.** The "with the tool" minutes are **measured whole-scan times from Stav's runs**, not estimated step by step. Stav reviews public RIDER scans in the live app from start to finish, baseline and follow-up, doing every step Daniel would: check each AI mark, fix outlines, match to the prior, central check, approve. The app's own timer records **active minutes** (paused after 2 min without input or a hidden tab), which is what the app writes into "Minutes on scan" and matches Daniel's definition (whole process, no long breaks; 17 Oct). Open minutes are kept and reported next to them.

**Step 3: Combine.** Median minutes per baseline and per follow-up, then weighted by the lab's mix (⅓ baseline, ⅔ follow-up) for the headline. The same weighting is used for before and after (`results/make_figures.py`).

**What could push the estimate either way (said out loud):**
- **Different people:** Stav built the tool and knows it well, which speeds her up. But she is not a trained reader, so she may check marks less thoroughly than Daniel would (faster) or less confidently (slower).
- **Different scans:** the public test scans mostly have large, obvious tumours. Daniel's real work includes faint ground-glass nodules, his slowest cases. **This probably makes the "after" figure optimistic.**
- **Different settings:** Stav's runs don't include the hospital's own systems (opening the study from the archive, the hospital viewer).
- **Different clocks:** Daniel's "before" was typed into his log by hand; we can't tell exactly how he handled breaks.
- **Small samples on both sides.** Each run and each log row is listed in the table below.

**The real measurement comes later:** in a hospital pilot, Daniel times his own reviews with and without the tool on the lab's scans (next steps).

### 4.2 Numbers

**Daniel's manual follow-up review, step by step** (his words, Slack, 18 Oct), and what the tool does to each step. The tool column describes the design; it is not a measured time per step.

| Step | Daniel today (manual) | What the tool does | Removed / shortened / kept |
|---|---|---|---|
| Loading | 1–2 min per scan | The scan opens from the worklist with the AI's marks already there (the AI runs beforehand, in batch); the prior scan is already linked. | Shortened |
| Re-finding each prior nodule and matching it | ~10 min **per nodule**: he aligns by bronchi and fissures because slice numbers are unreliable (breathing) | The AI suggests the match, and the prior and current scans open side by side, centred on the pair. He confirms or picks another; every prior nodule must be matched or marked "Not found". | Shortened (he still verifies each match) |
| Finding new nodules | 10–20 min per scan: two full passes over 250–400 slices | The AI marks candidates; one check pass, plus a required check of the hilum and mediastinum, where the AI misses tumours. | Shortened (the check stays) |
| Measuring | 2–4 min **per nodule** | Long and short axis drafted on the slice where the nodule is largest; he checks or edits them. | Shortened |
| Full outline | 15–25 min **per tumour, when needed** | Outline drafted for every nodule; he checks, edits and confirms it. Volume is then recorded for every confirmed nodule, not only the ones he outlines today. | Shortened per tumour; done for more nodules than today |
| Recording | 3–5 min per scan | Values are saved as he goes; one Excel export into his sheet's format, usually once a day. | Removed from the per-scan time (one export a day) |
| *New:* deciding on each AI mark | — | Accept or reject every AI suggestion, including false marks. | Added |
| *New:* central-areas check | — | Required tick before Approve: "I checked the hilum and mediastinum". | Added |
| **Total** | **40–55 min** (his own total) | **Measured as a whole: Stav's timed runs, below** | |

**Per scan, before vs with the tool (estimates):**

| | Share of incoming scans | Before: Daniel | Before: log (cross-check) | Target (half) | With the tool: Stav's runs (active min, n) | Saved (estimate) |
|---|---|---|---|---|---|---|
| Baseline | ⅓ | no breakdown yet → log | ~39 min (4 scans) | ~20 min | TBD | TBD |
| Follow-up | ⅔ | 40–55 min (midpoint ~48) | 55 min (1 scan) | ~24 min | TBD | TBD |
| **Per incoming scan (weighted)** | | **~45 min** | **~50 min** | **~22 min** | **TBD** | **TBD** |

![Time](results/figures/time_before_after.png)

**Data files.** Daniel's breakdown → `results/daniel_steps.csv` (`timepoint`, `step`, `unit`, `minutes_low`, `minutes_high`, `source`; a `TOTAL` row holds his own per-scan total). Stav's runs → `results/time_log.csv` (`timepoint`, `scan_id`, `active_minutes`, `open_minutes`, `who`). `python results/make_figures.py` rebuilds the chart and prints before, after, saved and the breakdown-vs-log cross-check. Timepoints without a breakdown (baseline, for now) use the log totals.

## 5. Quality details

**Test set.** RIDER Lung CT (public, The Cancer Imaging Archive): 31 patients, each scanned twice 15 minutes apart, 59 scans with an expert outline of one tumour. The whole pipeline runs with no hint. Measurements are taken the way Daniel takes them (long axis on the slice where the tumour is largest, perpendicular short axis, volume from the outline), on both the AI's and the expert's outline. The detector was not trained on RIDER.

### Finding
![Found vs missed](results/figures/finding_found_vs_missed.png)

- Expert tumour found in **52 of 59 scans (88%)**: 48 / 53 solid, 4 / 6 part-solid. The AI runs before review, ~49 s per scan on a free Colab GPU.
- Other AI marks: median 3 per scan. 82% of them reappear on the repeat scan taken 15 min later. This is only a proxy for "not a false alarm", because RIDER doesn't mark other nodules.

### Outline and measurements
![Error vs expert](results/figures/outline_error_vs_expert.png)

- Shipped outline setting (rim width scaled to the size of the AI's core): **long axis median error 3.0 mm (bias −0.3 mm), 20 / 52 within 2.3 mm; volume median error 14% (bias +0.5%), 27 / 52 within 17%**; median overlap with the expert outline (Dice) 0.76.
- No systematic bias, but individual tumours vary around the expert's value more than the expert varies between two scans. So the draft saves drawing time, and **every outline is checked**: volume is recorded only after the reviewer confirms it (Daniel's own rule).

![Methods tried](results/figures/outline_methods.png)

How the method was chosen (first exam, same 52 tumours): the model's own outline is too tight (long axis 6 mm short on median), MedSAM 2 with a box from the detection overshoots (+5.8 mm), and adding a rim around the model's core fixed the bias. Later the rim width was tuned (four variants compared on these 52 tumours, `results/halo_variants_found52.csv`); a more adaptive variant did better here (24 / 52 within 2.3 mm) but grew small nodules along vessels on other scans, so it was not shipped. Because the settings were compared on the same tumours, these numbers are somewhat optimistic; an independent test (LNDb) is planned.

### Matching and lobe
- In every pair where the tumour was found in both scans it was **paired correctly (24 / 24)**. Lung alignment error at the tumour: median 2.9 mm (max 13.9 mm).
- Note: the RIDER "follow-up" is a repeat scan 15 minutes later, so this tests matching, not growth.
- Lobe agrees with the expert outline's lobe in 52 / 52.

### Small nodules (repeatability, no expert outline)
- Same nodule on the two scans 15 min apart: 84 pairs < 16 mm (median 7 mm), 22 patients. Long axis: median difference 0.5 mm (72 / 84 within 2.3 mm). Volume: median 28% difference (32% for nodules < 8 mm). For small nodules, the diameters are reliable and the volume is approximate.

## 6. Failure details

### Central tumours are missed
All 7 misses (4 patients) are **central tumours touching the hilum or mediastinum**, 14–52 mm, with the model giving ~0 probability inside the tumour, so this is a limit of the model, not of our settings. Daniel told us central tumours are "common enough" in their cohort, so this matters for the lab.
- **What the app does:** Approve is blocked until the reviewer ticks "I checked the hilum and mediastinum", with a one-click switch to the mediastinal window and an Add nodule button.
- **Automatic flag tried, not kept** (3 ideas, ~2 h). Two flagged none of the missed tumours (3 of the 4 lie inside the lung outline, not in a dent). The best flagged 4 of the 7 missed scans but also raised 107 false flags on the other 52 scans (49 of 52 flagged), which would teach the reviewer to ignore it. Code and numbers: `engine/experiments/`. A likely real fix (a second model trained on lung-cancer outlines) did not fit this week.

### Outlines far off
- 19 / 52 long axes are more than 5 mm off (shipped setting): 13 too small, 6 too large.
- **Too small, small tumours (4):** the model marked only a small core of a fainter tumour. Since 17 Oct the engine flags these ("AI unsure about the edges: may be larger than drawn"); it catches all 4 and fires on 12% of all AI marks. Tuned on only 4 cases, so its true catch rate is uncertain.
- **Too small, large tumours (9):** not flagged. The reviewer has to see it.
- **Too large (6):** causes seen in the first exam were a rim drawn a little too wide or a vessel tail running off the nodule. One stroke of the Erase brush removes a tail.
- Key slice within 2 slices of the expert's choice in 62% of cases (often two near-equal slices); the reviewer can pick another.

### Follow-up view
In the side-by-side view, the earlier and current scans are locked together (centre, zoom, slice scrolling) by aligning on the **matched pair**, not on the engine's lung alignment, which the engine doesn't export yet. So **a wrong match also misaligns the two views.** The "Check this match" warning (different lobe, size > 50% different, alignment disagrees) is the guard for now. Next step: export each earlier nodule's aligned position from the engine.

## 7. Limits

- **Public practice data, not the lab's scans:** RIDER is mostly large, solid tumours (13–93 mm); the lab measures from 4 mm, and its cohort may differ.
- **No ground-glass nodules** in RIDER, which are Daniel's hardest cases. A test on the public LNDb set (27 ground-glass + 46 part-solid nodules ≥ 4 mm) is planned; its licence allows sharing numbers only, not images. *(TBD)*
- **False alarms** can't be counted directly (one marked tumour per scan); the 82% repeat-scan agreement is only a proxy.
- **Settings tuned on the test tumours:** the outline settings were compared on the same 52 tumours, so the quality numbers are somewhat optimistic.
- **The RIDER follow-up is a same-day repeat scan:** it tests matching, not growth.
- **Timing is an estimate,** not a measurement of Daniel using the tool: his manual breakdown vs Stav's runs on public scans, small samples on both sides (section 4.1).
- **What we measured is the AI's first draft,** not the reviewer's confirmed values that go into the sheet.

## 8. Next steps

- **Finish the timing estimate:** Daniel's step-by-step breakdown, Stav's timed runs, and the full "Minutes on scan" column for a stronger "before".
- **Ground-glass test** on the public LNDb set (27 ground-glass + 46 part-solid nodules ≥ 4 mm), which also decides the outline setting for small nodules.
- **Central tumours:** try a second model trained on lung-cancer outlines, used only where it disagrees with the nodule model; keep the manual central check until a test shows it works.
- **Follow-up view:** export the lung alignment from the engine, so the side-by-side view and the "Check this match" warning use the real alignment.
- **Cost for a research budget (last year's tool failed on price):** write down the full yearly cost before any rollout, namely the Base44 plan, one hospital server (an existing machine if it has a GPU or at least 8 GB of memory; CPU speed not yet measured) and the IT hours to set it up, so Naomi can compare it with last year's tool. No licence or per-scan fees for the AI models.
- **Hospital pilot (the real measurement):** with IT, run the engine on one hospital server on a small set of the lab's own scans; Daniel times his own reviews with and without the tool, and his confirmed values are compared with his manual ones.

## What the app does (for reference)
- The reviewer sees every AI mark on the image, accepts or rejects it, fixes the outline (move, add or delete points, Erase, Draw), or adds a missed nodule. Volume is recorded **only after the reviewer confirms the outline**.
- The export is the lab's master sheet (18 columns, same order and formats), plus an **edit trail** (AI draft vs final value, who approved, when) and a read-me sheet with the research-use statement. Checked on real exports from the live app and by 30 automated checks.
- Naomi can open Results and see each nodule's final outline next to the AI's original, with the full edit history.

## Raw data
`results/finding_exam_all59.csv` (one row per scan), `results/finding_exam_matching.csv` (one row per patient pair), `results/halo_variants_found52.csv` (outline settings on the 52 found tumours; shipped = `scaled_*`), `results/small_nodule_repeatability.csv`, `results/expert_baseline.csv` (expert test-retest), `results/central_check_blob_all59.csv`, `results/faint_flag_candidates.csv`, `results/finding_exam_summary.txt`.
