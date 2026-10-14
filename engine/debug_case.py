"""Save a picture of one case: expert (green), lung mask from AI (blue), tool (orange)."""
import sys, numpy as np, SimpleITK as sitk, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from data import load_case
from classic import box_from_expert, ai_lung_field, segment_box_v2
data, pid, scan, out = sys.argv[1:5]
ct, m = load_case(data, pid, scan); a = sitk.GetArrayFromImage(ct); sp = ct.GetSpacing()
z, box = box_from_expert(m)
lung = ai_lung_field(ct, z, z + 1)[0]
y0, y1, x0, x1 = box; pad = 70
Y0, Y1, X0, X1 = max(0, y0 - pad), y1 + pad, max(0, x0 - pad), x1 + pad
fig, ax = plt.subplots(1, 2, figsize=(10, 5))
ax[0].imshow(np.clip(a[z, Y0:Y1, X0:X1], -1000, 400), cmap="gray"); ax[0].set_title(f"{pid} {scan} slice {z}")
ax[1].imshow(np.clip(a[z, Y0:Y1, X0:X1], -1000, 400), cmap="gray")
ax[1].contour(m[z, Y0:Y1, X0:X1], [0.5], colors="lime")
ax[1].contour(lung[Y0:Y1, X0:X1], [0.5], colors="deepskyblue")
ax[1].add_patch(plt.Rectangle((x0 - X0, y0 - Y0), x1 - x0, y1 - y0, fill=False, ec="yellow", ls="--"))
ax[1].set_title("green expert · blue AI lung · yellow box")
for x in ax: x.axis("off")
plt.tight_layout(); plt.savefig(out, dpi=70)
