"""Phenomenological growth curves for cumulative infections, fit by a conditional-binomial likelihood (descriptive H3).

Local context — models for cumulative count C(t) (closed forms):
- linear       C = C0 + a t                                   (constant incidence; generalized-growth p=0)
- exponential  C = C0 e^{rt}                                  (Ma et al. 2014, Bull Math Biol 76:245, Eq. 1)
- logistic     C = K / (1 + (K/C0 - 1) e^{-rt})               (Ma et al. 2014 Eq. 3; SI closed form)
- richards     C = K [1 + ((K/C0)^a - 1) e^{-a r t}]^{-1/a}    (Ma et al. 2014 Eqs. 4-5: C' = rC[1 - (C/K)^a];
               a = 1 is the logistic; initial rate r0 = r[1 - (C0/K)^a])
- gompertz     C = C0 exp((r/b)(1 - e^{-bt}))                 (integral of C' = r C e^{-bt})
- ggm          C = [C0^{1-p} + (1-p) r t]^{1/(1-p)}           (generalized growth C' = r C^p; Viboud, Simonsen &
                                                               Chowell 2016, Epidemics 15:27; Chowell 2017 Eq. 1)
- bass         C = C0 + (M-C0) F(t), F = (1-e^{-(a+b)t}) / (1 + (b/a) e^{-(a+b)t})   (Bass 1969, Management Science
               15:215: a = external/innovation, b = internal/imitation coefficient)
Likelihood: new_t ~ Binomial(N - C_obs(t-1), h_t), h_t = (C(t) - C(t-1)) / (N - C(t-1)) from the model trajectory —
interval incidence rather than correlated cumulative points (Ma et al. 2014 §2.3 motivates fitting increments).
Multiple runs can be pooled (shared parameters, summed log-likelihoods). AICc ranks models (Burnham & Anderson 2004).
Global context: reported descriptively; treated as evidence only if `identifiability` in the pilot shows >= 80%
correct selection at N=32, T=10 (prereg).
"""

from __future__ import annotations  # forward references

from collections.abc import Callable  # function type
from dataclasses import dataclass  # model/fit records

import numpy as np  # numerics
from scipy import optimize  # bounded MLE


@dataclass(frozen=True)
class Model:
    """Growth model: C(t; theta), parameter names, bounds builder, start builder."""

    f: Callable[[np.ndarray, list], np.ndarray]  # cumulative curve
    names: tuple[str, ...]  # parameter names
    bounds: Callable[[int], list]  # N -> bounds
    starts: Callable[[float, int], list]  # (C0_obs, N) -> list of starting points


def _ggm(t, th):
    c0, r, p = th  # initial size, rate, deceleration exponent
    if abs(1 - p) < 1e-6:  # p -> 1 limit is exponential
        return c0 * np.exp(r * t)
    return np.power(np.maximum(c0 ** (1 - p) + (1 - p) * r * t, 0.0), 1 / (1 - p))


def _richards(t, th):
    c0, r, k, a = th  # initial size, rate, ceiling, shape exponent
    base = 1 + ((k / c0) ** a - 1) * np.exp(-a * r * t)  # Ma et al. 2014 Eq. 5 denominator
    return k * np.power(np.maximum(base, 1e-12), -1 / a)


def _bass(t, th):
    c0, a, b, m = th  # initial adopters, innovation, imitation, ceiling
    e = np.exp(-(a + b) * t)  # decay term
    return c0 + (m - c0) * (1 - e) / (1 + (b / max(a, 1e-12)) * e)


