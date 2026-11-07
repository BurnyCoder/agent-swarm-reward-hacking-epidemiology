"""Run-level statistics: two-group comparison (Welch, permutation, bootstrap CI, TOST), Holm correction, scoring rules.

Local context: the independent unit is the swarm RUN (agents within a run interact), so every confirmatory comparison
uses one summary value per run (cluster-level analysis; Field & Welsh 2007, JRSS-B 69:369 on cluster bootstraps).
- Welch's unequal-variance t-test: scipy.stats.ttest_ind(equal_var=False).
- Permutation test of the mean difference: scipy.stats.permutation_test (exact-ish Monte Carlo, 'greater').
- Bootstrap CI of the difference: resample runs within each group (percentile interval).
- Equivalence: two one-sided tests (TOST) with margin +-sesoi, statsmodels ttost_ind (Schuirmann 1987).
- Holm step-down adjustment: statsmodels multipletests(method="holm") (Holm 1979).
- CRPS of an ensemble forecast: E|X-y| - 0.5 E|X-X'| (Gneiting & Raftery 2007, JASA 102:359, Eq. 21).
Global context: `analysis.py` confirmatory family (H1) and H5 forecast scoring.
"""

from __future__ import annotations  # forward references

import numpy as np  # numerics
from scipy import stats  # tests
from statsmodels.stats.multitest import multipletests  # Holm
from statsmodels.stats.weightstats import ttost_ind  # TOST


def compare_runs(a: np.ndarray, b: np.ndarray, sesoi: float = 0.10, rng: np.random.Generator | None = None,
                 n_boot: int = 10000, n_perm: int = 10000) -> dict:
    """Compare run-level summaries of group a (e.g. MAIN) vs b (e.g. PLACEBO); directional H: mean(a) > mean(b)."""
    rng = rng or np.random.default_rng(0)  # reproducible resampling
    a, b = np.asarray(a, float), np.asarray(b, float)  # run-level values
    diff = a.mean() - b.mean()  # effect estimate (proportion points)
    welch = stats.ttest_ind(a, b, equal_var=False, alternative="greater")  # Welch one-sided
    perm = stats.permutation_test((a, b), lambda x, y: x.mean() - y.mean(), permutation_type="independent",
                                  n_resamples=n_perm, alternative="greater", random_state=rng)  # label shuffling
    boots = np.array([rng.choice(a, a.size).mean() - rng.choice(b, b.size).mean() for _ in range(n_boot)])  # runs
    lo, hi = np.percentile(boots, [2.5, 97.5])  # 95% percentile CI
    p_tost = float(ttost_ind(a, b, -sesoi, sesoi, usevar="unequal")[0])  # equivalence p-value
    return {"diff": float(diff), "ci_low": float(lo), "ci_high": float(hi), "p_welch": float(welch.pvalue),
            "p_perm": float(perm.pvalue), "p_tost": p_tost, "n_a": int(a.size), "n_b": int(b.size),
            "mean_a": float(a.mean()), "mean_b": float(b.mean())}


def holm(pvals) -> np.ndarray:
    """Holm-adjusted p-values (family-wise error control)."""
    return multipletests(np.asarray(pvals, float), method="holm")[1]


def crps_ensemble(ens: np.ndarray, y: float) -> float:
    """CRPS of ensemble `ens` at observation y: mean|X-y| - 0.5 mean|X-X'| (O(n log n) via sorting)."""
    x = np.sort(np.asarray(ens, float))  # sorted ensemble
    n = x.size
    term1 = np.mean(np.abs(x - y))  # E|X - y|
    # E|X - X'| = (2 / n^2) * sum_i (2i - n - 1) x_(i) for sorted x (1-indexed i)
    term2 = 2.0 / n**2 * np.sum((2 * np.arange(1, n + 1) - n - 1) * x)
    return float(term1 - 0.5 * term2)


def log_score_counts(ens: np.ndarray, y: int, support: int) -> float:
    """Log predictive probability of integer outcome y under an ensemble's smoothed empirical pmf on 0..support."""
    counts = np.bincount(np.asarray(ens, int), minlength=support + 1)[: support + 1] + 0.5  # Jeffreys-style smoothing
    return float(np.log(counts[y] / counts.sum()))


def cluster_bootstrap(groups: list, stat_fn, n_boot: int = 2000, rng: np.random.Generator | None = None) -> np.ndarray:
    """Bootstrap distribution of stat_fn(list of resampled clusters) — resample whole runs with replacement."""
    rng = rng or np.random.default_rng(0)
    return np.array([stat_fn([groups[i] for i in rng.integers(0, len(groups), len(groups))]) for _ in range(n_boot)])
