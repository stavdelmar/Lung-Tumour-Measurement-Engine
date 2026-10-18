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


def error_figure(noise_mm, noise_pct):
    """Per-tumour error of the SHIPPED outline (halo scaled to core size) vs the expert,
    with the expert's own repeat noise as a band. Source: halo_variants_found52.csv (52 found tumours)."""
    v = pd.read_csv(HERE / "halo_variants_found52.csv")
    long_err = v["scaled_dL"].sort_values().to_numpy()
    vol_err = v["scaled_dV%"].sort_values().to_numpy()
    n = len(v)
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
                   label=f"within expert repeat noise ({inside.sum()}/{n})")
        ax.scatter(x[~inside], err[~inside], s=28, color=ORANGE, zorder=3, edgecolor=SURFACE, linewidth=1.5,
                   label=f"outside ({(~inside).sum()}/{n})")
        ax.set_xticks([])
        ax.set_xlabel(f"{n} found tumours (28 patients), sorted by error")
        ax.set_ylabel(f"error ({unit})")
        ax.set_title(title, loc="left", fontweight="bold")
        ax.text(len(err) - 1, -band, f"band = expert repeat noise \u00b1{band:g} {unit}", ha="right", va="top",
                fontsize=9, color=INK2)
        ax.legend(loc="upper left", frameon=False, fontsize=9)
    fig.suptitle("AI first draft vs expert outline (RIDER, research use). Every draft is checked by the reviewer before it is recorded.",
                 x=0.01, ha="left", fontsize=10.5, color=INK2)
    fig.tight_layout()
    fig.savefig(OUT / "outline_error_vs_expert.png", dpi=200)
    plt.close(fig)
    a_l, a_v = np.abs(long_err), np.abs(vol_err)
    return float(np.median(a_l)), float(np.median(a_v)), int((a_l <= noise_mm).sum()), int((a_v <= noise_pct).sum()), n


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
    ax.set_title("How the outline method was chosen (exam setting): share within expert repeat noise", loc="left", fontweight="bold", fontsize=11)
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "outline_methods.png", dpi=200)
    plt.close(fig)


# Daniel's log, "Minutes on scan" (whole process). Last 5 rows: baseline 38, 49, 30, 37; follow-up 55.
# Update when the full column arrives.
BEFORE = {"Baseline": 39, "Follow-up": 55}
# Daniel (16 Oct): about two-thirds of incoming scans are follow-ups.
MIX = {"Baseline": 1 / 3, "Follow-up": 2 / 3}


def weighted(d):
    """Average minutes per incoming scan, using the lab's scan mix. None if a timepoint is missing."""
    if any(k not in d or pd.isna(d[k]) for k in MIX):
        return None
    return sum(MIX[k] * d[k] for k in MIX)


# Time-saved method (approved by Sam, 18 Oct): Daniel can't use the tool, so
#   before = Daniel's step-by-step breakdown of his manual review (falls back to his log totals above)
#   after  = Stav's timed runs in the tool (app timer, active minutes) on public RIDER scans
# Both are estimates and are labelled as such.
DANIEL_STEPS = HERE / "daniel_steps.csv"
# One row per step of the manual review: timepoint (Baseline|Follow-up), step, unit, minutes_low, minutes_high, source.
# Some steps are per nodule, so the per-scan "before" = Daniel's own TOTAL row (midpoint) when he gives one;
# otherwise the sum of per-scan step midpoints. Timepoints without a breakdown fall back to the log totals.
STAV_RUNS = HERE / "time_log.csv"
# One row per timed run in the tool: timepoint (Baseline|Follow-up), scan_id, active_minutes, open_minutes, who


def manual_steps():
    """Daniel's step breakdown as a table, or None if not received yet."""
    if not DANIEL_STEPS.exists():
        return None
    t = pd.read_csv(DANIEL_STEPS)
    t["minutes_mid"] = (t["minutes_low"] + t["minutes_high"]) / 2
    return t


def time_numbers():
    """Before / after minutes per timepoint + weighted average per incoming scan.

    Returns (before, after, sources): sources = {"before": "steps"|"log", "after": "stav"|None, "n_runs": {...}}.
    """
    before, after = dict(BEFORE), {}
    sources = {"before": "log", "after": None, "n_runs": {}}
    steps = manual_steps()
    if steps is not None:
        for tp, g in steps.groupby("timepoint"):
            tot = g[g["step"].str.upper() == "TOTAL"]
            before[tp] = float(tot["minutes_mid"].iloc[0]) if len(tot) else float(g["minutes_mid"].sum())
        sources["before"] = "steps"
        sources["steps_for"] = sorted(steps["timepoint"].unique())
    if STAV_RUNS.exists():
        t = pd.read_csv(STAV_RUNS)
        after = t.groupby("timepoint")["active_minutes"].median().to_dict()  # = exported "Minutes on scan"
        sources["after"] = "stav"
        sources["n_runs"] = t.groupby("timepoint").size().to_dict()
    before["Weighted"] = weighted(before)
    after["Weighted"] = weighted(after)
    return before, after, sources


