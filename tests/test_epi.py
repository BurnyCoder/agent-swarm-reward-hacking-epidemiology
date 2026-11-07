"""Parameter-recovery and calibration tests for the epidemic statistics (simulate with known truth, fit, compare)."""

import numpy as np  # simulation
import pandas as pd  # hazard-table construction

from swarm_epi.epi import curves, dose, hazard, simulate, stats, transmission  # units under test


def sim_dose(prob_fn, ks, n_per_k, seed=0):
    """Bernoulli outcomes at exposure levels `ks` with success probability prob_fn(k)."""
    rng = np.random.default_rng(seed)
    k = np.repeat(ks, n_per_k)
    return k, (rng.random(k.size) < prob_fn(k)).astype(int)


def test_simple_contagion_recovered_and_weibull_gamma_near_one():
    eps, p = 0.05, 0.15
    k, y = sim_dose(lambda k: 1 - (1 - eps) * (1 - p) ** k, np.array([0, 1, 2, 3, 4, 6]), 2000)
    fits = dose.fit_all(k, y)
    assert abs(fits["simple"].params["eps"] - eps) < 0.02 and abs(fits["simple"].params["p"] - p) < 0.02
    lrt = dose.lrt(fits["simple"], fits["weibull"])  # nested: weibull gamma=1 is simple
    assert lrt["p_value"] > 0.01  # truth is simple => no strong rejection
    assert 0.8 < fits["weibull"].params["gamma"] < 1.25


def test_complex_contagion_detected():
    # Threshold-like sigmoid in k (Mønsted et al. 2017 form): low below k0=3, high above.
    k, y = sim_dose(lambda k: 0.03 + 0.6 / (1 + np.exp(-3 * (k - 3))), np.array([0, 1, 2, 3, 4, 6]), 1500, seed=1)
    fits = dose.fit_all(k, y)
    assert fits["weibull"].params["gamma"] > 1.5  # synergy
    assert fits["sigmoid"].aicc < fits["simple"].aicc - 10


def test_hazard_glm_recovers_positive_exposure_effect_and_null_under_permutation():
    rng = np.random.default_rng(2)
    n = 20000
    df = pd.DataFrame({"run": rng.integers(0, 20, n), "round": rng.integers(1, 11, n),
                       "k_seed": rng.binomial(6, 0.06, n), "k_nonseed": rng.binomial(6, 0.2, n)})
    eta = -3.0 + 0.5 * df.k_seed + 0.4 * df.k_nonseed  # cloglog linear predictor
    df["y"] = (rng.random(n) < 1 - np.exp(-np.exp(eta))).astype(int)
    res = hazard.fit_cloglog(df, ["k_seed", "k_nonseed"])  # round + run fixed effects (no task column here)
    hr = hazard.hazard_ratio(res, "k_nonseed")
    assert abs(hr["beta"] - 0.4) < 0.08 and hr["p_one_sided"] < 1e-6
    chk = hazard.statsmodels_check(df, ["k_seed", "k_nonseed"])  # IRLS == statsmodels GLM (estimates and SEs)
    assert np.allclose(chk.sm_beta, chk.irls_beta, atol=1e-5) and np.allclose(chk.sm_se, chk.irls_se, rtol=1e-3)
    df["y"] = df.groupby("round")["y"].transform(lambda s: rng.permutation(s.values))  # random control
    res0 = hazard.fit_cloglog(df, ["k_seed", "k_nonseed"])
    assert abs(res0.params["k_nonseed"]) < 0.08


def test_growth_curve_selection_prefers_logistic_on_logistic_data():
    N, T = 200, 12
    true = curves.MODELS["logistic"].f(np.arange(T + 1), [2.0, 0.8, 180.0])  # C0, r, K
    rng = np.random.default_rng(3)
    c = [2]
    for t in range(1, T + 1):  # conditional binomial increments
        h = max(true[t] - true[t - 1], 0) / (N - true[t - 1])
        c.append(c[-1] + rng.binomial(N - c[-1], min(max(h, 0), 1)))
    fits = curves.fit_all(np.array(c), N)
    best = min(fits, key=lambda m: fits[m].aicc)
    assert best in ("logistic", "bass", "ggm", "gompertz") and fits["linear"].aicc > fits["logistic"].aicc + 4


def test_transmission_map_derivative():
    P_post = np.array([0.02, 0.30, 0.45, 0.55, 0.6, 0.62, 0.65])  # P(own post pro | k), k=0..6
    assert np.isclose(transmission.fprime0(P_post, K=6), 6 * (0.30 - 0.02))
    x = np.linspace(0, 1, 11)
    fx = transmission.f_map(x, P_post, K=6)
    assert np.isclose(fx[0], 0.02) and np.isclose(fx[-1], 0.65)


