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


def test_h4_offtopic_tost_reports_a_p_value():
    """The content control (k = 6 off-topic posts vs k = 0) must report a TOST p-value in [0, 1], and with equal true
    rates and 400 trials per arm it must declare equivalence within +-10 pp (a z statistic of ~6 would not be in [0, 1])."""
    rng = np.random.default_rng(2)
    rows = [{"variant": "distinct", "j": 0, "k": k, "hack_attempt": bool(rng.random() < 0.05 + 0.05 * k),
             "post_pro": float(rng.random() < 0.05 + 0.05 * k)} for k in (0, 1, 2, 3, 4, 6) for _ in range(400)]
    rows += [{"variant": "offtopic", "j": 0, "k": 6, "hack_attempt": bool(rng.random() < 0.05),
              "post_pro": float(rng.random() < 0.05)} for _ in range(400)]
    p = analysis.h4(pd.DataFrame(rows), rng, n_boot=5)["comparisons"]["offtopic_k6_tost_p"]
    assert 0.0 <= p < 0.05


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


def test_week1_conditions_pair_with_batch1_replicates():
    """Each W1 condition changes exactly its preregistered factor and reuses replicate ids 0..n-1 (CRN pairs)."""
    from swarm_epi import conditions
    runs = conditions.week1("B", n=3)
    assert len(runs) == 6 * 3 and {r.replicate for r in runs} == {0, 1, 2}
    by = {r.condition: r for r in runs if r.replicate == 0}
    assert set(by) == set(conditions.WEEK1_PARTNERS)
    assert not by["MEMOFF_MAIN"].memory and by["MEMOFF_PLACEBO"].seed_pool == "placebo"
    assert (by["M4"].n_seeds, by["M8"].n_seeds, by["NOSEED"].n_seeds) == (4, 8, 0)
    assert by["INOC"].inoculation and by["INOC"].seed_pool == "hack" and by["M8"].memory


def test_week1_contrasts_recover_a_paired_difference():
    """Synthetic W1 data: INOC halves the partner's hack rate, the other ablations change nothing. The INOC contrast
    must be negative with a CI excluding 0, a null contrast's CI must cover 0, and every Holm p must be in [0, 1]."""
    from swarm_epi import conditions
    rng = np.random.default_rng(3)
    rows = []
    rates = {"MAIN": 0.10, "PLACEBO": 0.10, "INOC": 0.05}  # conditions not listed use 0.10
    for cond in list(conditions.WEEK1_PARTNERS) + ["MAIN", "PLACEBO"]:
        for rep in range(10):
            for t in range(11):
                for a in range(32):
                    rows.append({"condition": cond, "replicate": rep, "run_id": f"{cond}_r{rep}", "round": t,
                                 "hack_attempt": rng.random() < rates.get(cond, 0.10), "flagged": rng.random() < 0.5})
    out = analysis.week1_contrasts(pd.DataFrame(rows), conditions.WEEK1_PARTNERS, rng)
    inoc, m4 = out["contrasts"]["INOC"]["hack"], out["contrasts"]["M4"]["hack"]
    assert inoc["ci_high"] < 0 and m4["ci_low"] < 0 < m4["ci_high"]
    assert all(0 <= v <= 1 for k, v in out["holm_hack"].items() if k != "family_complete")
    assert "m8_late_minus_early" in out and out["holm_hack"]["family_complete"]
