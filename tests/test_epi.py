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
    res = hazard.fit_cloglog(df, ["k_seed", "k_nonseed"])
    assert abs(res.params["k_nonseed"] - 0.4) < 0.08 and res.pvalues["k_nonseed"] < 1e-6
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
    zero = simulate.simulate(N=32, K=6, T=10, n_seeds=0, infect=lambda k: 0.0 * k, recover=0.2, pi=1.0, rng=rng)
    assert zero.sum() == 0
    spread = simulate.simulate_many(N=32, K=6, T=10, n_seeds=2, infect=lambda k: 1 - 0.9 ** k, recover=0.1,
                                    pi=0.8, reps=200, rng=rng)
    assert spread[:, -1].mean() > spread[:, 1].mean()


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
