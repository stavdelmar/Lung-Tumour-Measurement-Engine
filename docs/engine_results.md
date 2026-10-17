# Engine results: finding exam on all 59 RIDER scans (Colab T4, 15–16 Oct 2026)

Engine chat. Research use only. Raw data: engine repo `results/finding_exam_all59.csv`, `results/finding_exam_matching.csv`, summary `results/finding_exam_summary.txt` (script `engine/summarize_exam.py`).

**Setup.** The whole pipeline runs with no hint: lobes, then nodule finding (TotalSegmentator `lung_nodules`, full settings), then outline and measurement, then test↔retest matching. The comparison is with the expert outline of the one marked tumour per scan, measured the same way (Daniel's method). Quality bar = the expert's own test-retest noise: median 2.3 mm diameter, 17% volume.

## Finding
- **Expert tumour found in 52 / 59 scans (88%).** Solid 48 / 53, part-solid 4 / 6. RIDER has no pure ground-glass tumours.
- **7 misses in 4 patients**, all with model probability ~0 inside the tumour, so these are model limits, not settings:
  - RIDER-1286684383: missed in both scans. 39–52 mm, lower-left lobe, next to the hilum, irregular, mixed with vessels.
  - RIDER-1760553574: missed in both scans. 25–32 mm, part-solid, perihilar.
  - RIDER-2073083717: missed in both scans. 29–34 mm, upper-right lobe, lying flat against the mediastinum (79% outside the lung mask).
  - RIDER-1801720707: missed in TEST only (found in RETEST). 14 mm, near the hilum.
- **Pattern:** the model finds nodules surrounded by lung; it misses **central tumours touching the hilum or mediastinum**, even big ones. Daniel must still check the hilum and mediastinal borders, and add a missed tumour by hand.
- **Other candidates:** median 3 per scan (range 0–29; one patient with many small nodules has 28–29). **82% of candidates are found in both the test and the retest scan**, taken 15 minutes apart. This is a proxy only, because RIDER doesn't mark other nodules. About 1 in 5 candidates appears in only one scan: either a false alarm or a miss in the other scan.

> **One line for the lab:** for nodules under 8 mm, diameters are stable (0.5 mm), volume is approximate (~30%).

## Outline and measurements (52 found tumours)
| Outline method | Dice median | Long axis error, median (signed) | Long axis within 2.3 mm | Volume error, median (signed) | Volume within 17% | Too long / of which vessel tail |
|---|---|---|---|---|---|---|
| Model outline only | 0.77 | 6.0 mm (−6.0) | 12% | 26% (−26%) | 29% | 1 / 0 |
| **Model + halo (chosen)** | 0.77 | **2.8 mm (+0.8)** | **38%** | **20% (+5%)** | **48%** | 17 / 4 |
| MedSAM 2, box from the detection | 0.73 | 10.7 mm (+5.8) | 23% | 48% (+30%) | 10% | 31 / 2 |

- The model alone draws too tight: it leaves out the faint rim. The halo fixes the bias, but each single tumour still varies around the expert's value. Only about half are within the expert's own repeat noise, **so Daniel's review of the outline stays essential**. This matches his rule: volume is recorded only after he confirms the outline.
- MedSAM 2 with an expert box was good earlier (Dice 0.84). With a box from the detection (enlarged 25%) it overshoots. Not used.
- **Vessel tails:** 17 halo long axes are too long; in 4 of them a vessel tail is the cause. The other too-long cases come from a rim that is a bit too wide.
- **Lobe agrees with the lobe of the expert outline in 100%.** Type agrees in 98%, but both use the same density rule, so this is not independent.
- Key slice within 2 slices of the expert's widest slice: 62%. "Largest long axis" and "largest area" often pick different, near-equal slices.
- Type is judged on the model's core, not the halo rim (16 Oct).

## Re-measure with a smarter halo width (16 Oct evening; NOT the default, see 17 Oct check below)
The exam's halo grows the outline up to a **fixed 4 mm** around the model's core. That inflated the smaller tumours (+2.6 mm, +25% volume) and pushed tiny specks over the 4 mm reporting line. This morning's fix (width = 25% of the core's size) helped most small tumours but **failed badly on 4 faint 13–20 mm tumours where the model marked only a 4–7 mm piece** (long axis 7–12 mm too short). Tried, on all 52 found tumours:

