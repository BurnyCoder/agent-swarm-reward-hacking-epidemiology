"""Dose-response (exposure-curve) models for simple vs complex contagion, fit by maximum likelihood.

Local context — functional forms copied from the contagion literature:
- simple:   P(k) = 1 - (1-eps)(1-p)^k         independent exposures (Centola & Macy 2007, AJS 113:702; Reed-Frost)
- weibull:  P(k) = 1 - (1-eps) exp(-lam k^g)  g=1 reduces to simple (p = 1-e^-lam); g>1 synergy (complex),
                                              g<1 saturation; nested => likelihood-ratio test of g=1
- sigmoid:  P(k) = rl + (rh-rl)/(1+exp(-w(k-k0)))  complex-contagion threshold form (Mønsted et al. 2017,
                                              PLOS ONE 12:e0184148, https://doi.org/10.1371/journal.pone.0184148)
- saturated: one free probability per exposure level (Romero, Meeder & Kleinberg 2011 exposure curve p(k))
Model comparison by AICc (Burnham & Anderson 2004, https://doi.org/10.1177/0049124104268644) and LRT for nested pairs.
Global context: used on the randomized dose-response assay (H4) and to build the infection kernel for the
chain-binomial simulator (H5).
"""

from __future__ import annotations  # forward references

from collections.abc import Callable  # model function type
from dataclasses import dataclass  # fit record

import numpy as np  # numerics
from scipy import optimize, stats  # MLE + chi-square tail
from scipy.special import expit  # logistic transform for (0,1) parameters

EPS = 1e-9  # probability clipping to keep log-likelihood finite


@dataclass
class Fit:
    """Result of one maximum-likelihood fit."""

    name: str  # model name
    params: dict  # natural-scale parameters
    loglik: float  # maximized binomial log-likelihood (without the combinatorial constant)
    n_params: int  # number of free parameters
    n_obs: int  # number of Bernoulli trials
    predict: Callable[[np.ndarray], np.ndarray]  # P(k) at the MLE

    @property
    def aicc(self) -> float:
        """AICc = -2 logL + 2K + 2K(K+1)/(n-K-1) (Burnham & Anderson 2004, Eq. for small samples)."""
        k, n = self.n_params, self.n_obs
        return -2 * self.loglik + 2 * k + 2 * k * (k + 1) / max(n - k - 1, 1)

    @property
    def bic(self) -> float:
        """BIC = -2 logL + K ln n."""
        return -2 * self.loglik + self.n_params * np.log(self.n_obs)


def _aggregate(k: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Collapse Bernoulli data to (levels, successes, trials) per exposure level — same likelihood, faster."""
    levels = np.unique(k)  # distinct exposure counts
    s = np.array([y[k == v].sum() for v in levels], float)  # successes per level
    n = np.array([(k == v).sum() for v in levels], float)  # trials per level
    return levels.astype(float), s, n


def _ll(prob: np.ndarray, s: np.ndarray, n: np.ndarray) -> float:
    """Binomial log-likelihood sum s log P + (n-s) log(1-P)."""
    p = np.clip(prob, EPS, 1 - EPS)  # numerical safety
    return float(np.sum(s * np.log(p) + (n - s) * np.log1p(-p)))


# Each model: (unconstrained-parameter -> P(k) function builder, natural-parameter mapper, list of starts)
def _simple(th):
    eps, p = expit(th[0]), expit(th[1])  # both in (0,1)
    return (lambda k: 1 - (1 - eps) * (1 - p) ** k), {"eps": eps, "p": p}


def _weibull(th):
    eps, lam, g = expit(th[0]), np.exp(th[1]), np.exp(th[2])  # lam, g > 0
    return (lambda k: 1 - (1 - eps) * np.exp(-lam * np.power(k, g))), {"eps": eps, "lam": lam, "gamma": g}


def _sigmoid(th):
    rl, rh, w, k0 = expit(th[0]), expit(th[1]), np.exp(th[2]), th[3]  # floor, ceiling, steepness, threshold
    return (lambda k: rl + (rh - rl) / (1 + np.exp(-w * (k - k0)))), {"rl": rl, "rh": rh, "w": w, "k0": k0}


MODELS = {
    "simple": (_simple, [[-3, -2], [-1, -1], [-4, 0]]),
    "weibull": (_weibull, [[-3, -2, 0], [-3, -1, 0.7], [-2, -3, -0.5], [-4, -2, 1.2]]),
    "sigmoid": (_sigmoid, [[-3, 0, 0, 2], [-3, -1, 1, 3], [-2, 1, -0.5, 1], [-4, 0.5, 1.5, 4]]),
}


def fit_model(name: str, k: np.ndarray, y: np.ndarray) -> Fit:
    """MLE of one parametric model with multiple Nelder-Mead starts (best log-likelihood kept)."""
    levels, s, n = _aggregate(np.asarray(k), np.asarray(y))  # sufficient statistics
    builder, starts = MODELS[name]  # model definition
    best = None  # best optimizer result
    for th0 in starts:  # multi-start to avoid local optima
        nll = lambda th: -_ll(builder(th)[0](levels), s, n)
        r = optimize.minimize(nll, np.array(th0, float), method="Nelder-Mead",
                              options={"maxiter": 20000, "xatol": 1e-8, "fatol": 1e-10})
        if best is None or r.fun < best.fun:
            best = r
    fn, params = builder(best.x)  # MLE function and parameters
    return Fit(name, {k_: float(v) for k_, v in params.items()}, -float(best.fun), len(best.x), int(n.sum()),
               lambda kk, fn=fn: fn(np.asarray(kk, float)))


def fit_saturated(k: np.ndarray, y: np.ndarray) -> Fit:
    """Saturated exposure curve: empirical P at each level (Romero et al. 2011 p(k))."""
    levels, s, n = _aggregate(np.asarray(k), np.asarray(y))
    phat = s / n  # MLE per level
    table = dict(zip(levels, phat))  # level -> probability
    return Fit("saturated", {f"p{int(v)}": float(p) for v, p in table.items()}, _ll(phat, s, n), len(levels),
               int(n.sum()), lambda kk: np.array([table.get(float(x), np.nan) for x in np.atleast_1d(kk)]))


def fit_all(k: np.ndarray, y: np.ndarray) -> dict[str, Fit]:
    """Fit simple, Weibull, sigmoid and saturated models."""
    out = {name: fit_model(name, k, y) for name in MODELS}  # parametric fits
    out["saturated"] = fit_saturated(k, y)  # nonparametric reference
    return out


def lrt(small: Fit, big: Fit) -> dict:
    """Likelihood-ratio test for nested models: 2(llB - llS) ~ chi2(df = KB - KS) (Wilks)."""
    stat = max(2 * (big.loglik - small.loglik), 0.0)  # non-negative by nesting
    df = big.n_params - small.n_params  # degrees of freedom
    return {"stat": stat, "df": df, "p_value": float(stats.chi2.sf(stat, df))}
