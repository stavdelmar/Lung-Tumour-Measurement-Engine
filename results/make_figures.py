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


# Time-saved method (approved by Sam, 18 Oct; everything is an ESTIMATE):
#   before        = Daniel's step-by-step account of his manual review (results/daniel_steps.csv),
#                   timepoints without one fall back to his log totals above
#   tool overhead = Stav's timed runs in the tool (results/time_log.csv): the tool's mechanics only
#                   (opening, confirming, editing, matching, export) by a developer, NOT a reader's judgement
#   with the tool = overhead + the reader's judgement time on each step the tool shortens -> NOT measured,
#                   so it is reported as a range, never as one number or a % saved.
DANIEL_STEPS = HERE / "daniel_steps.csv"
STAV_RUNS = HERE / "time_log.csv"
# time_log.csv: patient, timepoint (Baseline | Follow-up 1), active_minutes, open_minutes, nodules_reviewed, who, note
# Rows whose note starts with "exclude" are left out (e.g. scan left open while doing something else).


def manual_steps():
    """Daniel's step breakdown as a table, or None if not received yet."""
    if not DANIEL_STEPS.exists():
        return None
    t = pd.read_csv(DANIEL_STEPS)
    t["minutes_mid"] = (t["minutes_low"] + t["minutes_high"]) / 2
    return t


def overhead_runs():
    """Stav's pilot runs (included rows only), timepoint normalised to Baseline / Follow-up."""
    if not STAV_RUNS.exists():
        return None, 0
    t = pd.read_csv(STAV_RUNS)
    excluded = t["note"].fillna("").str.lower().str.startswith("exclude")
    t = t[~excluded].copy()
    t["timepoint"] = t["timepoint"].str.replace(r"^Follow-up.*", "Follow-up", regex=True)
    return t, int(excluded.sum())


def time_numbers():
    """Before (Daniel) per timepoint + weighted; tool overhead (measured); bracket for 'with the tool' (follow-up)."""
    before = dict(BEFORE)
    steps = manual_steps()
    fu_total, fu_record = None, None
    if steps is not None:
        for tp, g in steps.groupby("timepoint"):
            tot = g[g["step"].str.upper() == "TOTAL"]
            before[tp] = float(tot["minutes_mid"].iloc[0]) if len(tot) else float(g["minutes_mid"].sum())
        fu = steps[steps["timepoint"] == "Follow-up"]
        tot = fu[fu["step"].str.upper() == "TOTAL"]
        rec = fu[fu["step"].str.lower().str.startswith("recording")]
        if len(tot):
            fu_total = (float(tot["minutes_low"].iloc[0]), float(tot["minutes_high"].iloc[0]))
        if len(rec):
            fu_record = (float(rec["minutes_low"].iloc[0]), float(rec["minutes_high"].iloc[0]))
    before["Weighted"] = weighted(before)
    runs, n_excluded = overhead_runs()
    overhead = None
    if runs is not None and len(runs):
        a = runs["active_minutes"]
        overhead = {"min": float(a.min()), "median": float(a.median()), "max": float(a.max()), "n": int(len(a)),
                    "n_excluded": n_excluded, "nodules": (int(runs["nodules_reviewed"].min()), int(runs["nodules_reviewed"].max()))}
    # Upper end of 'with the tool' for a follow-up: today's time minus the step the tool removes (recording),
    # i.e. as if checking each AI draft took as long as doing the step by hand. Could be higher still if the
    # new steps (deciding on each AI mark, the central check) add time.
    upper = (fu_total[0] - fu_record[1], fu_total[1] - fu_record[0]) if fu_total and fu_record else None
    return before, overhead, fu_total, upper


