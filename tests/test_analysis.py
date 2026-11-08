"""Unit tests for analysis-level estimators that the end-to-end pipeline test cannot exercise with its fake model."""

import numpy as np  # simulation
import pandas as pd  # data frame in the analysis format

from swarm_epi import analysis  # unit under test


def test_counter_contagion_recovers_flag_hazard_ratio():
    """Simulate flag onsets with a known cloglog effect of anti-hack posts read (HR = 1.5 per post) under randomized
    exposure (k_anti ~ Binomial(K, board share), E_anti = K * share) and check the estimate's 95% CI covers it while
    the pro-hack counts, which have no effect, stay near HR = 1."""
    rng = np.random.default_rng(0)
    rows, K, beta = [], 6, np.log(1.5)
    for run in range(16):
        for t in range(11):
            q_anti, q_pro = rng.uniform(0.1, 0.6), rng.uniform(0.0, 0.2)  # board composition of round t - 1
            for a in range(32):
                k_anti = rng.binomial(K, q_anti)
                k_pro = rng.binomial(K - k_anti, q_pro)
                eta = -2.0 + 0.05 * t + beta * k_anti  # baseline drift over rounds + causal effect
                rows.append({"condition": "MAIN" if run % 2 else "PLACEBO", "run": f"r{run}", "round": t,
                             "task": f"t{rng.integers(200)}", "prev_flag": bool(rng.random() < 0.4) if t else np.nan,
                             "flagged": bool(rng.random() < 1 - np.exp(-np.exp(eta))), "k_anti": k_anti,
                             "E_anti": K * q_anti, "k_seed_pro": 0, "k_nonseed_pro": k_pro, "E": K * q_pro,
                             "post_anti": False})
    out = analysis.counter_contagion(pd.DataFrame(rows))
    assert out["k_anti"]["hr_low"] < 1.5 < out["k_anti"]["hr_high"]
    assert out["k_nonseed_pro"]["hr_low"] < 1.0 < out["k_nonseed_pro"]["hr_high"]
    assert set(out["flag_rate_round0"]) == {"MAIN", "PLACEBO"}


def test_marginal_h1_averages_over_the_whole_risk_set():
    """Prereg §7.3: h1 is averaged over the risk set. Half the tasks are never hacked (true hazard 0), so their rows
    are dropped from the fixed-effects fit (no outcome variation) but still belong to the risk set, where one more
    post changes the hazard by 0. The estimate must match the risk-set average, about half the hackable-task effect."""
    from swarm_epi.epi import hazard
    rng = np.random.default_rng(1)
    rows, base, beta = [], -2.5, np.log(2.0)
    for run in range(24):
        for t in range(1, 11):
            for a in range(32):
                task = f"t{rng.integers(400)}"
                k = rng.binomial(6, 0.1)
                hackable = int(task[1:]) % 2 == 0
                p = 1 - np.exp(-np.exp(base + beta * k)) if hackable else 0.0
                rows.append({"run": f"r{run}", "round": t, "task": task, "y": int(rng.random() < p),
                             "k_seed_pro": 0, "k_nonseed_pro": k, "E": 0.6, "hackable": hackable})
    df = pd.DataFrame(rows)
    pr = lambda e: 1 - np.exp(-np.exp(e))
    truth = np.mean(np.where(df.hackable, pr(base + beta * (df.k_nonseed_pro + 1)) - pr(base + beta * df.k_nonseed_pro),
                             0.0))
    res = hazard.fit_cloglog(df, ["k_nonseed_pro"])
    assert res.n_dropped > 0.3 * len(df)
    assert abs(hazard.marginal_h1(res, "k_nonseed_pro") - truth) < 0.3 * truth
