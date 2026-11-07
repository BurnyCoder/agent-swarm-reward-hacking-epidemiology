"""Run-level statistics: paired (CRN) comparisons, Welch robustness, bootstrap CIs, TOST, Holm, forecast scores.

Local context (preregistration §9.1, §9.4-9.6):
- Primary paired test: exact sign-flip permutation test over CRN pairs (`scipy.stats.permutation_test` with
  permutation_type="samples", n_resamples=np.inf, alternative="greater"), statistic = mean paired difference.
- Effect CI: percentile bootstrap resampling whole CRN pairs (B = 10,000; Field & Welsh 2007, JRSS-B 69:369).
- Equivalence: paired TOST against +-sesoi (statsmodels `ttost_paired`; Schuirmann 1987); Welch TOST as robustness
  (`ttost_ind(usevar="unequal")`).
- Robustness: one-sided Welch t-test on run means (`ttest_ind(equal_var=False)`), which ignores the pairing.
- Holm step-down adjustment: `multipletests(method="holm")` (the library default is Holm-Sidak; Holm 1979).
- Forecast scores for integer counts from a predictive pmf (Gneiting & Raftery 2007, JASA 102:359): CRPS* =
  sum_x (F(x) - 1{y <= x})^2 (lower is better, p. 367) and log score log p(y) (Eq. 19), add-one smoothing over bins.
Global context: `analysis.py` H1 / H3 / H5.
"""

from __future__ import annotations  # forward references

import numpy as np  # numerics
from scipy import stats  # tests
from statsmodels.stats.multitest import multipletests  # Holm
from statsmodels.stats.weightstats import ttost_ind, ttost_paired  # TOST


def compare_paired(a: np.ndarray, b: np.ndarray, sesoi: float = 0.10, rng: np.random.Generator | None = None,
                   n_boot: int = 10000, covariate: np.ndarray | None = None) -> dict:
    """Paired comparison of CRN pairs (a[r], b[r]); directional H: mean(a - b) > 0.

    `covariate` (optional, e.g. round-0 prevalence difference per pair) gives the pre-registered adjusted robustness
    test: d_adj = d - beta * (c - mean(c)) with beta from OLS of d on c, then the same sign-flip test.
    """
    rng = rng or np.random.default_rng(0)  # reproducible resampling
    a, b = np.asarray(a, float), np.asarray(b, float)  # paired run-level values
    d = a - b  # paired differences

    def signflip_p(x: np.ndarray) -> float:
        res = stats.permutation_test((x, np.zeros_like(x)), lambda u, v, axis: np.mean(u - v, axis=axis),
                                     permutation_type="samples", n_resamples=np.inf, alternative="greater",
                                     vectorized=True)  # exact enumeration of all 2^n within-pair swaps
        return float(res.pvalue)

    boots = np.array([d[rng.integers(0, d.size, d.size)].mean() for _ in range(n_boot)])  # resample pairs
    out = {"diff": float(d.mean()), "ci_low": float(np.percentile(boots, 2.5)),
           "ci_high": float(np.percentile(boots, 97.5)), "p_signflip": signflip_p(d),
           "p_welch": float(stats.ttest_ind(a, b, equal_var=False, alternative="greater").pvalue),
           "p_tost_paired": float(ttost_paired(a, b, -sesoi, sesoi)[0]),
           "p_tost_welch": float(ttost_ind(a, b, -sesoi, sesoi, usevar="unequal")[0]),
           "p_two_sided_negative": float(stats.ttest_rel(a, b, alternative="less").pvalue),
           "ci90_low": float(np.percentile(boots, 5)), "ci90_high": float(np.percentile(boots, 95)),
           "n_pairs": int(d.size), "mean_a": float(a.mean()), "mean_b": float(b.mean())}
    if covariate is not None:  # round-0-adjusted robustness
        c = np.asarray(covariate, float) - np.mean(covariate)  # centred covariate
        beta = float(np.dot(c, d - d.mean()) / max(np.dot(c, c), 1e-12))  # OLS slope
        out["p_signflip_adjusted"] = signflip_p(d - beta * c)
    return out


def compare_runs(a: np.ndarray, b: np.ndarray, sesoi: float = 0.10, rng: np.random.Generator | None = None,
                 n_boot: int = 10000, n_perm: int = 10000) -> dict:
    """Unpaired comparison (independent groups): permutation + Welch + bootstrap CI + Welch TOST."""
    rng = rng or np.random.default_rng(0)
    a, b = np.asarray(a, float), np.asarray(b, float)
    perm = stats.permutation_test((a, b), lambda x, y, axis: np.mean(x, axis=axis) - np.mean(y, axis=axis),
                                  permutation_type="independent", n_resamples=n_perm, alternative="greater",
                                  vectorized=True, random_state=rng)
    boots = np.array([rng.choice(a, a.size).mean() - rng.choice(b, b.size).mean() for _ in range(n_boot)])
    return {"diff": float(a.mean() - b.mean()), "ci_low": float(np.percentile(boots, 2.5)),
            "ci_high": float(np.percentile(boots, 97.5)), "p_perm": float(perm.pvalue),
            "p_welch": float(stats.ttest_ind(a, b, equal_var=False, alternative="greater").pvalue),
            "p_tost": float(ttost_ind(a, b, -sesoi, sesoi, usevar="unequal")[0]), "n_a": int(a.size),
            "n_b": int(b.size), "mean_a": float(a.mean()), "mean_b": float(b.mean())}


def holm(pvals) -> np.ndarray:
    """Holm-adjusted p-values (family-wise error control)."""
    return multipletests(np.asarray(pvals, float), method="holm")[1]


def pmf_from_samples(samples: np.ndarray, support: int) -> np.ndarray:
    """Add-one-smoothed empirical pmf on 0..support (prereg §9.5)."""
    counts = np.bincount(np.asarray(samples, int), minlength=support + 1)[: support + 1] + 1.0  # add-one smoothing
    return counts / counts.sum()


def crps_star(pmf: np.ndarray, y: int) -> float:
    """CRPS* for an integer outcome: sum_x (F(x) - 1{y <= x})^2 over the support (lower is better)."""
    F = np.cumsum(pmf)  # predictive CDF
    x = np.arange(pmf.size)  # support
    return float(np.sum((F - (y <= x)) ** 2))


def log_score(pmf: np.ndarray, y: int) -> float:
    """Logarithmic score log p(y) (higher is better)."""
    return float(np.log(pmf[y]))


def interval_covers(pmf: np.ndarray, y: int, level: float = 0.90) -> bool:
    """Whether the central `level` predictive interval (quantiles of the pmf) contains y."""
    F = np.cumsum(pmf)
    lo = int(np.searchsorted(F, (1 - level) / 2))  # lower quantile
    hi = int(np.searchsorted(F, 1 - (1 - level) / 2))  # upper quantile
    return lo <= y <= hi


def crps_ensemble(ens: np.ndarray, y: float) -> float:
    """CRPS of a continuous ensemble: mean|X-y| - 0.5 mean|X-X'| (Gneiting & Raftery 2007, Eq. 21; sorted form)."""
    x = np.sort(np.asarray(ens, float))
    n = x.size
    return float(np.mean(np.abs(x - y)) - (np.sum((2 * np.arange(1, n + 1) - n - 1) * x) / n**2))