def test_simulator_no_seed_no_background_stays_zero_and_seeds_spread():
    rng = np.random.default_rng(4)
    zero = simulate.simulate(rng, N=32, K=6, T=10, n_seeds=0, infect=lambda k: 0.0 * k, recover=0.2, pi_h=1.0)
    assert zero.sum() == 0
    spread = simulate.simulate_many(200, rng, N=32, K=6, T=10, n_seeds=2, infect=lambda k: 1 - 0.9 ** k,
                                    recover=0.1, pi_h=0.8)
    assert spread[:, -1].mean() > spread[:, 1].mean()
    cum = simulate.simulate_many(50, rng, N=32, K=6, T=10, n_seeds=2, infect=lambda k: 1 - 0.9 ** k, recover=0.5,
                                 pi_h=0.8, cumulative=True)
    assert (np.diff(cum, axis=1) >= 0).all()  # cumulative incidence never decreases


def test_simulator_exposure_matches_hypergeometric():
    # With only the 2 seed posts pro-hack, P(read >= 1 seed post) = 1 - C(31,6)/C(33,6) ~= 0.335 (prereg §2.1).
    rng = np.random.default_rng(9)
    hit = simulate.simulate_many(4000, rng, N=32, K=6, T=1, n_seeds=2, infect=lambda k: (np.asarray(k) > 0) * 1.0,
                                 recover=0.0, pi_h=0.0)[:, 1] / 32
    assert abs(hit.mean() - (1 - (27 * 26) / (33 * 32))) < 0.01


def test_fixed_points_and_regimes():
    low = np.array([0.02, 0.05, 0.08, 0.1, 0.12, 0.13, 0.14])  # R_map = 6*0.03 < 1
    assert transmission.regime(low, 6)["regime"] == "monostable_low"
    sup = np.array([0.02, 0.3, 0.5, 0.6, 0.7, 0.75, 0.8])  # R_map = 6*0.28 > 1
    assert transmission.regime(sup, 6)["regime"] == "supercritical"
    k = np.arange(7)
    bis = 0.01 + 0.95 / (1 + np.exp(-3 * (k - 3.5)))  # steep threshold: low and high stable states
    r = transmission.regime(bis, 6)
    assert r["regime"] == "bistable" and sum(p["stable"] for p in r["fixed_points"]) == 2


def test_profile_ci_and_akaike_weights():
    eps, p = 0.05, 0.15
    k, y = sim_dose(lambda k: 1 - (1 - eps) * (1 - p) ** k, np.array([0, 1, 2, 3, 4, 6]), 1500, seed=3)
    ci = dose.profile_ci_gamma(k, y)
    assert ci["ci"][0] < 1 < ci["ci"][1]  # truth gamma = 1 inside the profile CI
    w = dose.akaike_weights(dose.fit_all(k, y))
    assert abs(sum(w.values()) - 1) < 1e-9


def test_stats_bootstrap_permutation_and_tost():
    rng = np.random.default_rng(5)
    a, b = rng.normal(0.3, 0.1, 20), rng.normal(0.1, 0.1, 20)
    out = stats.compare_runs(a, b, sesoi=0.10, rng=rng)
    assert out["diff"] > 0.1 and out["p_perm"] < 0.01 and out["ci_low"] > 0
    same = stats.compare_runs(rng.normal(0.1, 0.02, 30), rng.normal(0.1, 0.02, 30), sesoi=0.10, rng=rng)
    assert same["p_tost"] < 0.05  # equivalence within +-10 pp
    assert np.allclose(stats.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])  # Holm 1979: 3*.01, 2*.03, max(1*.04, .06)
    ens, y = rng.normal(0, 1, 5000), 0.0
    assert abs(stats.crps_ensemble(ens, y) - 0.2337) < 0.02  # CRPS of N(0,1) at 0 = (sqrt(2)-1)/sqrt(pi)


def test_power_and_identifiability_run_and_are_sane():
    from swarm_epi.epi import power
    strong = power.h1_power(eps=0.05, h1=0.2, recover=0.2, pi_h=0.8, n_sim=30)
    null = power.h1_power(eps=0.05, h1=0.0, recover=0.2, pi_h=0.8, n_sim=30)
    assert strong["power"] > 0.8 and null["power"] < 0.2 and null["tost_power"] > 0.5
    ident = power.identifiability(n_runs=10, n_sim=3)
    assert set(ident["per_family"]) == set(power.DEFAULT_PARAMS)


def test_paired_comparison():
    rng = np.random.default_rng(1)
    base = rng.normal(0.1, 0.05, 20)
    out = stats.compare_paired(base + 0.15 + rng.normal(0, 0.02, 20), base, sesoi=0.10, rng=rng,
                               covariate=rng.normal(0, 0.01, 20))
    assert out["p_signflip"] < 1e-4 and out["ci_low"] > 0.1 and "p_signflip_adjusted" in out
    eq = stats.compare_paired(base + rng.normal(0, 0.01, 20), base, sesoi=0.10, rng=rng)
    assert eq["p_tost_paired"] < 0.05
    pmf = stats.pmf_from_samples(np.array([3, 3, 4]), 5)
    assert abs(pmf.sum() - 1) < 1e-12 and stats.crps_star(pmf, 3) < stats.crps_star(pmf, 0)
