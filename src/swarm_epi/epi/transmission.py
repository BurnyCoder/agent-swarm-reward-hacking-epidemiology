"""One-step transmission map, fixed points / regime, and reproduction-number formulas (prereg §7.1, §7.3).

Local context:
- Map (Hu et al. 2026, arXiv 2610.12822, App. L, Eq. L.2, without their pass-probability normalization because every
  agent posts): with uniform sampling the number of pro-hack posts read is ~Binomial(K, x), so the share of pro-hack
  posts next round is f(x) = sum_k Bin(k; K, x) q_k, q_k = P(own post pro-hack | k) from the dose-response assay.
  R_map = f'(0) = K (q_1 - q_0).
- Regimes (prereg §7.1; cf. Dodds & Watts 2004 classes): supercritical if R_map > 1; bistable if there are two stable
  fixed points (low and high) separated by an unstable one; otherwise monostable low.
- Board R0 with persistence (prereg §7.3; homogeneous R0 = d q of Wu et al. 2026, Eq. 4, with fan-out d = K~ D and
  q = pi h1): R0 = pi * K~ * h1 * D.
Global context: `analysis.py` H3.
"""

from __future__ import annotations  # forward references

from collections.abc import Callable  # map type

import numpy as np  # numerics
from scipy import optimize  # root finding
from scipy.stats import binom  # binomial pmf


def f_map(x: np.ndarray, q: np.ndarray, K: int) -> np.ndarray:
    """f(x) = sum_{k=0}^{K} Bin(k; K, x) q[k] (vectorized over x)."""
    x = np.atleast_1d(np.asarray(x, float))
    k = np.arange(K + 1)
    return binom.pmf(k[None, :], K, x[:, None]) @ np.asarray(q, float)


def fprime0(q: np.ndarray, K: int) -> float:
    """f'(0) = K (q_1 - q_0) (derivative of the binomial mixture at x = 0)."""
    return float(K * (q[1] - q[0]))


def fixed_points(f: Callable[[np.ndarray], np.ndarray], n_grid: int = 2001) -> list[dict]:
    """All fixed points x* = f(x*) on [0, 1] with stability |f'(x*)| < 1 (grid sign changes + Brent refinement)."""
    x = np.linspace(0, 1, n_grid)
    g = f(x) - x  # fixed points are roots of g
    out = []
    for i in np.where(np.sign(g[:-1]) * np.sign(g[1:]) <= 0)[0]:
        if g[i] == 0 and i > 0 and g[i - 1] == 0:
            continue  # flat zero run: count once
        root = optimize.brentq(lambda z: float(f(np.array([z]))[0] - z), x[i], x[i + 1]) if g[i] != g[i + 1] else x[i]
        h = 1e-5
        slope = float((f(np.array([min(root + h, 1)]))[0] - f(np.array([max(root - h, 0)]))[0]) / (2 * h))
        if not out or abs(root - out[-1]["x"]) > 1e-6:
            out.append({"x": float(root), "slope": slope, "stable": abs(slope) < 1})
    return out


def regime(q: np.ndarray, K: int) -> dict:
    """Classify the memoryless post-level epidemic from q_k (prereg §7.1)."""
    fps = fixed_points(lambda x: f_map(x, q, K))
    stable = [p for p in fps if p["stable"]]
    r_map = fprime0(q, K)
    if r_map > 1:
        name = "supercritical"
    elif len(stable) >= 2 and any(not p["stable"] for p in fps):
        name = "bistable"
    else:
        name = "monostable_low"
    return {"R_map": r_map, "fixed_points": fps, "regime": name}


def hu_R(theta1: float, u0: float, k: int) -> float:
    """Hu et al. (2026) local propagation factor R = k theta_1 / u_0 (assumes theta_0 = 0)."""
    return float(k * theta1 / u0)


def board_R0(pi: float, K_tilde: float, h1: float, D: float) -> float:
    """R0 = pi * K~ * h1 * D (prereg §7.3)."""
    return float(pi * K_tilde * h1 * D)
