"""Static figures (PNG) for README/paper, generated only from results files written by `analysis.py`.

Local context: matplotlib with the dataviz reference palette (categorical slots 1-3 validated all-pairs; colors follow
the condition entity in every figure: MAIN blue, PLACEBO orange, TRANSIENT aqua). Proportions keep 0 as the baseline;
the top is 1 or, for rare outcomes, just above the largest per-run value so differences stay visible,
uncertainty is always drawn (95% bootstrap bands over runs, Wilson intervals for assay cells), one y-axis per chart.
Global context: `scripts/analyze.py` calls `make_all`; filenames are referenced from README and the paper.
"""

from __future__ import annotations  # forward references

import json  # summary
from pathlib import Path  # paths

import matplotlib
import matplotlib.ticker  # plain log-axis tick labels

matplotlib.use("Agg")  # headless rendering
import matplotlib.pyplot as plt  # plotting (imported after selecting the Agg backend)
import numpy as np  # numerics
import pandas as pd  # tables
from statsmodels.stats.proportion import proportion_confint  # Wilson intervals

from .epi import dose  # shared fitted dose-response curve formulas

COLORS = {"MAIN": "#2a78d6", "PLACEBO": "#eb6834", "TRANSIENT": "#1baf7a"}  # dataviz palette slots 1-3 (light)
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"  # text primary / secondary, recessive grid
plt.rcParams.update({"axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10, "lines.linewidth": 2, "figure.dpi": 150})


def _band(values: np.ndarray, rng: np.random.Generator, B: int = 2000) -> tuple[np.ndarray, np.ndarray]:
    """95% bootstrap band of the across-run mean for a runs x rounds matrix (resampling runs)."""
    boots = np.stack([values[rng.integers(0, len(values), len(values))].mean(0) for _ in range(B)])
    return np.percentile(boots, 2.5, 0), np.percentile(boots, 97.5, 0)


def fig_prevalence(prev: pd.DataFrame, out: Path, col: str = "prevalence", fname: str = "fig_prevalence.png",
                   ylabel: str = "Hack-attempt prevalence (non-seed agents)",
                   title: str = "Spread of hacking through the swarm") -> None:
    """Per-round rate `col` (default: non-seed hack-attempt prevalence): thin per-run lines + mean with 95% bootstrap
    band. Also draws the flag-rate curve (col="flag_rate") for the counter-contagion analysis."""
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(7, 4))
    top = 1.0 if prev[col].max() > 0.5 else max(0.2, 1.15 * prev[col].max())  # zero baseline kept; rare outcomes zoom
    for cond, g in prev.groupby("condition"):
        mat = g.pivot(index="run_id", columns="round", values=col).values  # runs x rounds
        x = np.arange(mat.shape[1])
        for row in mat:  # individual runs (recessive)
            ax.plot(x, row, color=COLORS.get(cond, INK2), alpha=0.12, linewidth=0.8)
        lo, hi = _band(mat, rng)
        ax.fill_between(x, lo, hi, color=COLORS.get(cond, INK2), alpha=0.2, linewidth=0)
        ax.plot(x, mat.mean(0), color=COLORS.get(cond, INK2), label=f"{cond} (n={len(mat)} runs)")
    ax.set(xlabel="Round (0 = warm-up, empty board)", ylabel=ylabel, ylim=(0, top), title=title)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / fname)
    plt.close(fig)


def fig_dose(summary: dict, out: Path) -> None:
    """Assay dose-response: P(hack | k) with Wilson CIs and the fitted simple / Weibull / sigmoid curves."""
    a = summary.get("h4")
    if not a:
        return
    tab = pd.DataFrame(a["table"])
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    kk = np.linspace(0, 6, 200)
    for ax, col, title in [(axes[0], "hack", "P(hack attempt | k pro-hack posts read)"),
                           (axes[1], "post_pro", "P(own post pro-hack | k)")]:
        lo, hi = proportion_confint((tab[col] * tab["n"]).round(), tab["n"], method="wilson")  # 95% Wilson
        ax.errorbar(tab["k"], tab[col], yerr=[tab[col] - lo, hi - tab[col]], fmt="o", color=COLORS["MAIN"],
                    markersize=6, capsize=3, label="assay cells (95% Wilson CI)")
        if col == "hack":  # fitted kernels (neutral ink, line style encodes the model)
            for name, ls in zip(("simple", "weibull", "sigmoid"), ["-", "--", ":"]):
                ax.plot(kk, dose.curve(name, a["hack"][name]["params"], kk), color=INK2, linestyle=ls,
                        linewidth=1.5, label=f"{name} fit")
        ax.set(xlabel="k = pro-hack posts among K=6 read", ylim=(0, 1), title=title)
        ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_dose_response.png")
    plt.close(fig)