MODELS = {
    "linear": Model(lambda t, th: th[0] + th[1] * t, ("C0", "a"),
                    lambda N: [(0, N), (0, N)], lambda c0, N: [[c0, 1.0], [c0, N / 10]]),
    "exponential": Model(lambda t, th: th[0] * np.exp(th[1] * t), ("C0", "r"),
                         lambda N: [(1e-3, N), (0, 5)], lambda c0, N: [[max(c0, .5), 0.3], [max(c0, .5), 1.0]]),
    "logistic": Model(lambda t, th: th[2] / (1 + (th[2] / th[0] - 1) * np.exp(-th[1] * t)), ("C0", "r", "K"),
                      lambda N: [(1e-3, N), (0, 10), (1e-3, N)],
                      lambda c0, N: [[max(c0, .5), 0.5, N * .8], [max(c0, .5), 1.5, N * .5]]),
    "richards": Model(_richards, ("C0", "r", "K", "a"), lambda N: [(1e-3, N), (0, 10), (1e-3, N), (0.05, 10)],
                      lambda c0, N: [[max(c0, .5), 0.8, N * .8, 1.0], [max(c0, .5), 1.5, N * .6, 0.5],
                                     [max(c0, .5), 0.5, N * .9, 3.0]]),
    "gompertz": Model(lambda t, th: th[0] * np.exp(th[1] / th[2] * (1 - np.exp(-th[2] * t))), ("C0", "r", "b"),
                      lambda N: [(1e-3, N), (0, 10), (1e-3, 10)],
                      lambda c0, N: [[max(c0, .5), 0.8, 0.3], [max(c0, .5), 2.0, 0.8]]),
    "ggm": Model(_ggm, ("C0", "r", "p"), lambda N: [(1e-3, N), (1e-4, 20), (0, 1)],
                 lambda c0, N: [[max(c0, .5), 0.5, 0.9], [max(c0, .5), 2.0, 0.5], [max(c0, .5), 5.0, 0.1]]),
    "bass": Model(_bass, ("C0", "a", "b", "M"), lambda N: [(0, N), (1e-6, 5), (0, 10), (1e-3, N)],
                  lambda c0, N: [[c0, 0.01, 0.5, N * .8], [c0, 0.1, 0.1, N * .6], [c0, 0.02, 1.5, N * .9]]),
}


@dataclass
class CurveFit:
    """Fit result."""

    name: str
    params: dict
    loglik: float
    n_params: int
    n_obs: int

    @property
    def aicc(self) -> float:
        """Small-sample AIC (Burnham & Anderson 2004)."""
        k, n = self.n_params, self.n_obs
        return -2 * self.loglik + 2 * k + 2 * k * (k + 1) / max(n - k - 1, 1)


def loglik(model: Model, th, C: np.ndarray, N: int) -> float:
    """Conditional-binomial log-likelihood of increments, summed over runs (rows of C)."""
    C = np.atleast_2d(C).astype(float)  # runs x (T+1)
    t = np.arange(C.shape[1], dtype=float)  # rounds 0..T
    m = np.clip(model.f(t, th), 0, N - 1e-6)  # model trajectory bounded by population size
    h = np.clip(np.diff(m) / np.maximum(N - m[:-1], 1e-9), 1e-9, 1 - 1e-9)  # per-round hazard
    n_sus = N - C[:, :-1]  # observed susceptibles at start of each round
    x = np.diff(C, axis=1)  # observed new infections
    return float(np.sum(x * np.log(h) + (n_sus - x) * np.log1p(-h)))


def fit(name: str, C: np.ndarray, N: int) -> CurveFit:
    """Bounded multi-start MLE of one model."""
    model = MODELS[name]  # model definition
    C = np.atleast_2d(C)  # pooled runs allowed
    c0 = float(np.mean(C[:, 0]))  # observed initial count
    best = None  # best optimizer result
    for th0 in model.starts(c0, N):  # multi-start
        th0 = [min(max(v, lo), hi) for v, (lo, hi) in zip(th0, model.bounds(N))]  # clip starts into bounds
        r = optimize.minimize(lambda th: -loglik(model, th, C, N), th0, method="L-BFGS-B", bounds=model.bounds(N))
        if best is None or r.fun < best.fun:
            best = r
    n_obs = int(C.shape[0] * (C.shape[1] - 1))  # number of increments
    return CurveFit(name, dict(zip(model.names, map(float, best.x))), -float(best.fun), len(best.x), n_obs)


def fit_all(C: np.ndarray, N: int) -> dict[str, CurveFit]:
    """Fit every growth model."""
    return {name: fit(name, C, N) for name in MODELS}


def initial_rate(fit_: CurveFit) -> float:
    """Identifiable initial growth rate r0 of a logistic or Richards fit (Ma et al. 2014, below Eq. 5).

    Logistic: r0 = r (1 - C0/K); Richards: r0 = r [1 - (C0/K)^a] (logistic is a = 1).
    """
    p = fit_.params
    a = p.get("a", 1.0)  # logistic has no shape parameter
    return float(p["r"] * (1 - (p["C0"] / p["K"]) ** a))


def doubling_time(r: float) -> float:
    """T_d = ln 2 / r (per round) for exponential growth rate r."""
    return float(np.log(2) / r) if r > 0 else float("inf")
