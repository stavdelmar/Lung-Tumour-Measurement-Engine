# Experiments (not used by the engine)

**Central-mass "check here" flag (16 Oct, ~2 h, NOT kept).** Goal: flag the regions where the nodule model
misses central tumours (7 of 59 RIDER scans, 4 patients). Three ideas tried; none separates those
tumours from normal hilar vessels. Details and numbers: `claude/engine-results.md` (project), section
"Central check".

| file | idea | result |
|---|---|---|
| `central_dent_check.py` | dent in the lung outline (closing per slice), soft tissue in the dent | 0 / 4 missed tumours flagged (11 dev scans): 3 of 4 lie INSIDE the lung mask |
| `central_anatomy_check.py` | soft tissue not explained by any TotalSegmentator organ | 0 / 4; the 3 mm model labels 65% of one tumour as an organ, the others are inside the lung |
| `central_blob_check.py` | dense blobs inside the lungs that survive a ball opening (thick, not tube-like) | best setting: 4 / 7 missed scans flagged, but 107 false flags on the 52 other scans (49 of 52 flagged) → too noisy. `results/central_check_blob_all59.csv` |
