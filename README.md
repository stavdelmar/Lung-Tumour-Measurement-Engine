# Lung Tumour Measurement Tool

Home assignment, Forward Deployed Engineer (Base44), Stav Delmar.
**Research use only. No clinical claims.**

The tool cuts the time a researcher spends outlining and measuring lung tumours on CT:
the researcher draws one box around the tumour on one slice, the tool outlines it in 3D and
measures longest diameter and volume, and the researcher checks, edits and approves.

> Work in progress: this README will gain the link to the running tool and full run instructions.

## What is in the repo

| Path | What it is |
| --- | --- |
| `engine/` | Our engine (v5): AI lung mask (lungmask R231) + box-prompted 3D outline, and the evaluation scripts |
| `notebooks/medsam2_vs_our_engine.ipynb` | Colab notebook that runs MedSAM 2 on the same exam |
| `results/` | Raw results: expert baseline, engine on all 59 scans, in-house tool reference |

## How we test

Every method gets the same prompt: a box around the tumour on the expert's widest slice of each of the
59 expert-outlined RIDER scans. The tool's 3D outline is compared with the expert's (Dice overlap,
volume error, diameter error). The quality bar is the expert's own variation between two scans taken
15 minutes apart: 2.3 mm diameter, 17% volume (median).

## Data and citations

- RIDER Lung CT: Zhao, B. et al. (2015). *Coffee-break lung CT collection with scan images reconstructed at multiple imaging parameters.* The Cancer Imaging Archive. https://doi.org/10.7937/k9/tcia.2015.u1x8a5nr
- RIDER-LungCT-Seg: Wee, L., Aerts, H., Kalendralis, P., & Dekker, A. (2020). *RIDER Lung CT Segmentation Labels from: Decoding tumour phenotype by noninvasive imaging using a quantitative radiomics approach.* The Cancer Imaging Archive. https://doi.org/10.7937/tcia.2020.jit9grk8
- lungmask: Hofmanninger, J. et al. (2020). https://github.com/JoHof/lungmask
- MedSAM 2: Ma, J. et al. (2025). *MedSAM2: Segment Anything in 3D Medical Images and Videos.* arXiv:2504.03600. Apache-2.0.