def time_figure(fu_total, overhead, upper):
    """Range chart for one follow-up scan: Daniel today vs what is known about 'with the tool'.
    Deliberately NOT a before/after bar pair: the measured part (tool mechanics) is not comparable to a reader's time."""
    fig, ax = plt.subplots(figsize=(9, 3.2))
    y_today, y_tool = 1.0, 0.0
    if fu_total:
        lo, hi = fu_total
        ax.barh(y_today, lo, 0.42, color=INK2)
        ax.barh(y_today, hi - lo, 0.42, left=lo, color=INK2, alpha=0.45)
        ax.text(hi + 0.8, y_today, f"{lo:.0f}\u2013{hi:.0f} min (Daniel's own estimate)", va="center", fontsize=9.5)
    if overhead:
        ax.barh(y_tool, overhead["max"], 0.42, color=BLUE)
        ax.text(overhead["max"] + 0.5, y_tool + 0.33,
                f"tool mechanics, measured: {overhead['min']:.0f}\u2013{overhead['max']:.0f} active min "
                f"(n = {overhead['n']}, developer, not a reader)", va="center", fontsize=9, color=INK)
    if upper and overhead:
        ax.barh(y_tool, upper[1] - overhead["max"], 0.42, left=overhead["max"], color=SURFACE,
                edgecolor=INK2, hatch="///", linewidth=0.8)
        ax.text((overhead["max"] + upper[1]) / 2, y_tool - 0.36,
                "+ reader's judgement on the checked steps: NOT MEASURED (somewhere in this range)",
                ha="center", va="center", fontsize=9, color=INK2)
        ax.text(upper[1] + 0.8, y_tool, f"up to ~{upper[0]:.0f}\u2013{upper[1]:.0f} min if checking\ntakes as long as doing it by hand",
                va="center", fontsize=8.5, color=INK2)
    ax.set_yticks([y_tool, y_today], ["With the tool\n(estimate)", "Daniel today\n(manual)"])
    ax.set_xlim(0, 80)
    ax.set_ylim(-0.75, 1.5)
    ax.set_xlabel("minutes per follow-up scan")
    ax.grid(axis="y", visible=False)
    ax.set_title("One follow-up scan: what we know, and what we haven't measured (ESTIMATE)", loc="left",
                 fontweight="bold", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "time_before_after.png", dpi=200)
    plt.close(fig)