BEFORE_LABEL = {"steps": "Before: Daniel's own estimate (follow-up) / log (baseline)", "log": "Before: Daniel's log (manual)"}
AFTER_LABEL = "After: Stav's timed runs in the tool (active min)"
TITLE = "Time per scan (ESTIMATE: Daniel's manual breakdown vs Stav's runs in the tool)"


def time_figure(before, after, sources):
    """Before vs after: baseline, follow-up, and the weighted average per incoming scan (the headline)."""
    groups = ["Baseline", "Follow-up", "Weighted"]
    labels = ["Baseline", "Follow-up", "Per incoming scan\n(weighted: \u2153 baseline, \u2154 follow-up)"]
    x = np.array([0, 1, 2.3])  # small gap before the headline group
    fig, ax = plt.subplots(figsize=(8.5, 4))
    for i, g in zip(x, groups):
        b = before[g]
        ax.bar(i - 0.19, b, 0.36, color=INK2, label=BEFORE_LABEL[sources["before"]] if g == "Baseline" else None)
        ax.text(i - 0.19, b + 1, f"{b:.0f}", ha="center", fontsize=10, fontweight="bold" if g == "Weighted" else None)
        a = after.get(g)
        if a is not None and not pd.isna(a):
            ax.bar(i + 0.19, a, 0.36, color=BLUE, label=AFTER_LABEL if g == "Baseline" else None)
            ax.text(i + 0.19, a + 1, f"{a:.0f}", ha="center", fontsize=10, fontweight="bold" if g == "Weighted" else None)
        else:
            ax.text(i + 0.19, 3, "pending", ha="center", fontsize=9, color=INK2)
        ax.plot([i - 0.4, i + 0.4], [b / 2, b / 2], ls="--", color=ORANGE, lw=1.2)
    ax.plot([], [], ls="--", color=ORANGE, label="Naomi's target: half")
    ax.axvline(1.65, color=GRID, lw=1)
    ax.set_xticks(x, labels)
    ax.set_ylabel("minutes per scan (whole process)")
    ax.set_title(TITLE, loc="left", fontweight="bold", fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_ylim(0, 80)
    fig.tight_layout()
    fig.savefig(OUT / "time_before_after.png", dpi=200)
    plt.close(fig)


def main():
    f = pd.read_csv(HERE / "finding_exam_all59.csv")
    m = pd.read_csv(HERE / "finding_exam_matching.csv")
    found = f[f.found == True]
    noise_mm, noise_pct, n_pairs = expert_noise()
    finding_figure(f)
    lm, vm, lin, vin, nq = error_figure(noise_mm, noise_pct)
    method_figure(found, noise_mm, noise_pct)
    before, after, sources = time_numbers()
    time_figure(before, after, sources)
    if sources["before"] == "steps":
        for k in sources.get("steps_for", []):
            gap = before[k] / BEFORE[k] - 1
            flag = "  <-- differs > 20%: report both in RESULTS 4.1" if abs(gap) > 0.2 else ""
            print(f"cross-check {k}: Daniel's breakdown {before[k]:.0f} min vs log {BEFORE[k]} min ({100 * gap:+.0f}%){flag}")
    print(f"time sources: before = {sources['before']}, after = {sources['after'] or 'none yet'}, runs = {sources['n_runs']}")
    ev = m[m.tumour_matched.notna()]
    print(f"expert repeat noise (n={n_pairs}): {noise_mm:.1f} mm, {noise_pct:.0f}%")
    print(f"found {len(found)}/{len(f)}; shipped outline: long err median {lm:.1f} mm ({lin}/{nq} within); "
          f"vol err median {vm:.0f}% ({vin}/{nq} within)")
    print(f"matching: {int((ev.tumour_matched == True).sum())}/{len(ev)} tumour pairs matched; "
          f"registration error median {m.registration_error_mm.median():.1f} mm")
    def fmt(d, k):
        v = d.get(k)
        return "pending" if v is None or pd.isna(v) else f"{v:.0f} min"
    for k in ["Baseline", "Follow-up", "Weighted"]:
        b, a = before[k], after.get(k)
        saved = "" if a is None or pd.isna(a) else f", saved {100 * (1 - a / b):.0f}%"
        print(f"time {k}: before {b:.1f} min, after {fmt(after, k)}{saved}, target {b / 2:.0f} min")
    print(f"figures written to {OUT}")


if __name__ == "__main__":
    main()
