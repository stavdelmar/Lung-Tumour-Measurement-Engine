"""Make the result figures for RESULTS.md and the presentation.

Re-run whenever the engine results change:
    python results/make_figures.py
Reads results/*.csv, writes results/figures/*.png and prints the headline numbers.
Research use only.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)

# Reference palette (dataviz skill, light mode)
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
BAND = "#cde2fb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
})


def expert_noise():
    """Expert's own test-retest difference (manual outlines, same patient 15 min apart)."""
    b = pd.read_csv(HERE / "expert_baseline.csv")
    m = b[b.outline == "MANUAL"].pivot(index="patient", columns="scan",
                                        values=["longest_diameter_mm", "volume_ml"]).dropna()
    d = (m["longest_diameter_mm"]["TEST"] - m["longest_diameter_mm"]["RETEST"]).abs()
    v = (m["volume_ml"]["TEST"] - m["volume_ml"]["RETEST"]).abs() / m["volume_ml"][["TEST", "RETEST"]].mean(axis=1)
    return round(d.median(), 1), round(v.median() * 100), len(m)  # rounded, as quoted in the write-up


def finding_figure(f):
    """Found vs missed, split by tumour type. Misses are all central."""
    found = f[f.found == True]
    missed = f[f.found != True]
    fig, ax = plt.subplots(figsize=(8, 2.6))
    ax.barh([0], [len(found)], color=BLUE, height=0.5)
    ax.barh([0], [len(missed)], left=[len(found) + 0.4], color=ORANGE, height=0.5)
    ax.text(len(found) / 2, 0, f"Found  {len(found)}", ha="center", va="center", color="white", fontweight="bold")
    ax.text(len(found) + 0.4 + len(missed) / 2, 0, f"Missed {len(missed)}", ha="center", va="center",
            color="white", fontweight="bold", fontsize=9)
    ax.set_xlim(0, len(f) + 1)
    ax.set_yticks([])
    ax.set_xlabel("RIDER scans with an expert-marked tumour")
    ax.grid(False)
    ax.set_title(f"AI found the expert's tumour in {len(found)} of {len(f)} scans "
                 f"({100 * len(found) / len(f):.0f}%)", loc="left", fontweight="bold")
    ax.annotate("all 7 misses: central tumours\ntouching hilum / mediastinum",
                xy=(len(found) + 4, 0.28), xytext=(len(found) - 18, 0.75),
                fontsize=9, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    ax.set_ylim(-0.5, 1.1)
    fig.tight_layout()
    fig.savefig(OUT / "finding_found_vs_missed.png", dpi=200)
    plt.close(fig)


def error_figure(found, noise_mm, noise_pct):
    """Per-tumour error vs the expert, with the expert's own repeat noise as a band."""
    long_err = (found.halo_long - found.expert_long).sort_values().to_numpy()
    vol_err = (100 * (found.halo_vol - found.expert_vol) / found.expert_vol).sort_values().to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, err, band, unit, title in [
        (axes[0], long_err, noise_mm, "mm", "Long axis: AI draft minus expert"),
        (axes[1], vol_err, noise_pct, "%", "Volume: AI draft vs expert"),
    ]:
        x = np.arange(len(err))
        inside = np.abs(err) <= band
        ax.axhspan(-band, band, color=BAND, zorder=0)
        ax.axhline(0, color=INK2, lw=0.8)
        ax.scatter(x[inside], err[inside], s=28, color=BLUE, zorder=3, edgecolor=SURFACE, linewidth=1.5,
                   label=f"within expert repeat noise ({inside.sum()}/{len(err)})")
        ax.scatter(x[~inside], err[~inside], s=28, color=ORANGE, zorder=3, edgecolor=SURFACE, linewidth=1.5,
                   label=f"outside ({(~inside).sum()}/{len(err)})")
        ax.set_xticks([])
        ax.set_xlabel("52 found tumours, sorted by error")
        ax.set_ylabel(f"error ({unit})")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.text(len(err) - 1, -band, f"band = expert repeat noise ±{band:g} {unit}", ha="right", va="top",
                fontsize=9, color=INK2)
        ax.legend(loc="upper left", frameon=False, fontsize=9)
    fig.suptitle("The AI draft is close, but not yet as precise as the expert → Daniel confirms every outline",
                 x=0.01, ha="left", fontsize=11, color=INK2)
    fig.tight_layout()
    fig.savefig(OUT / "outline_error_vs_expert.png", dpi=200)
    plt.close(fig)
    return float(np.median(np.abs(long_err))), float(np.median(np.abs(vol_err))), \
        float((np.abs(long_err) <= noise_mm).mean()), float((np.abs(vol_err) <= noise_pct).mean())


def method_figure(found, noise_mm, noise_pct):
    """Share of tumours within expert noise, per outline method tried."""
    methods = [("Model only", "tool"), ("Model + halo\n(chosen)", "halo"), ("MedSAM 2\n(box from detection)", "medsam2")]
    long_ok, vol_ok = [], []
    for _, p in methods:
        long_ok.append(100 * ((found[f"{p}_long"] - found.expert_long).abs() <= noise_mm).mean())
        vol_ok.append(100 * ((found[f"{p}_vol"] - found.expert_vol).abs() / found.expert_vol * 100 <= noise_pct).mean())
    x = np.arange(len(methods))
    w = 0.36
    fig, ax = plt.subplots(figsize=(8, 3.8))
    b1 = ax.bar(x - w / 2 - 0.01, long_ok, w, color=BLUE, label=f"long axis within ±{noise_mm:.1f} mm")
    b2 = ax.bar(x + w / 2 + 0.01, vol_ok, w, color=AQUA, label=f"volume within ±{noise_pct:.0f}%")
    for bars in (b1, b2):
        for r in bars:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 1, f"{r.get_height():.0f}%",
                    ha="center", va="bottom", fontsize=9, color=INK2)
    ax.set_xticks(x, [m for m, _ in methods])
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of found tumours")
    ax.set_title("Outline methods tried: share within the expert's own repeat noise", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "outline_methods.png", dpi=200)
    plt.close(fig)


