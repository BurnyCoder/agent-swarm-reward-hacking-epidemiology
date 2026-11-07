"""One-step transmission map, its derivative at zero, and reproduction-number formulas.

Local context:
- Map (Hu et al. 2026, arXiv 2610.12822, App. L: T(x) = sum_j Bin(j; k, x) theta_j): if a fraction x of readable posts
  is pro-hack and an agent reads K posts uniformly, the number of pro-hack posts read is ~Binomial(K, x), so the
  probability that the agent's own post is pro-hack is f(x) = sum_k Bin(k; K, x) P_post(k), with P_post(k) measured in
  the randomized dose-response assay. Without memory, iterating x_{t+1} = f(x_t) gives the post-level epidemic; spread
  from a small seed grows geometrically iff f'(0) = K (P_post(1) - P_post(0)) > 1 (linearization at x=0).
- Hu et al.'s propagation factor R = k theta_1 / u_0 for their normalized map T/(T+U) is provided for comparison.
- Board R0 with memory: an infectious agent writes a pro-hack post with probability pi per round, each post is read by
  K susceptible agents on average (every agent reads K of ~N posts), each reader is infected with marginal probability
  h1 = P(1) - P(0), and the infectious period lasts D = 1/gamma rounds on average => R0 = pi * K * h1 * D.
  (Our derivation from the same branching logic; reported with bootstrap CIs.)
Global context: used by `analysis.py` for H3/H5 summaries.
"""

from __future__ import annotations  # forward references

import numpy as np  # numerics
from scipy.stats import binom  # binomial pmf


def f_map(x: np.ndarray, P_post: np.ndarray, K: int) -> np.ndarray:
    """f(x) = sum_{k=0}^{K} Bin(k; K, x) * P_post[k] (vectorized over x)."""
    x = np.atleast_1d(np.asarray(x, float))  # fractions of pro-hack posts
    k = np.arange(K + 1)  # exposure counts
    return binom.pmf(k[None, :], K, x[:, None]) @ np.asarray(P_post, float)  # mixture over k


def fprime0(P_post: np.ndarray, K: int) -> float:
    """Derivative of f at x=0: d/dx sum_k C(K,k) x^k (1-x)^(K-k) P_k |_{x=0} = K (P_1 - P_0)."""
    return float(K * (P_post[1] - P_post[0]))


def iterate_map(x0: float, P_post: np.ndarray, K: int, T: int) -> np.ndarray:
    """Trajectory x_0..x_T of the memoryless map."""
    xs = [x0]  # start
    for _ in range(T):
        xs.append(float(f_map(xs[-1], P_post, K)[0]))  # x_{t+1} = f(x_t)
    return np.array(xs)


def hu_R(theta1: float, u0: float, k: int) -> float:
    """Hu et al. (2026) propagation factor R = k * theta_1 / u_0."""
    return float(k * theta1 / u0)


def board_R0(pi: float, K: int, h1: float, gamma: float) -> float:
    """R0 = pi * K * h1 * D with D = 1/gamma (mean geometric infectious period in rounds)."""
    return float(pi * K * h1 / gamma) if gamma > 0 else float("inf")
