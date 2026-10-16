LungMarker demo data (static engine output)
==========================================

RESEARCH USE ONLY. NOT FOR CLINICAL USE.
The nodules, outlines, measurements, lobes and test/retest matches in these files are AI DRAFTS made
for a research workflow demo. They are not clinical results and have not been reviewed by a clinician.

What this is
- A read-only copy of the LungMarker engine API (contract v1): api/v1/health.json, scans.json,
  scans/<scan_id>/meta.json, findings.json, slices/<lung|mediastinal>/<z>.png
- 4 patients x 2 scans (test = "Baseline", retest 15 minutes later = "Follow-up 1"; the retest is a
  repeat scan, so it tests matching, not growth).
- AI drafts: TotalSegmentator lung_nodules + lobes (Apache-2.0) with LungMarker's outline and
  measurement steps.

Data credit
- CT scans: RIDER Lung CT collection, The Cancer Imaging Archive (TCIA).
  Zhao B, Schwartz LH, Kris MG. Data From RIDER Lung CT. The Cancer Imaging Archive (2015).
  https://doi.org/10.7937/K9/TCIA.2015.U1X8A5NR
- TCIA: Clark K, et al. The Cancer Imaging Archive (TCIA): Maintaining and Operating a Public
  Information Repository. J Digit Imaging 26(6):1045-1057 (2013).
- Images are shown as 8-bit PNG slices (lung and mediastinal windows) derived from the original DICOM.