def time_figure():
    """Before vs after minutes per scan. 'Before' = Daniel's log; 'after' = app timer (results/time_log.csv)."""
    before = {"Baseline": 39, "Follow-up": 55}  # Daniel's log, last 5 rows (update when full column arrives)
    log = HERE / "time_log.csv"  # columns: timepoint (Baseline|Follow-up), total_minutes, active_minutes, who
    after = {}
    if log.exists():
        t = pd.read_csv(log)
        after = t.groupby("timepoint")["total_minutes"].median().to_dict()
    fig, ax = plt.subplots(figsize=(7, 3.6))
    x = np.arange(len(before))
    ax.bar(x - 0.19, list(before.values()), 0.36, color=INK2, label="Before (Daniel's log)")
    for i, v in enumerate(before.values()):
        ax.text(i - 0.19, v + 1, f"{v}", ha="center", fontsize=10)
    if after:
        vals = [after.get(k, np.nan) for k in before]
        ax.bar(x + 0.19, vals, 0.36, color=BLUE, label="With LungMarker (app timer)")
        for i, v in enumerate(vals):
            if not np.isnan(v):
                ax.text(i + 0.19, v + 1, f"{v:.0f}", ha="center", fontsize=10)
    else:
        for i in x:
            ax.text(i + 0.19, 3, "pending\npilot", ha="center", fontsize=9, color=INK2)
    halved = [v / 2 for v in before.values()]
    for i, h in enumerate(halved):
        ax.plot([i - 0.4, i + 0.4], [h, h], ls="--", color=ORANGE, lw=1.2)
    ax.plot([], [], ls="--", color=ORANGE, label="Naomi's target: half")
    ax.set_xticks(x, list(before.keys()))
    ax.set_ylabel("minutes per scan (whole process)")
    ax.set_title("Time per scan", loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_ylim(0, 70)
    fig.tight_layout()
    fig.savefig(OUT / "time_before_after.png", dpi=200)
    plt.close(fig)


def main():
    f = pd.read_csv(HERE / "finding_exam_all59.csv")
    m = pd.read_csv(HERE / "finding_exam_matching.csv")
    found = f[f.found == True]
    noise_mm, noise_pct, n_pairs = expert_noise()
    finding_figure(f)
    lm, vm, lin, vin = error_figure(found, noise_mm, noise_pct)
    method_figure(found, noise_mm, noise_pct)
    time_figure()
    ev = m[m.tumour_matched.notna()]
    print(f"expert repeat noise (n={n_pairs}): {noise_mm:.1f} mm, {noise_pct:.0f}%")
    print(f"found {len(found)}/{len(f)}; long err median {lm:.1f} mm ({100*lin:.0f}% within); "
          f"vol err median {vm:.0f}% ({100*vin:.0f}% within)")
    print(f"matching: {int((ev.tumour_matched == True).sum())}/{len(ev)} tumour pairs matched; "
          f"registration error median {m.registration_error_mm.median():.1f} mm")
    print(f"figures written to {OUT}")


if __name__ == "__main__":
    main()