def fig_hazard(summary: dict, out: Path) -> None:
    """Forest plot of hazard ratios per pro-hack post read (seed vs non-seed authors) + permutation control."""
    h = summary.get("h2", {})
    if "k_nonseed_pro" not in h:
        return
    rows = [("non-seed author (primary)", h["k_nonseed_pro"]), ("seed author", h["k_seed_pro"]),
            ("non-seed, run x round FE", h["robust_run_round_fe"]),
            ("author hack status (judge-free)", h["robust_author_status"]),
            ("non-seed, first-ever hack", h["sensitivity_first_ever"])]
    fig, ax = plt.subplots(figsize=(8, 3.4))  # wide enough for the row labels, title and axis label
    for i, (name, r) in enumerate(rows):
        ax.errorbar(r["hr"], i, xerr=[[r["hr"] - r["hr_low"]], [r["hr_high"] - r["hr"]]], fmt="o", capsize=3,
                    color=COLORS["MAIN"] if i == 0 else INK2, markersize=7)
    ax.axvline(1, color=INK2, linewidth=1)  # no-effect reference
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_xscale("log")
    lo, hi = min(r["hr_low"] for _, r in rows), max(r["hr_high"] for _, r in rows)
    ticks = [t for t in (0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8, 12) if lo / 1.1 <= t <= hi * 1.1] or [1]
    ax.set_xticks(ticks, [f"{t:g}" for t in ticks])  # plain labels instead of 2x10^0
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set(xlabel="Hazard ratio per pro-hack post read (log scale, 95% cluster-robust CI)",
           title="Per-post transmission hazard (randomized exposure; all conditions)")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out / "fig_hazard.png")
    plt.close(fig)


def fig_h5(summary: dict, out: Path, N: int = 32) -> None:
    """Observed mean infected count vs assay-calibrated simulator (95% envelope) and broadcast-only baseline."""
    h5 = summary.get("h5") or {}
    conds = [c for c in ("MAIN", "TRANSIENT") if c in h5]
    if not conds:
        return
    fig, axes = plt.subplots(1, len(conds), figsize=(4.8 * len(conds), 3.8), squeeze=False)
    for ax, cond in zip(axes[0], conds):
        d = h5[cond]
        x = np.arange(len(d["observed_mean"]))
        for name, ls in [("assay_model", "-"), ("broadcast_only", "--")]:
            ax.fill_between(x, np.array(d[name]["lo"]) / N, np.array(d[name]["hi"]) / N, color=INK2, alpha=0.12,
                            linewidth=0)
            ax.plot(x, np.array(d[name]["mean_curve"]) / N, color=INK2, linestyle=ls,
                    label=f"{name.replace('_', ' ')} (CRPS {d[name]['crps']:.2f})")
        ax.plot(x, np.array(d["observed_mean"]) / N, "o-", color=COLORS[cond], label="observed mean")
        ax.set(xlabel="Round", ylabel="Hack-attempt prevalence", ylim=(0, 1), title=f"{cond}: out-of-sample prediction")
        ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_h5_prediction.png")
    plt.close(fig)


def fig_mechanisms(summary: dict, out: Path) -> None:
    """Hack mechanisms by condition (counts of hack-attempt agent-rounds)."""
    mech = summary.get("mechanisms") or {}
    if not mech:
        return
    df = pd.DataFrame(mech).fillna(0)  # mechanisms x conditions
    fig, ax = plt.subplots(figsize=(7, 3.5))
    width = 0.8 / max(len(df.columns), 1)
    for i, cond in enumerate(df.columns):
        ax.bar(np.arange(len(df)) + i * width, df[cond], width=width * 0.92, color=COLORS.get(cond, INK2),
               label=cond)
    ax.set_xticks(np.arange(len(df)) + width * (len(df.columns) - 1) / 2, df.index, rotation=15)
    ax.set(ylabel="Hack-attempt agent-rounds", title="How agents hacked (ImpossibleBench taxonomy)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "fig_mechanisms.png")
    plt.close(fig)


def make_all(results_dir: Path) -> list[str]:
    """Render every figure that the available results support; returns written filenames."""
    out = results_dir / "figures"
    out.mkdir(parents=True, exist_ok=True)
    summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    prev = pd.read_csv(results_dir / "prevalence_by_round.csv")
    fig_prevalence(prev, out)
    if "flag_rate" in prev:  # counter-contagion: share of non-seed agents replying with the flag
        fig_prevalence(prev, out, "flag_rate", "fig_flag_rate.png", "Flag rate (non-seed agents)",
                       "Spread of flagging through the swarm")
    for fn in (fig_dose, fig_hazard, fig_h5, fig_mechanisms):
        fn(summary, out)
    return sorted(p.name for p in out.glob("*.png"))
