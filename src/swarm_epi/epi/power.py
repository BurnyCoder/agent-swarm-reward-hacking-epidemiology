"""Simulation-based power and identifiability (prereg §8.6, ADEMP structure of Morris, White & Crowther 2019).

Local context:
- Data-generating mechanism: the K-of-N chain-binomial simulator (`simulate.py`), N=32, m=2, K=6, T=10, baseline
  hazard eps from the calibration (k=0 rate of the chosen prompt), per-post hazard h1 in {0, .01, .02, .05, .10, .20}
  (simple kernel 1 - (1-eps)(1-h1)^k), recovery and post stances from the pilot harvest.
- H1 power: rejection rate of the one-sided paired test of run-level mean prevalence (MAIN vs PLACEBO, 20 pairs) at the
  worst-case Holm level alpha = 0.05/3; the paired t-test is used as a fast stand-in for the exact sign-flip test
  (documented; both are tests of the mean paired difference). Monte Carlo SE = sqrt(P(1-P)/n_sim).
- TOST power: probability of declaring equivalence within +-10 pp when both arms are PLACEBO (true effect 0).
- Identifiability: cumulative-incidence data are simulated from each growth family (its pilot-fitted or default
  parameters) with conditional-binomial noise; the share of datasets where AICc picks the generating family is
  reported per family and overall (prereg rule: curve-family comparisons are descriptive only if < 80%).
Global context: `run_experiment.py power` writes data/power.json, quoted in the Stage 2 addendum.
"""

from __future__ import annotations  # forward references

import numpy as np  # numerics
from scipy import stats  # tests
from statsmodels.stats.weightstats import ttost_paired  # paired TOST

from . import curves  # growth families
from .simulate import simulate_many  # chain-binomial simulator


def h1_power(eps: float, h1: float, recover: float, pi_h: float, pi_n: float = 0.0, n_pairs: int = 20,
             n_sim: int = 1000, N: int = 32, K: int = 6, T: int = 10, alpha: float = 0.05 / 3,
             sesoi: float = 0.10, seed: int = 0) -> dict:
    """Power of H1 (and TOST power when h1 = 0) under the simple-contagion kernel with per-post hazard h1."""
    rng = np.random.default_rng(seed)
    kernel = lambda k: 1 - (1 - eps) * (1 - h1) ** np.asarray(k)
    flat = lambda k: np.full(np.shape(k), eps)
    reject = equiv = 0
    diffs = []
    for _ in range(n_sim):
        main = simulate_many(n_pairs, rng, N=N, K=K, T=T, n_seeds=2, infect=kernel, recover=recover, pi_h=pi_h,
                             pi_n=pi_n)
        plac = simulate_many(n_pairs, rng, N=N, K=K, T=T, n_seeds=2, infect=kernel, recover=recover, pi_h=pi_h,
                             pi_n=pi_n) if h1 == 0 else \
            simulate_many(n_pairs, rng, N=N, K=K, T=T, n_seeds=0, infect=flat, recover=recover, pi_h=0, pi_n=0)
        a, b = main[:, 1:].mean(1) / N, plac[:, 1:].mean(1) / N  # run-level mean prevalence, rounds 1..T
        diffs.append(float(np.mean(a - b)))
        reject += stats.ttest_rel(a, b, alternative="greater").pvalue < alpha
        equiv += ttost_paired(a, b, -sesoi, sesoi)[0] < 0.05
    p, q = reject / n_sim, equiv / n_sim
    return {"h1": h1, "power": p, "mc_se": float(np.sqrt(p * (1 - p) / n_sim)), "tost_power": q,
            "mean_diff": float(np.mean(diffs)), "n_sim": n_sim}


def simulate_family(name: str, params: list, n_runs: int, N: int, T: int, rng: np.random.Generator) -> np.ndarray:
    """Cumulative counts (n_runs x T+1) from a growth family via conditional-binomial increments."""
    m = np.clip(curves.MODELS[name].f(np.arange(T + 1, dtype=float), params), 0, N - 1e-6)  # model trajectory
    h = np.clip(np.diff(m) / np.maximum(N - m[:-1], 1e-9), 0, 1)  # per-round hazards
    C = np.zeros((n_runs, T + 1), int)
    C[:, 0] = rng.binomial(N, min(m[0] / N, 1))  # initial counts
    for t in range(1, T + 1):
        C[:, t] = C[:, t - 1] + rng.binomial(N - C[:, t - 1], h[t - 1])
    return C


DEFAULT_PARAMS = {  # plausible shapes at N=32, T=10 (used when the pilot gives no fit for a family)
    "linear": [1.0, 1.5], "exponential": [1.0, 0.3], "logistic": [1.0, 0.8, 25.0], "gompertz": [1.0, 1.2, 0.4],
    "ggm": [1.0, 0.8, 0.6], "bass": [1.0, 0.02, 0.8, 26.0], "richards": [1.0, 0.8, 25.0, 3.0],
}


def identifiability(params: dict | None = None, n_runs: int = 20, n_sim: int = 100, N: int = 32, T: int = 10,
                    seed: int = 0) -> dict:
    """Share of simulated pooled datasets in which AICc selects the generating family."""
    params = params or DEFAULT_PARAMS
    rng = np.random.default_rng(seed)
    acc = {}
    for name, th in params.items():
        hits = 0
        for _ in range(n_sim):
            fits = curves.fit_all(simulate_family(name, th, n_runs, N, T, rng), N)
            hits += min(fits, key=lambda m: fits[m].aicc) == name
        acc[name] = hits / n_sim
    return {"per_family": acc, "overall": float(np.mean(list(acc.values()))),
            "passes_80pct": bool(np.mean(list(acc.values())) >= 0.80)}
