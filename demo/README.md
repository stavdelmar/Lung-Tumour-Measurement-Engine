# Static demo of the engine API ("demo mode")

The demo data is hosted on Amazon S3 (not in this repo, to keep the repo small):

**Base URL for the app:** `https://lungmarker-demo-data-sd.s3.eu-north-1.amazonaws.com/api/v1`

Contents: 4 RIDER patients (test = Baseline, retest = Follow-up 1), lung + mediastinal windows, contract v1
(`docs/engine_api.md`). `refine` is not available (static files; `health.json` says `refine_available: false`).
Rebuild it with `python -m engine.build_demo NII CACHE STATE OUT <patients>` from the Colab AI cache.
Credits and research-use statement: `DATA_README.txt` (also at the bucket root as `README.txt`).
