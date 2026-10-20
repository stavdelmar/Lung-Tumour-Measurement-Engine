# Results — LungMarker

**Research use only. Not for clinical use. No clinical claims.**
Status: draft, 20 Oct 2026. Quality and failure numbers come from a test on public data (RIDER Lung CT). Timing is an estimate: Daniel's own step-by-step account of his manual review, a developer pilot that measures the tool's own steps, and Daniel's estimate of checking time.
Figures are made by `python results/make_figures.py` from the CSVs in `results/`, so they update when the numbers change.

The lab asked for three things for its lab meeting and grant panel: **an honest timing comparison, a quality comparison, and clear failure cases.** They come first, in that order. Details follow below in the same order.

---

## 1. Timing comparison

> **Takeaway (estimate): a follow-up scan (two nodules) that takes Daniel 40–55 min today would take about 13–17 min with the tool, roughly 60–75% less. That rests on the tool's own steps, measured at 1–2 min per scan (7 developer runs), and on Daniel's own estimate that checking a draft takes 20–30% of the time of doing it from scratch, not a measurement. The tool still saves half as long as checking stays under about 45% of doing it by hand. Not every draft is solid, so some scans will take longer. The next step is Daniel's own timed reviews.**

| | Share of incoming scans | Today: Daniel, manual | Tool's own steps, measured (developer pilot) | Checking each draft (Daniel's estimate) | With the tool (estimate) |
|---|---|---|---|---|---|
| Baseline | ⅓ | ~39 min (log, 4 scans) | 1–2 active min (4 scans) | 20–30% of doing it by hand | not estimated (no step breakdown yet) |
| Follow-up | ⅔ | 40–55 min (Daniel's own step-by-step estimate); log: 55 min (1 scan) | 1–2 active min (3 scans; 1 excluded) | 20–30% of doing it by hand | **≈ 13–17 min** (two nodules), roughly 60–75% less; half of today = 20–27.5 min |
| **Per incoming scan (weighted)** | | **~45 min** (~50 with the log figure) | | | not estimated |

- **What the pilot measures:** the tool's mechanics (opening a scan, accepting or rejecting marks, confirming and editing outlines, matching, approving, export), done by the developer on public scans. It does **not** include a trained reader's checking time, which is where most of Daniel's time goes.
- **Checking time is Daniel's estimate, not ours and not measured:** checking a match or an outline takes "about 20–30% of the time" of doing it from scratch, "assuming the draft is generally solid" (Slack, 20 Oct). Not every draft is solid (19 of 52 outlines were more than 5 mm off; central tumours are missed), so some cases will take longer.
- **How it is built:** Daniel can't use the tool on his own scans (they never leave the hospital), so the comparison combines his step-by-step account of his manual review with the developer's timed runs. Method agreed with Base44's FDE lead (Sam) on 18 Oct; step table in [section 4](#4-timing-details).
- **Small samples on both sides:** 7 timed runs, 5 log rows, a follow-up breakdown only, and the ⅔ follow-up share and the 20–30% checking share are Daniel's estimates.

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

**Why an estimate.** The real measurement would be Daniel timing his own work with and without the tool on the lab's scans. That isn't possible yet: the lab's scans never leave the hospital, and the tool runs on public data only. So we combine three inputs that can be collected now. Method agreed with Sam (Base44 FDE lead), 18 Oct; Daniel's checking estimate added 20 Oct.

**Source 1: Daniel's manual review, step by step** (his words, Slack, 18 Oct; table in 4.2). Some steps are per nodule, so the per-scan figure is **his own stated total for a follow-up, 40–55 min**, not a sum we calculated. Cross-check against his log: one follow-up row, 55 min (−14% from his midpoint, within the 20% we set for flagging a mismatch). No baseline breakdown yet, so the baseline uses his log (~39 min, 4 scans).

**Source 2: the developer's timed runs in the tool** (Stav, 18 Oct, final app version, 4 public RIDER patients, baseline + follow-up each). Each scan was taken through the whole flow: accept or reject every AI mark, confirm outlines, match to the prior, central check, approve, export. Minutes come from the app's own timer ("Minutes on scan" and the approval rows in the edit trail): **active minutes**, paused after 2 min without input or a hidden tab, rounded to whole minutes, so "1 min" means roughly 0.5–1.5 min. One follow-up (12 active min) is excluded because the scan was left open while writing messages.

**Source 3: Daniel's estimate of checking time** (Slack, 20 Oct): checking a match or an outline takes "about 20–30% of the time" of doing it from scratch, "assuming the draft is generally solid". We call this share **f = 0.20–0.30**. It is his estimate, not a measurement and not ours.

**Combining them.** For one follow-up scan:

> **With the tool ≈ opening 0.5 + checking (f × 41) + tool steps 1.5 + centre check 2.5** (minutes)

- **The parts:** opening the scan 0.5 min (loading, 1–2 min today, is mostly gone: the AI has already run); the tool's own steps 1.5 min (midpoint of the measured 1–2); the required central check 2.5 min; and checking the AI's drafts, f × 41 min. **41 min = what the tool shortens for two nodules: searching 15 (midpoint of 10–20) + matching 2 × 10 + measuring 2 × 3.** Recording (3–5 min) is removed: values are saved as he goes and exported once a day.
- **Result:** 0.5 + 0.20 × 41 + 1.5 + 2.5 ≈ 13 min at f = 0.20; 0.5 + 0.30 × 41 + 1.5 + 2.5 ≈ 17 min at f = 0.30. So **≈ 13–17 min per follow-up vs 40–55 today, roughly 60–75% less.**
- **Against the lab's target:** half of today is 20–27.5 min, so the estimate is under half across Daniel's range.
- **Break-even:** the tool still saves half as long as checking takes less than **about 45%** of doing it by hand (f < ~0.45, solving 4.5 + 41 f = ½ × today at today's midpoint of 47.5 min; it is ~0.38 if today is 40 min and ~0.56 if 55). Daniel's estimate (20–30%) leaves room for error.
- **Not included:** full outlines (15–25 min per tumour, only when needed) aren't in the 41 min, on either side; the estimate is for two nodules, and more nodules add matching and measuring time.
- **What could make it slower:** drafts that aren't "generally solid" (19 of 52 outlines more than 5 mm off; missed central tumours to add by hand), and the new steps (deciding on each AI mark, the central check), which his estimate may not fully cover.

**What the pilot shows on its own:** the tool's mechanics are not where the time goes. For 2–5 nodules per scan, opening, confirming, editing, matching and exporting took about 1–2 active minutes. The open question is how fast a trained reader checks the drafts; Daniel's estimate gives a first answer, and his timed reviews would measure it.

**Caveats, said out loud:**
- **Developer, not a reader:** Stav built the tool and knows it well, and did not spend a reader's judgement time on each mark.
- **Easier scans:** the public test scans mostly have large, clear tumours; the lab's real work includes faint ground-glass nodules (Daniel's slowest cases), which would likely need more edits and more checking.
- **No hospital systems:** the runs don't include opening a study from the hospital archive or its viewer.
- **Hand-typed "before":** Daniel's log was typed by hand, and his breakdown is his own estimate.

**Next step:** Daniel's own timed reviews with the tool on the lab's scans, in a hospital pilot. That replaces his estimate of checking time with a measurement.

### 4.2 Numbers

**Daniel's manual follow-up review, step by step** (his words, Slack, 18 Oct), and what the tool does to each step. The tool columns describe the design; there is no measured time per step. Checking time is Daniel's own estimate (20 Oct), applied to the whole scan, not step by step.

| Step | Daniel today (manual) | What the tool does | Removed / shortened / kept | What's left with the tool |
|---|---|---|---|---|
| Loading | 1–2 min per scan | The scan opens from the worklist with the AI's marks already there (the AI runs beforehand, in batch); the prior scan is already linked. | Shortened | Opening the scan (part of the measured overhead) |
| Re-finding each prior nodule and matching it | ~10 min **per nodule**: he aligns by bronchi and fissures because slice numbers are unreliable (breathing) | The AI suggests the match; the prior and current scans open side by side, centred on the pair. Every prior nodule must be matched or marked "Not found". | Shortened | His check of each suggested match: **checking: Daniel estimates 20–30% of doing it by hand** |
| Finding new nodules | 10–20 min per scan: two full passes over 250–400 slices | The AI marks candidates; one check pass, plus a required check of the hilum and mediastinum, where the AI misses tumours. | Search shortened; his check kept | One check pass + the central check: **checking: Daniel estimates 20–30% of doing it by hand** |
| Measuring | 2–4 min **per nodule** | Long and short axis drafted on the slice where the nodule is largest. | Shortened | Checking (and if needed editing) each axis: **checking: Daniel estimates 20–30% of doing it by hand** |
| Full outline | 15–25 min **per tumour, when needed** | Outline drafted for every nodule; volume recorded for every confirmed nodule, not only the ones he outlines today. | Shortened per tumour; done for more nodules than today | Checking, editing and confirming each outline: **checking: Daniel estimates 20–30% of doing it by hand** |
| Recording | 3–5 min per scan | Values saved as he goes; one Excel export into his sheet's format, usually once a day. | Removed from the per-scan time | One export a day (overhead) |
| *New:* deciding on each AI mark | — | Accept or reject every AI suggestion, including false marks. | Added | **Checking: part of Daniel's estimate** |
| *New:* central-areas check | — | Required tick before Approve: "I checked the hilum and mediastinum". | Added | **Checking: part of Daniel's estimate** |
| **Total** | **40–55 min** (his own total) | | | **≈ 13–17 min = opening 0.5 + checking (f × 41) + tool steps 1.5 + centre check 2.5, f = 0.20–0.30 (his estimate)** |

**Developer pilot: tool overhead per scan** (`results/time_log.csv`; whole active minutes from the app's timer):

| Patient (public RIDER) | Timepoint | Active min | Open min | Nodules reviewed | Note |
|---|---|---|---|---|---|
| RIDER-1225316081 | Baseline | 1 | 1 | 2 | |
| RIDER-1225316081 | Follow-up 1 | *12* | *20* | 3 | **Excluded:** scan left open while writing messages |
| RIDER-1332496276 | Baseline | 1 | 1 | 2 | |
| RIDER-1332496276 | Follow-up 1 | 1 | 1 | 2 | |
| RIDER-1500037140 | Baseline | 2 | 2 | 4 | |
| RIDER-1500037140 | Follow-up 1 | 2 | 2 | 4 | |
| RIDER-1532432635 | Baseline | 2 | 2 | 5 | incl. 2 rejected |
| RIDER-1532432635 | Follow-up 1 | 2 | 2 | 5 | incl. 1 rejected + 1 not found |
| **Included: 7 scans** | | **1–2 (median 2)** | | **2–5** | developer, not a reader |

**Per follow-up scan, today vs with the tool (estimate):**

| | Today: Daniel | Opening | Tool's own steps (measured 1–2) | Centre check | Checking: f × 41 min (f = Daniel's estimate) | With the tool | Less than today | Half of today | Break-even |
|---|---|---|---|---|---|---|---|---|---|
| Follow-up, two nodules | 40–55 min | 0.5 min | 1.5 min | 2.5 min | 8.2–12.3 min (f = 0.20–0.30) | **≈ 13–17 min** | roughly 60–75% | 20–27.5 min | f < ~0.45 |

![Time](results/figures/time_before_after.png)

**Data files.** Daniel's breakdown → `results/daniel_steps.csv` (`timepoint`, `step`, `unit`, `minutes_low`, `minutes_high`, `source`; a `TOTAL` row holds his own per-scan total). Pilot runs → `results/time_log.csv` (`patient`, `timepoint`, `active_minutes`, `open_minutes`, `nodules_reviewed`, `who`, `note`; a note starting with "exclude" leaves the row out). `python results/make_figures.py` rebuilds the chart and prints the overhead, the estimate with Daniel's f (`F_DANIEL`), half of today, the break-even f and the breakdown-vs-log cross-check.

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
- **Timing is an estimate,** not a measurement of Daniel using the tool: the pilot measures the tool's mechanics only (7 scans, developer), and checking time comes from Daniel's own estimate (20–30%), which assumes the drafts are generally solid (section 4.1).
- **What we measured is the AI's first draft,** not the reviewer's confirmed values that go into the sheet.

## 8. Next steps

- **Measure checking time:** Daniel's own timed reviews with the tool on the lab's scans (hospital pilot below), to replace his 20–30% estimate with a measurement. Before that: his baseline breakdown and the full "Minutes on scan" column.
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
