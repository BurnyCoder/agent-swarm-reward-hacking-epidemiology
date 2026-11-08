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
