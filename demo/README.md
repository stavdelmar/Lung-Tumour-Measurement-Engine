# Static demo of the engine API ("demo mode")

Read-only copy of the engine API (contract v1, `docs/engine_api.md`) for 3 RIDER patients (test = Baseline,
retest = Follow-up 1, 15 minutes apart), lung window only. Base URL for the app:
`https://raw.githubusercontent.com/stavdelmar/Lung-Tumour-Measurement-Tool/main/demo`
(all paths start with `/api/v1`). `refine` is not available here (health.json says `refine_available: false`).

AI drafts come from the Colab exam (TotalSegmentator lung_nodules + size-scaled halo outline), built with
`python -m engine.build_demo`. Public RIDER data (CC BY 3.0, TCIA). **Research use only.**
