# Engine API contract — v1 (Engine chat, 15 Oct 2026)

v0 was drafted by the App chat; the Engine chat accepts it with the changes marked **[v1]**.
The FastAPI server in `engine/api.py` implements exactly this; `engine/export_static.py` writes the same
GET tree as static files for demo mode. Research use only.

## Principles (unchanged from v0)
1. Heavy AI runs ahead of time (batch). The app only reads results. Only live call: `refine` (+ `process`, admin).
2. Every read is a plain GET of a `.json` or `.png` path → servable by FastAPI or as static files.
3. Coordinates = pixels of the PNG we serve: `x` = column, `y` = row, origin top-left. PNG = original voxel grid.
4. CORS open, no secret (public RIDER data only).
5. Errors: `{"error": {"code": "...", "message": "..."}}` with HTTP 4xx/5xx.
All paths start with `/api/v1`. `z` = 0-based slice index, **0 = most superior** (the engine flips internally).

## 1. Health — `GET /api/v1/health.json`
```json
{"status": "ok", "engine_version": "0.1.0", "mode": "live", "research_use_only": true,
 "models": {"detector": "TotalSegmentator lung_nodules (nnU-Net, BlueMind AI)",
            "lobes": "TotalSegmentator total 3mm", "segmenter": "same as detector + click-to-correct"},
 "refine_available": true}
```

## 2. Scan list — `GET /api/v1/scans.json`
As v0. `scan_id` = `RIDER-<id>_test` / `RIDER-<id>_retest`. **[v1]** `status`: `processed` | `queued` |
`processing` | `new` | `failed` (+ `error`). 59 scans (31 patients; 3 patients have only one expert-outlined scan).

## 3. Scan detail — `GET /api/v1/scans/{scan_id}/meta.json`
As v0 (`slices[]` with `z`, `slice_number` = DICOM InstanceNumber, `z_position_mm`; `windows`).

## 4. Slice images — `GET /api/v1/scans/{scan_id}/slices/{window}/{z}.png`
As v0. `lung` = L −600 / W 1500, `mediastinal` = L 40 / W 350. 8-bit grayscale, cols × rows.

## 5. Findings — `GET /api/v1/scans/{scan_id}/findings.json`
As v0, plus **[v1]** `research_use_only`, `match_summary` (`new_in_current`, `not_found_in_current`).
`409 not_processed` if the scan has no AI draft yet.

**Finding** = v0 fields, with:
- `finding_id`: `F1`, `F2`… largest volume first. Stable across refines; an added nodule gets the next number.
- `confidence` **[v1.1, 16 Oct]**: mean model probability over the drawn outline (0–1) = how much of the outline the model
  itself marked. (The max probability saturates at 1.0 for every finding, so it said nothing; it stays available as
  `detection_max_prob`.) Low = the outline was largely extended by the rim step → check the edges. `null` for user-added.
- `type_guess`: from density of the core (`Solid` ≥80% voxels > −300 HU, `Ground-glass` <10%, else `Part-solid`).
- **[v1] extra fields:** `source` (`ai` | `user_click`), `mean_diameter_mm`, `solid_component_mm` (Part-solid only),
  `mean_hu`, `n_slices`.
- Axes: long = longest edge-to-edge diameter on `key_slice_z` (slice where the long axis is largest);
  short = longest diameter perpendicular to it. Endpoints in `long_axis_px` / `short_axis_px` as `[[x,y],[x,y]]`.
- `volume_mm3` from the 3D outline (voxel count × voxel volume).
- `match` (follow-ups only): `{prior_scan_id, prior_finding_id, distance_mm, confidence, set_by}`; a suggestion.
- `flags`: `low_confidence` (confidence < 0.6), `below_4mm`, `touches_pleura` (>20% outside the lung mask),
  `possible_vessel` (thin and tall: z-extent > 2.5 × long axis and long axis < 10 mm).
- **[v1]** The engine returns only findings with long axis ≥ 4 mm (so `below_4mm` appears only after a refine).

## Demo hosting
Static demo (4 patients, both windows) on Amazon S3. **Base URL:** `https://lungmarker-demo-data-sd.s3.eu-north-1.amazonaws.com/api/v1`.

## 6. Refine (live only) — `POST /api/v1/scans/{scan_id}/refine`
Request exactly as v0: `finding_id` (null = add a missed nodule), `z`, `points` (`label` 1 = nodule, 0 = not),
optional `box_px` `[x0,y0,x1,y1]`, optional `polygon_px` (Daniel's outline on slice `z`, replaces that slice).
- label 1 points grow the outline to include that spot (model signal at a lower bar, else density growing);
  label 0 points cut that part away (watershed split); a box clips slice `z`; a polygon replaces slice `z`.
- Response: one Finding (all measurements recomputed) + **[v1]** `refine: {method, seconds}`.
- `404 nothing_found` when adding at a spot with no nodule; `422 empty_outline` if a correction removes everything.
- **Speed:** uses the stored model output, no model re-run → about 1–3 s on CPU.

## 7. **[v1] Process (admin, live only)** — `POST /api/v1/scans/{scan_id}/process`
Body `{"force": false}` → `{"status": "queued"|"processing"|"processed"}`. Runs the prior first if needed.
Finding nodules needs the model at full settings (full patch, 32-bit): ~30 s per scan on a Colab T4 GPU;
on CPU it needs ~8+ GB RAM (fits the free 16 GB HF Space, not a 6 GB box) and ~10–15 min per scan.
So the demo scans are processed ahead of time on Colab and loaded into the engine.

## 8. Not in the engine (app does it)
Axes from a dragged outline (or call `refine` with `polygon_px` to get them from the engine), mean diameter after
caliper edits, storing edits/approvals/timer, export.
