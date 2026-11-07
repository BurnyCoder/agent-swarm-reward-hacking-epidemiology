"""Discrete-time hazard model of infection with randomized exposure counts (confirmatory test H2).

Local context: complementary log-log binomial GLM, the standard grouped-time proportional-hazards model
(Prentice & Gloeckler 1978, Biometrics 34:57; Allison 1982, Sociological Methodology 13:61):
    P(infected in round t | susceptible) = 1 - exp(-exp(alpha_t + b_seed * k_seed + b_nonseed * k_nonseed)),
where k_* count pro-hack posts the agent read this round, split by author type, and alpha_t are round fixed effects
(absorbing time trends such as frustration from repeated impossible tasks). Because the board sampler randomizes which
posts an agent reads, k_* are exogenous given the board composition, so b_nonseed > 0 is causal evidence of SECONDARY
transmission (non-seed agents infecting others). Standard errors are cluster-robust by run (runs are the independent
units), via statsmodels `GLM(..., family=Binomial(link=CLogLog())).fit(cov_type="cluster")`.
Global context: `analysis.py` builds the agent-round table (susceptible = not hacking in the previous round).
"""

from __future__ import annotations  # forward references

import numpy as np  # numerics
import pandas as pd  # design matrices
import statsmodels.api as sm  # GLM


def fit_cloglog(df: pd.DataFrame, exposure_cols: list[str], round_fe: bool = True, extra_cols: list[str] = ()):
    """Fit the cloglog hazard GLM; `df` needs columns y (0/1), run, round and the exposure/extra columns."""
    X = df[list(exposure_cols) + list(extra_cols)].astype(float)  # exposure covariates
    if round_fe:  # round fixed effects (one dummy per round, no global intercept)
        X = pd.concat([X, pd.get_dummies(df["round"], prefix="round", dtype=float)], axis=1)
    else:
        X = sm.add_constant(X)  # global intercept
    model = sm.GLM(df["y"].astype(float), X, family=sm.families.Binomial(link=sm.families.links.CLogLog()))
    groups = pd.factorize(df["run"])[0]  # integer cluster ids
    return model.fit(cov_type="cluster", cov_kwds={"groups": groups})  # cluster-robust (sandwich) covariance


def hazard_ratio(res, col: str) -> dict:
    """Hazard ratio exp(b) per additional post, with 95% CI and one-sided p (H: b > 0)."""
    b, se = float(res.params[col]), float(res.bse[col])  # estimate + robust SE
    z = b / se  # Wald statistic
    from scipy.stats import norm  # normal tail

    return {"beta": b, "se": se, "hr": float(np.exp(b)), "hr_low": float(np.exp(b - 1.96 * se)),
            "hr_high": float(np.exp(b + 1.96 * se)), "p_one_sided": float(norm.sf(z))}
