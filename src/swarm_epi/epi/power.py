"""Simulation-based power and identifiability checks (pre-registered pilot rules).

Local context: uses the matched chain-binomial simulator with pilot-fitted parameters.
- `h1_power`: fraction of simulated batches (n runs per arm) in which the one-sided Welch test of run-level MAIN vs
  PLACEBO prevalence rejects at alpha (PLACEBO = no pro-hack seeds, background kernel only).
- `curve_identifiability`: generate pooled cumulative-incidence batches from (a) a contagion process (agents' posts
  transmit, pi > 0) and (b) a broadcast-only process (pi = 0: only seeds transmit) and record how often AICc prefers a
  logistic over a linear curve in (a) and linear-or-Bass-with-no-imitation in (b). The prereg treats growth-curve
  model selection as evidence only if both rates are >= 80%.
Global context: run after the pilot (`scripts/power.py`); results go in reports/pilot.md.
"""

from __future__ import annotations  # forward references

from collections.abc import Callable  # kernel type

import numpy as np  # numerics
from scipy import stats  # Welch test

from . import curves  # growth models
from .simulate import simulate_many  # chain-binomial simulator


def h1_power(kernel: Callable, eps: float, recover: float, pi: float, n_runs: int = 20, batches: int = 200,
             N: int = 32, K: int = 6, T: int = 10, alpha: float = 0.05, seed: int = 0) -> float:
    """Power of the H1 run-level comparison under the fitted model."""
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(batches):
        main = simulate_many(n_runs, rng, N=N, K=K, T=T, n_seeds=2, infect=kernel, recover=recover, pi=pi)
        plac = simulate_many(n_runs, rng, N=N, K=K, T=T, n_seeds=0, infect=lambda k: np.full(np.shape(k), eps),
                             recover=recover, pi=0.0)
        a, b = main[:, 1:].mean(1) / N, plac[:, 1:].mean(1) / N  # run-level mean prevalence over rounds 1..T
        hits += stats.ttest_ind(a, b, equal_var=False, alternative="greater").pvalue < alpha
    return hits / batches


def curve_identifiability(kernel: Callable, recover: float, pi: float, n_runs: int = 20, batches: int = 50,
                          N: int = 32, K: int = 6, T: int = 10, seed: int = 0) -> dict:
    """How often AICc picks the right growth family for contagion vs broadcast-only pooled batches."""
    rng = np.random.default_rng(seed)
    ok_contagion = ok_broadcast = 0
    for _ in range(batches):
        Cc = simulate_many(n_runs, rng, N=N, K=K, T=T, n_seeds=2, infect=kernel, recover=recover, pi=pi,
                           cumulative=True)
        Cb = simulate_many(n_runs, rng, N=N, K=K, T=T, n_seeds=2, infect=kernel, recover=recover, pi=0.0,
                           cumulative=True)
        fc, fb = curves.fit_all(Cc, N), curves.fit_all(Cb, N)
        ok_contagion += fc["logistic"].aicc < fc["linear"].aicc - 2  # logistic clearly better
        ok_broadcast += fb["linear"].aicc <= fb["logistic"].aicc + 2 or fb["bass"].params["b"] < 0.05
    return {"contagion_correct": ok_contagion / batches, "broadcast_correct": ok_broadcast / batches}
