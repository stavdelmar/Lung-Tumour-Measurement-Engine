import numpy as np

def dice(a, b):
    s = a.sum() + b.sum()
    return 2 * np.logical_and(a, b).sum() / s if s else 1.0

def volume_ml(m, sp):
    return m.sum() * sp[0] * sp[1] * sp[2] / 1000

def longest_diameter_mm(m, sp):
    best = 0.0
    rng = np.random.default_rng(0)
    for z in np.nonzero(m.any(axis=(1, 2)))[0]:
        ys, xs = np.nonzero(m[z])
        pts = np.stack([ys * sp[1], xs * sp[0]], 1)
        if len(pts) > 2500:
            pts = pts[rng.choice(len(pts), 2500, replace=False)]
        d = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1)).max()
        best = max(best, float(d))
    return best
