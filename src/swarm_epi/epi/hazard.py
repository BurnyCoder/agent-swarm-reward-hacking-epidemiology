"""Discrete-time hazard model of infection with randomized exposure counts (confirmatory test H2, prereg §9.2).

Local context: complementary log-log binomial GLM, the grouped-time proportional-hazards model (Prentice & Gloeckler
1978, Biometrics 34:57; Allison 1982, Sociological Methodology 13:61):
    log(-log(1 - h_irt)) = alpha_t + u_r + v_task + b_s S_irt + b_n M_irt + b_e E_rt,
S = seed pro-hack posts read, M = non-seed judge-pro-hack posts read, E = expected M given the round-(t-1) board
(K x share of non-seed pro-hack posts among the posts the agent could sample). Given the board, M is randomized by the
sampler; conditioning on E removes confounding by board composition (Borusyak & Hull 2023, Econometrica 91:2155).
Fixed-effect levels whose outcomes are all 0 (or all 1) carry no information about the slopes and make the MLE
diverge; like R's fixest for binomial models they are dropped before fitting (reported as n_dropped).
Fit: statsmodels GLM Binomial(link=CLogLog()) with run-clustered sandwich covariance. Because the CLogLog docstring
says "untested", `direct_mle` cross-checks a fit by maximizing the same likelihood with scipy.
Global context: `analysis.py` H2, R0's h1, and the permutation random control.
"""

from __future__ import annotations  # forward references

import numpy as np  # numerics
import pandas as pd  # design matrices
import statsmodels.api as sm  # GLM
from scipy import optimize, sparse  # direct MLE cross-check, sparse design
from scipy.stats import norm  # one-sided Wald p-values


def _drop_constant_groups(df: pd.DataFrame, fe: list[str]) -> tuple[pd.DataFrame, int]:
    """Iteratively drop rows of FE levels with no outcome variation (fixest-style)."""
    n0 = len(df)
    changed = True
    while changed:  # dropping one FE's levels can make another FE's levels constant
        changed = False
        for col in fe:
            var = df.groupby(col)["y"].transform(lambda s: s.nunique() > 1)  # level has both 0s and 1s
            if not var.all():
                df, changed = df[var], True
    return df, n0 - len(df)


def design(df: pd.DataFrame, slopes: list[str], fe: list[str]) -> pd.DataFrame:
    """Slopes + one-hot fixed effects (first FE complete, later FEs drop their first level to avoid collinearity)."""
    parts = [df[slopes].astype(float)]
    for i, col in enumerate(fe):
        parts.append(pd.get_dummies(df[col].astype(str), prefix=col, dtype=float, drop_first=i > 0))
    return pd.concat(parts, axis=1)


class FastResult:
    """Minimal results object (params, bse as pandas Series) mirroring the statsmodels attributes we use."""

    def __init__(self, params: pd.Series, bse: pd.Series, design_frame: pd.DataFrame, n_dropped: int, n_iter: int):
        self.params, self.bse, self.design_frame = params, bse, design_frame  # estimates, robust SEs, design
        self.n_dropped, self.n_iter = n_dropped, n_iter  # bookkeeping


def irls_cloglog(X: np.ndarray, y: np.ndarray, groups: np.ndarray, tol: float = 1e-10, max_iter: int = 200):
    """Cloglog Bernoulli GLM by iteratively reweighted least squares (normal equations) + cluster-robust covariance.

    IRLS (McCullagh & Nelder 1989, §2.5): mu = 1 - exp(-e^eta), dmu/deta = e^eta exp(-e^eta), working weight
    w = (dmu/deta)^2 / (mu (1 - mu)), working response z = eta + (y - mu)/(dmu/deta); solve (X'WX) b = X'Wz.
    Sandwich: V = B^-1 M B^-1 with B = observed information and M = sum_g s_g s_g', s_g = sum_{i in g} x_i (y_i - mu_i) dmu_i /
    (mu_i (1 - mu_i)), times statsmodels' default small-sample factor G/(G-1) * (n-1)/(n-p).
    """
    Xs = sparse.csr_matrix(X)  # one-hot FE columns are sparse: X'WX in O(nnz) instead of dense BLAS

    def moments(eta):
        e = np.exp(np.clip(eta, -30, 3.0))  # e^eta, bounded (mu saturates near 1 beyond eta = 3)
        mu = np.clip(1 - np.exp(-e), 1e-10, 1 - 1e-10)  # mean
        dmu = np.maximum(e * np.exp(-e), 1e-10)  # derivative of the inverse link
        return mu, dmu

    def deviance(eta):
        mu, _ = moments(eta)
        return -2 * np.sum(y * np.log(mu) + (1 - y) * np.log1p(-mu))

    mu0 = (y + 0.5) / 2  # R glm.fit / statsmodels binomial starting values
    eta = np.log(-np.log(1 - mu0))  # cloglog link of the start
    beta, dev_old = None, deviance(eta)
    for it in range(1, max_iter + 1):
        mu, dmu = moments(eta)
        w = dmu**2 / (mu * (1 - mu))  # IRLS weights
        z = eta + (y - mu) / dmu  # working response
        A = (Xs.T.multiply(w)) @ Xs  # X'WX (sparse)
        new = np.linalg.solve(A.toarray(), Xs.T @ (w * z))  # normal equations
        eta_new = Xs @ new
        dev = deviance(eta_new)
        halvings = 0
        while beta is not None and dev > dev_old + 1e-9 and halvings < 30:  # step-halving (R glm.fit)
            new = (new + beta) / 2
            eta_new = Xs @ new
            dev, halvings = deviance(eta_new), halvings + 1
        beta, eta = new, eta_new
        if abs(dev_old - dev) < tol * (abs(dev) + 0.1):  # R's convergence criterion form
            break
        dev_old = dev
    mu, dmu = moments(eta)
    # Bread = inverse OBSERVED information, as statsmodels uses for GLM sandwiches (verified numerically). With
    # u = e^eta, q = e^-u: d2 loglik/d eta2 = y u q (1 - q - u)/(1 - q)^2 - (1 - y) u (our derivation).
    u = np.exp(np.clip(eta, -30, 3.0))
    q = np.exp(-u)
    d2 = y * u * q * (1 - q - u) / np.maximum((1 - q) ** 2, 1e-20) - (1 - y) * u  # per-row second derivative
    Binv = np.linalg.inv(((Xs.T.multiply(-d2)) @ Xs).toarray())  # inverse observed information
    score = Xs.multiply(((y - mu) * dmu / (mu * (1 - mu)))[:, None]).tocsr()  # per-row score contributions
    S = (sparse.csr_matrix((np.ones(len(groups)), (groups, np.arange(len(groups))))) @ score).toarray()  # by cluster
    G, n, p = S.shape[0], X.shape[0], X.shape[1]
    V = Binv @ (S.T @ S) @ Binv * (G / (G - 1)) * ((n - 1) / (n - p))  # cluster-robust covariance
    return beta, np.sqrt(np.diag(V)), it