def summary_figure(f, noise_mm, fu_total, overhead, upper):
    """Page-1 figure for the short report: finding, quality, time, side by side."""
    v = pd.read_csv(HERE / "halo_variants_found52.csv")
    err = v["scaled_dL"].sort_values().to_numpy()
    found = int((f.found == True).sum()); n = len(f)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.3), gridspec_kw={"width_ratios": [1, 1.25, 1.35]})
    # (a) finding
    ax = axes[0]
    ax.barh([0], [found], color=BLUE, height=0.5)
    ax.barh([0], [n - found], left=[found + 0.6], color=ORANGE, height=0.5)
    ax.text(found / 2, 0, f"found {found}", ha="center", va="center", color="white", fontweight="bold")
    ax.text(found + 0.6 + (n - found) / 2, 0.42, f"missed {n - found}", ha="center", va="bottom", fontsize=9, color=INK2)
    ax.set_xlim(0, n + 2); ax.set_ylim(-0.6, 1.0); ax.set_yticks([]); ax.grid(False)
    ax.set_xlabel(f"{n} scans, 31 patients (public data)")
    ax.set_title(f"Finding: {found}/{n} scans ({100*found/n:.0f}%)", loc="left", fontweight="bold", fontsize=10.5)
    ax.text(0, -0.55, "all misses: central tumours", fontsize=8.5, color=INK2)
    # (b) quality
    ax = axes[1]
    x = np.arange(len(err)); inside = np.abs(err) <= noise_mm
    ax.axhspan(-noise_mm, noise_mm, color=BAND, zorder=0); ax.axhline(0, color=INK2, lw=0.8)
    ax.scatter(x[inside], err[inside], s=16, color=BLUE, zorder=3, edgecolor=SURFACE, linewidth=1)
    ax.scatter(x[~inside], err[~inside], s=16, color=ORANGE, zorder=3, edgecolor=SURFACE, linewidth=1)
    ax.set_xticks([]); ax.set_ylabel("mm")
    ax.set_xlabel(f"{len(err)} tumours, 28 patients, sorted")
    ax.set_title(f"Quality: long axis, AI draft vs expert", loc="left", fontweight="bold", fontsize=10.5)
    ax.text(1, max(err) * 0.92, f"{inside.sum()}/{len(err)} within the expert's own\nrepeat variation (band, \u00b1{noise_mm:g} mm)",
            fontsize=8.5, color=INK2, va="top")
    # (c) time
    ax = axes[2]
    if fu_total:
        lo, hi = fu_total
        ax.barh(1, lo, 0.45, color=INK2); ax.barh(1, hi - lo, 0.45, left=lo, color=INK2, alpha=0.45)
        ax.text(hi + 1, 1, f"{lo:.0f}\u2013{hi:.0f} min", va="center", fontsize=9)
    if overhead and upper:
        ax.barh(0, overhead["max"], 0.45, color=BLUE)
        ax.barh(0, upper[1] - overhead["max"], 0.45, left=overhead["max"], color=SURFACE, edgecolor=INK2, hatch="///", linewidth=0.7)
        ax.text(0, -0.48, f"measured: tool mechanics {overhead['min']:.0f}\u2013{overhead['max']:.0f} min (n={overhead['n']}, developer)",
                fontsize=8, color=INK, va="center")
        ax.text(0, -0.8, "hatched: reader's judgement, NOT measured", fontsize=8, color=INK2, va="center")
    ax.set_yticks([0, 1], ["with the tool\n(estimate)", "Daniel today"])
    ax.set_xlim(0, 70); ax.set_ylim(-1.0, 1.5); ax.grid(axis="y", visible=False)
    ax.set_xlabel("minutes per follow-up scan")
    ax.set_title("Time: one follow-up scan", loc="left", fontweight="bold", fontsize=10.5)
    fig.tight_layout(w_pad=2.5)
    fig.savefig(OUT / "summary_at_a_glance.png", dpi=220)
    plt.close(fig)


def main():
    f = pd.read_csv(HERE / "finding_exam_all59.csv")
    m = pd.read_csv(HERE / "finding_exam_matching.csv")
    found = f[f.found == True]
    noise_mm, noise_pct, n_pairs = expert_noise()
    finding_figure(f)
    lm, vm, lin, vin, nq = error_figure(noise_mm, noise_pct)
    method_figure(found, noise_mm, noise_pct)
    before, overhead, fu_total, upper = time_numbers()
    time_figure(fu_total, overhead, upper)
    summary_figure(f, noise_mm, fu_total, overhead, upper)
    print(f"before: baseline {before['Baseline']:.0f} min, follow-up {before['Follow-up']:.1f} min, weighted {before['Weighted']:.1f} min")
    if fu_total:
        print(f"follow-up today (Daniel): {fu_total[0]:.0f}-{fu_total[1]:.0f} min; log cross-check {BEFORE['Follow-up']} min")
    if overhead:
        print(f"tool overhead (developer pilot): {overhead['min']:.0f}-{overhead['max']:.0f} active min, median {overhead['median']:.0f}, "
              f"n = {overhead['n']} ({overhead['n_excluded']} excluded), {overhead['nodules'][0]}-{overhead['nodules'][1]} nodules per scan")
    if upper and overhead:
        print(f"with the tool, follow-up: between {overhead['min']:.0f}-{overhead['max']:.0f} min (mechanics only) and ~{upper[0]:.0f}-{upper[1]:.0f} min "
              f"(judgement as slow as doing it by hand); judgement time NOT measured")
    print(f"figures written to {OUT}")


if __name__ == "__main__":
    main()