| Halo width | Long axis within 2.3 mm | Long axis error, median (signed) | > 5 mm off | Volume within 17% | Volume error, median (signed) | Dice | Other candidates ≥ 4 mm (52 scans) |
|---|---|---|---|---|---|---|---|
| Fixed 4 mm (exam) | 19 / 52 | 3.1 mm (+0.8) | 15 | 23 / 52 | 24% (+6%) | 0.76 | 366 |
| Scaled to core size (16 Oct morning) | 20 / 52 | 3.0 mm (−0.3) | 19 | 27 / 52 | 14% (0%) | 0.76 | 272 |
| Image-driven for every nodule | 24 / 52 | 2.5 mm (−1.6) | 16 | 30 / 52 | 13% (−4%) | 0.79 | 358 |
| **Hybrid (opt-in)** | **24 / 52** | **2.4 mm (−0.4)** | **15** | 27 / 52 | 14% (0%) | 0.78 | **272** |

- **Hybrid rule** (`outline.halo_adaptive`, `ENGINE_OUTLINE=hybrid`): model core < 16 mm → the image decides the width (grow in 1 mm steps up to 4 mm, stop when less than half of the next shell is tissue); core ≥ 16 mm → 4 mm as in the exam (the image-driven stop shortened large tumours by ~2 mm); model specks < 3.5 mm → 1 mm (otherwise a vessel can grow a speck into a false 11 mm "finding").
- **11 tumours < 21 mm:** long axis within 2.3 mm in **10 / 11** (fixed 4 mm: 5, scaled: 6), none more than 5 mm off (scaled: 4). Volume still tends to come out ~14% small on these, so the outline check stays.
- **41 tumours ≥ 21 mm:** identical to the exam setting.
- **Small nodules without an expert outline (repeatability):** same nodule in test vs retest (15 min apart), 22 patients, 84 paired nodules < 16 mm (median 7 mm). **Long axis is steady: median difference 0.5 mm** (72 / 84 within 2.3 mm), with every halo width. **Volume of small nodules is not:** median 28% difference between the two scans (< 8 mm nodules: 32%). That is the voxel limit of a 5–8 mm nodule, not the halo (every width gives 18–33%). → For nodules under ~8 mm, trust the diameters; treat the volume as a rough figure.
- **Caution:** the rule was chosen while looking at these same scans, so these numbers are somewhat optimistic. LNDb (other scanners, radiologist outlines, small and ground-glass nodules) is the independent test.
- **17 Oct check on the demo patients → hybrid NOT made the default.** Rebuilding the 4 demo patients showed what the 52 expert tumours can't: the other small nodules (no expert outline).
  - A 5 mm nodule next to the spine (RIDER-1225316081 retest F2) grew along branching vessels to **12.9 mm** (confidence 0.11).
  - Small nodules touching the pleura grew along the chest wall (RIDER-1532432635 F5: 4.2 → 10.3 mm). This part is fixed: only lung voxels now count when deciding to keep growing, with no change on the 11 small tumours.
  - Test vs retest got less stable on the demo's paired nodules: one 15 mm nodule measured 11.4 mm vs 18.2 mm (morning rule: 15.1 vs 13.9).
  - Counting only faint (ground-glass-like) tissue as rim stops the vessel growth, but breaks the faint tumours again (long axis 7–8 mm short).
  - **Conclusion:** the same ambiguity as the central flag. The model marks only a small core in two different cases: a faint tumour that is much bigger (grow!), or a small nodule touching vessels (don't grow!). No simple image rule tells them apart.
  - **Default = the morning rule** (width scaled to core size; the same as the S3 demo, which stays as is). Its known weak spot is the faint small tumour drawn too small; since 17 Oct the `faint_rim` warning flags it (see below). **The hybrid stays opt-in until LNDb**, whose radiologist outlines of small nodules are exactly the missing ground truth.
- Raw data: `results/halo_variants_found52.csv`, `results/small_nodule_repeatability.csv`, `results/remeasure_small.csv`; scripts `engine/experiments/remeasure_variants.py`, `small_repeat.py`.

## Warning for outlines that may be too small (17 Oct) → shipped
The default outline can come out far too small when the model marks only a small core of a fainter, bigger tumour, and nothing used to warn about it. **New flag `faint_rim`:** for each nodule the engine also tries the image-driven width (the opt-in rule). If that would make the long axis **≥ 4 mm longer**, the finding gets `faint_rim` **and** `low_confidence`, so the app shows "AI unsure about the edges". The outline itself is unchanged; the value is in `faint_rim_growth_mm`.
- **52 expert tumours:** catches **all 4** small tumours the default draws 7–12 mm too small; fires on none of the others. It does **not** catch the 14 large tumours (> 20 mm) drawn too small for other reasons (large cores always get the full 4 mm width).
- **All 322 candidates in the 52 scans:** fires on **38 (12%)**; 8 of them were already `low_confidence`. Together, "AI unsure about the edges" now shows on **81 / 322 nodules (25%)**, up from 51 (16%). Flagged at least once in 22 of 52 scans. Threshold 3 mm would flag 16% (also catches all 4); 4 mm chosen for less noise.
- **Demo:** adds the warning to 2 findings (RIDER-1225316081 retest F2, the 5.6 mm nodule beside branching vessels; RIDER-1332496276 retest F2, 13.9 mm). No outline, size or ID changes.
- **Honest limits:** tuned on the same 52 tumours (only 4 positives), so the true catch rate is uncertain; some warnings will be vessels next to a small nodule rather than a faint rim (still a fair "check the edges"). Raw data: `results/faint_flag_candidates.csv`.

## Matching (test ↔ retest)
- **The marked tumour was paired correctly in 24 / 24 pairs** where it was found in both scans.
- Registration error at the tumour: median 2.9 mm, max 13.9 mm (one patient, still matched).
- Lining up the lungs takes ~40 s per pair on CPU.

## Speed
- Colab T4: nodule finding median 49 s per scan, lobes 5 s, measuring ~1 s.
- Free CPU: needs > 6 GB RAM at full settings; not run here.

## Central check: a "check here" flag for the missed central tumours (16 Oct, ~2 h, NOT kept)
**Result: no simple rule separates the missed central tumours from normal hilar vessels.** The best setting flags 4 of the 7 missed scans, but also adds about 2 false flags to every other scan (107 on the 52 scans where the tumour was found; 49 of the 52 get at least one). That would train Daniel to ignore the flag, so it is not shipped. Daniel says central tumours are "common enough" in their cohort, so this stays the most important known gap.

**Why it is hard (what the data showed):**
- **3 of the 4 missed patients' tumours lie INSIDE the lung mask** (71%, 100% and 100% of the tumour), not outside it. Only RIDER-2073083717 is pushed out of the mask (79% outside), and its dent is wider than a closing can fill.
- **They are not compact lumps.** 25–52 mm long, but only 4.6–7.3 ml and irregular, growing along vessels and airways. A test that removes thin, tube-like structures removes them too (less than 30% of each tumour survives a 6 mm-wide filter).

| Idea tried | Missed scans flagged (of 7) | False flags on the other scans | Verdict |
|---|---|---|---|
| Dent in the lung outline (close each lung per slice, soft tissue in the dent), as in engine v5 | 0 of 4 dev scans | 0 | Misses: 3 of 4 tumours are inside the lung mask |
| Soft tissue that no TotalSegmentator organ explains (heart, aorta, veins, airway, bone) | 0 of 4 dev scans | ~1–4 per scan on 7 dev scans | The 3 mm model labels 65% of RIDER-2073083717's tumour as an organ |
| Dense blobs inside the lungs, thick rather than tube-like, not covered by a finding (all 59 scans) | **4** (RIDER-1286684383 and RIDER-1760553574, both scans) | **107 on 52 scans** (49 of 52 flagged) | Too noisy |
| Same, stricter (thicker blobs only) | 2 → 0 | 102 → 42 → 19 | Catches nothing once the noise is acceptable |

- Even where it flags the tumour, the flag is not the largest one on that scan (hilar vessels are bigger), so ranking doesn't help.
- What would likely work, but doesn't fit this week: a second model trained on lung **cancer** outlines (e.g. the Medical Segmentation Decathlon lung-tumour task, which has central tumours), used only where it disagrees with the nodule model. Needs a GPU run plus its own exam.
- **What the product does instead:** the review screen tells Daniel what the AI is weak at ("central tumours touching the hilum or mediastinum can be missed; check there") and makes adding a missed tumour quick (4 clicks).
- Code and raw numbers: engine repo `engine/experiments/` (3 scripts + README) and `results/central_check_blob_all59.csv`.

## Honest limits to say out loud
- RIDER marks one tumour per scan, so false alarms can only be estimated (the 82% repeatability).
- No ground-glass tumours in RIDER. LNDb (27 GGO + 46 part-solid nodules ≥ 4 mm) is planned after Saturday.
- The detector was partly trained on LIDC-IDRI, not on RIDER. Good: RIDER is unseen data.
- Measurement accuracy per tumour is below the expert's repeat precision; the tool drafts, Daniel confirms.
- Volume of nodules under ~8 mm varies ~30% between two scans 15 minutes apart (diameters vary ~0.5 mm), so small-nodule volumes are rough.
- Central tumours touching the hilum or mediastinum can be missed (7 / 59 scans), and a simple "check here" flag could not catch them without flooding every scan with false flags.