def fit_cloglog(df: pd.DataFrame, slopes: list[str], fe: tuple[str, ...] = ("round", "run", "task")) -> FastResult:
    """Fit the cloglog hazard model; `df` needs y (0/1), run, the FE columns and the slope columns."""
    fe = [c for c in fe if c in df.columns]  # allow reduced models
    d, n_dropped = _drop_constant_groups(df.copy(), [c for c in fe if c != "round"])  # never drop rounds
    X = design(d, slopes, fe) if fe else sm.add_constant(d[slopes].astype(float))  # design matrix
    beta, se, it = irls_cloglog(X.values, d["y"].values.astype(float), pd.factorize(d["run"])[0])
    return FastResult(pd.Series(beta, X.columns), pd.Series(se, X.columns), X, n_dropped, it)


def statsmodels_check(df: pd.DataFrame, slopes: list[str], fe: tuple[str, ...] = ("round", "run")) -> pd.DataFrame:
    """Same model through statsmodels GLM(Binomial(CLogLog)) with run-clustered covariance — validation of
    `irls_cloglog` (estimates and SEs must agree)."""
    d, _ = _drop_constant_groups(df.copy(), [c for c in fe if c != "round"])
    X = design(d, slopes, list(fe))
    sm_res = sm.GLM(d["y"].astype(float), X, family=sm.families.Binomial(link=sm.families.links.CLogLog())).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d["run"])[0]})
    ours = fit_cloglog(df, slopes, fe)
    return pd.DataFrame({"sm_beta": sm_res.params[slopes], "irls_beta": ours.params[slopes],
                         "sm_se": sm_res.bse[slopes], "irls_se": ours.bse[slopes]})


def hazard_ratio(res, col: str) -> dict:
    """Hazard ratio exp(b) per post with 95% CI, one-sided p (H: b > 0) and the 90% CI of b."""
    b, se = float(res.params[col]), float(res.bse[col])  # estimate + robust SE
    return {"beta": b, "se": se, "hr": float(np.exp(b)), "hr_low": float(np.exp(b - 1.96 * se)),
            "hr_high": float(np.exp(b + 1.96 * se)), "beta_ci90": [b - 1.645 * se, b + 1.645 * se],
            "p_one_sided": float(norm.sf(b / se))}


def marginal_h1(res, col: str) -> float:
    """Average marginal increase in hazard from one more post: mean over the risk set of P(eta+b) - P(eta),
    with P(eta) = 1 - exp(-exp(eta)) (prereg §7.3)."""
    eta = res.design_frame.values @ res.params.values  # linear predictor per row
    p = lambda e: 1 - np.exp(-np.exp(e))  # noqa: E731 - inverse cloglog
    return float(np.mean(p(eta + res.params[col]) - p(eta)))


def direct_mle(df: pd.DataFrame, slopes: list[str], fe: tuple[str, ...] = ("round",)) -> pd.Series:
    """Maximize the cloglog Bernoulli likelihood directly (BFGS) — cross-check of the statsmodels fit."""
    X = design(df, slopes, list(fe)).values  # small design (round FE + slopes)
    y = df["y"].values.astype(float)

    def nll(beta):
        eta = np.clip(X @ beta, -30, 5)  # numerically safe range
        p = np.clip(1 - np.exp(-np.exp(eta)), 1e-12, 1 - 1e-12)
        return -np.sum(y * np.log(p) + (1 - y) * np.log1p(-p))

    r = optimize.minimize(nll, np.full(X.shape[1], -2.0), method="BFGS")
    return pd.Series(r.x, index=design(df, slopes, list(fe)).columns)
