"""Central-mass check v3: dense COMPACT blobs inside the lungs that no AI finding covers.
Vessels are thin tubes; a mass is a thick lump. An opening with a ball of radius R removes anything
thinner than 2R. Run on a 1.5 mm grid. Prints hits/flags for several R and size limits."""
import os, sys, time
import numpy as np, SimpleITK as sitk
from scipy import ndimage as ndi

U = os.path.expanduser("~/mnt/lung-tumour-project/work.nosync/nii")
C = sys.argv[1]           # cache dir with <sid>.npz (lobes, nod)
OUTCSV = sys.argv[2]
sids = sys.argv[3:]
G = 1.5


def ball(r_mm):
    r = int(round(r_mm / G))
    z, y, x = np.ogrid[-r:r + 1, -r:r + 1, -r:r + 1]
    return x * x + y * y + z * z <= r * r


def to_grid(img, arr=None, nn=False):
    if arr is not None:
        im = sitk.GetImageFromArray(arr); im.CopyInformation(img); img = im
    size = [int(round(s * p / G)) for s, p in zip(img.GetSize(), img.GetSpacing())]
    r = sitk.Resample(img, size, sitk.Transform(), sitk.sitkNearestNeighbor if nn else sitk.sitkLinear,
                      img.GetOrigin(), [G] * 3, img.GetDirection(), 0 if nn else -1024)
    return sitk.GetArrayFromImage(r)


rows = []
done = set()
if os.path.exists(OUTCSV):
    import csv; done = {r["scan"] for r in csv.DictReader(open(OUTCSV))}
f = open(OUTCSV, "a")
if not done:
    f.write("scan,R_mm,min_ml,n_flags,hit,flag_ml_list\n")
T0 = time.time()
for sid in sids:
    if sid in done:
        continue
    if time.time() - T0 > 150:
        print('TIME'); break
    t = time.time()
    z = np.load(f"{C}/{sid}.npz")
    img = sitk.ReadImage(f"{U}/{sid}_ct.nii.gz")
    hu = to_grid(img)
    lobes = to_grid(img, z["lobes"].astype(np.uint8), nn=True)
    nod = to_grid(img, z["nod"].astype(np.uint8), nn=True) > 0
    ex = to_grid(img, sitk.GetArrayFromImage(sitk.ReadImage(f"{U}/{sid}_expert.nii.gz")).astype(np.uint8), nn=True) > 0
    lung = ndi.binary_fill_holes(lobes > 0)      # solid masses inside a lobe can be holes in the mask
    lungd = ndi.binary_dilation(lung, iterations=2)
    dense = (hu > -100) & lungd
    nodd = ndi.binary_dilation(nod, iterations=3)
    exd = ndi.binary_dilation(ex, iterations=2)
    for R in (2, 3):
        op = ndi.binary_opening(dense, ball(R))
        # keep what lies mostly inside the lung (chest wall / heart touch the dilated mask only at the rim)
        lab, n = ndi.label(op)
        for min_ml in (1, 2, 4):
            flags = []
            hit = False
            for i, s in enumerate(ndi.find_objects(lab), 1):
                m = lab[s] == i
                ml = m.sum() * G ** 3 / 1000
                if ml < min_ml:
                    continue
                if (lung[s] & m).sum() < 0.5 * m.sum():      # mostly outside the lungs: heart, wall
                    continue
                if (nodd[s] & m).sum() > 0.3 * m.sum():      # already an AI finding
                    continue
                h = bool((exd[s] & m).any())
                flags.append(round(ml, 1) if not h else -round(ml, 1))
                hit |= h
            f.write(f"{sid},{R},{min_ml},{len(flags)},{hit},\"{flags}\"\n")
    f.flush()
    print(sid, f"{time.time()-t:.0f}s", flush=True)
