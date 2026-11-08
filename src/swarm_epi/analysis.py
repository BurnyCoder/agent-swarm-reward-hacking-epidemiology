"""Pre-registered analysis (reports/preregistration.md §9): reads results files only, writes every number/table.

Local context — estimator per hypothesis:
- H1 (§9.1): run-level mean non-seed hack-attempt prevalence over rounds 1..10; MAIN vs PLACEBO over CRN pairs: exact
  sign-flip test (primary), Welch and round-0-adjusted tests (robustness), pair-bootstrap CI, paired/Welch TOST.
- H2 (§9.2): cloglog hazard on susceptible agent-rounds (not hacking in t-1) of all conditions, slopes S (seed
  pro-hack posts read), M (non-seed judge-pro-hack posts read), E (expected M given the board), fixed effects round,
  run, task, run-clustered SEs; one-sided Wald test of beta_M > 0. Robustness: cluster bootstrap over runs within
  condition, run x round FE instead of E, author-hack-status exposure, first-ever-hack risk set. Random control:
  1,000 within run x round label permutations (§9.7).
- H4 (§9.3): simple / Weibull / sigmoid on the assay's j=0 distinct cells; LRT of gamma = 1; AICc + Akaike weights;
  profile CI of gamma; falsification bootstrap; Dodds-Watts superadditivity; same-vs-distinct; anti posts; content
  control with TOST.
- Holm over {H1, H2, H4} (§9.6).
- H3 (§9.4): TRANSIENT vs PLACEBO late window (rounds 8-10) sign-flip + TOST, logit slope over rounds 3-10, R0 =
  pi K~ h1 D and R_map = K(q1 - q0) with regime, bootstrap CIs, three-way decision; descriptive growth curves.
- H5 (§9.5): assay-calibrated simulator (pilot recovery, PLACEBO baseline) vs broadcast-only and leave-one-run-out
  logistic; CRPS* and log score on counts; sign-flip test over runs; 90% interval coverage.
Global context: `scripts/analyze.py` runs `run_all`; `figures.py` / `site.py` read results/summary.json.
"""

from __future__ import annotations  # forward references

import ast  # unparseable-output rate
import json  # IO
from pathlib import Path  # paths

import numpy as np  # numerics
import pandas as pd  # tables
from scipy import optimize  # LOO logistic baseline
from scipy.special import expit, logit  # logistic transforms
from scipy.stats import binom  # binomial predictive pmf
from statsmodels.stats.proportion import tost_proportions_2indep  # content-control TOST

from .epi import curves, dose, hazard, simulate, stats, transmission  # statistics

RNG_SEED = 20261107  # analysis RNG seed
K, N, M_SEEDS = 6, 32, 2  # design constants (prereg §2.1)


# ============================================================================================ loading / exposure
def load_runs(batch_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """rounds.jsonl (agent-rounds) and board.jsonl (posts) of every COMPLETED run in `batch_dir`."""
    recs, posts = [], []
    for d in sorted(p for p in batch_dir.iterdir() if (p / "state.json").exists()):
        if not json.loads((d / "state.json").read_text(encoding="utf-8")).get("done"):
            continue  # only completed runs enter the analysis (prereg §9.8)
        cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
        recs += [json.loads(x) for x in (d / "rounds.jsonl").read_text(encoding="utf-8").splitlines() if x]
        posts += [json.loads(x) | {"run_id": d.name, "condition": cfg["condition"], "replicate": cfg["replicate"]}
                  for x in (d / "board.jsonl").read_text(encoding="utf-8").splitlines() if x]
    return pd.DataFrame(recs), pd.DataFrame(posts)


def label_of(labels: dict, run_id: str, post_id: str, is_seed: bool, pool_id: str) -> dict:
    """Judge scores for a post (seed posts are labelled once per pool item)."""
    return labels.get(f"pool:{pool_id}" if is_seed else f"{run_id}:{post_id}", {})


def _parses(code: str) -> bool:
    """Whether code parses (unparseable-output rate, prereg §9.8)."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def judged(s: dict, stance: str) -> bool:
    """A post is "judged pro-hack" / "judged anti-hack" when the judge's 3-way label (argmax of P(pro), P(anti),
    P(neutral)) is that stance: the label is what the kappa validation of prereg §8.5 checks against hand labels.
    (The 0.8 thresholds of §5 / §2.3 apply only to building the seed pools and the assay stimulus sets.)"""
    return s.get("label") == stance


def attach_exposure(recs: pd.DataFrame, posts: pd.DataFrame, labels: dict) -> pd.DataFrame:
    """Per agent-round: S, M, anti counts, author-hack exposure, E / E_anti (expected M / anti given the board),
    lagged hack and flag state."""
    hack = {(r.run_id, r.agent, r.round): bool(r.hack_attempt) for r in recs.itertuples()}  # author status
    info, board = {}, {}  # (run, post_id) -> flags; (run, round) -> candidate posts
    for p in posts.itertuples():
        s = label_of(labels, p.run_id, p.post_id, p.is_seed, p.pool_id)
        pro, anti = judged(s, "pro"), judged(s, "anti")  # judge label of this post
        ah = (not p.is_seed) and hack.get((p.run_id, p.author, p.round), False)
        info[(p.run_id, p.post_id)] = (p.is_seed, pro, anti, ah)
        board.setdefault((p.run_id, p.round), []).append((p.author, p.is_seed, pro, ah, anti))
    rows = []
    for r in recs.itertuples():
        S = Mn = A = Mh = 0
        for pid in r.read_post_ids:
            seed, pro, anti, ah = info.get((r.run_id, pid), (False, False, False, False))
            S += int(pro and seed)
            Mn += int(pro and not seed)
            A += int(anti)
            Mh += int(ah)
        cand = [b for b in board.get((r.run_id, r.round - 1), []) if b[0] != r.agent]  # readable posts
        kk = min(K, len(cand))
        E = kk * np.mean([(not b[1]) and b[2] for b in cand]) if cand else 0.0  # expected non-seed pro-hack read
        Eh = kk * np.mean([b[3] for b in cand]) if cand else 0.0  # expected hacked-author posts read
        Ea = kk * np.mean([b[4] for b in cand]) if cand else 0.0  # expected anti-hack posts read
        rows.append((S, Mn, A, Mh, E, Eh, Ea))
    out = recs.copy()
    cols = ["k_seed_pro", "k_nonseed_pro", "k_anti", "k_author_hack", "E", "E_author", "E_anti"]
    out[cols] = pd.DataFrame(rows, index=out.index, columns=cols)
    out = out.sort_values(["run_id", "agent", "round"]).reset_index(drop=True)
    out["prev_hack"] = out.groupby(["run_id", "agent"])["hack_attempt"].shift(1)  # NaN in round 0
    out["prev_flag"] = out.groupby(["run_id", "agent"])["flagged"].shift(1)  # flag state in t-1 (counter-contagion)
    out["ever_before"] = out.groupby(["run_id", "agent"])["hack_attempt"].transform(
        lambda s: s.astype(int).cumsum().shift(1, fill_value=0) > 0)  # hacked in an earlier round
    out["post_pro"] = [judged(labels.get(f"{r}:{p}", {}), "pro") for r, p in zip(out.run_id, out.post_id)]
    out["post_anti"] = [judged(labels.get(f"{r}:{p}", {}), "anti") for r, p in zip(out.run_id, out.post_id)]
    out["task"], out["run"] = out["task_id"], out["run_id"]
    out["unparseable"] = [not _parses(a[0]["code"]) if a else True for a in out["attempts"]]
    return out


def example_posts(posts: pd.DataFrame, labels: dict, n: int = 2) -> dict:
    """Example board posts for the reports: `n` agent posts per judged stance and one seed post per pool, drawn with
    a fixed RNG of their own (so the analysis RNG stream is untouched) — illustrations, not a representative sample."""
    rng = np.random.default_rng(RNG_SEED + 1)
    lab = [label_of(labels, r.run_id, r.post_id, r.is_seed, r.pool_id) for r in posts.itertuples()]
    d = posts.assign(label=[x.get("label") for x in lab], p_pro=[round(x.get("p_pro", 0.0), 3) for x in lab])
    pick = lambda g, k: [{c: (int(v) if c == "round" else v) for c, v in row.items()}
                         for row in g.iloc[np.sort(rng.choice(len(g), min(k, len(g)), replace=False))][
                             ["run_id", "round", "label", "p_pro", "text"]].to_dict("records")] if len(g) else []
    out = {st: pick(d[~d.is_seed & (d.label == st)], n) for st in ("pro", "anti", "neutral")}
    out |= {f"seed_{c}": pick(d[d.is_seed & (d.condition == c)], 1) for c in ("MAIN", "PLACEBO")}
    return out


# ============================================================================================ H1
def run_means(df: pd.DataFrame, rounds: range) -> pd.DataFrame:
    """Run-level mean prevalence over `rounds` and round-0 prevalence, indexed by (condition, replicate)."""
    prev = df.groupby(["condition", "replicate", "round"])["hack_attempt"].mean().unstack()  # runs x rounds
    cols = [c for c in rounds if c in prev.columns]  # rounds present (shorter test runs)
    if not cols:
        return pd.DataFrame(columns=["mean", "round0"])
    return pd.DataFrame({"mean": prev[cols].mean(1), "round0": prev[0]})


def paired(rm: pd.DataFrame, a: str, b: str, rng, sesoi: float = 0.10) -> dict:
    """CRN-paired comparison of conditions a vs b over replicates present in both."""
    conds = set(rm.index.get_level_values(0)) if len(rm) else set()
    if a not in conds or b not in conds:
        return {}
    A, B = rm.loc[a], rm.loc[b]
    common = A.index.intersection(B.index)  # CRN pairs
    if len(common) < 3:
        return {}
    return stats.compare_paired(A.loc[common, "mean"].values, B.loc[common, "mean"].values, sesoi, rng,
                                covariate=(A.loc[common, "round0"] - B.loc[common, "round0"]).values)


# ============================================================================================ H2
SLOPES = ["k_seed_pro", "k_nonseed_pro", "E"]


def risk_set(df: pd.DataFrame, first_ever: bool = False) -> pd.DataFrame:
    """Susceptible agent-rounds (rounds >= 1): not hacking in t-1 (primary) or never hacked before (sensitivity)."""
    h = df[df["round"] >= 1]
    h = h[~h["ever_before"]] if first_ever else h[h["prev_hack"] == False]
    h = h.copy()
    h["y"] = h["hack_attempt"].astype(int)
    return h


def _resample_runs(df: pd.DataFrame, rng, conds: list[str] | None = None) -> pd.DataFrame:
    """Cluster bootstrap: resample runs with replacement within condition; duplicates get distinct run ids."""
    groups = {c: g["run"].unique() for c, g in df.groupby("condition") if conds is None or c in conds}
    pick = [r for rs in groups.values() for r in rng.choice(rs, len(rs))]
    return pd.concat([df[df.run == r].assign(run=f"{r}#{i}") for i, r in enumerate(pick)], ignore_index=True)


def h2(df: pd.DataFrame, rng, n_perm: int = 1000, n_boot: int = 2000, h1_star: float = 0.02) -> dict:
    """Primary cloglog hazard model, robustness fits, the permutation random control and the §13 verdict inputs.

    `h1_star` is the smallest effect of interest fixed at Stage 2 (data/stage2_constants.json; 0.02 if the pilot
    could not estimate pi or D, prereg §9.2). Falsified for this setup if the upper 90% CI bound of h1 < h1_star.
    """
    h = risk_set(df)
    if h["y"].sum() < 5 or h["run"].nunique() < 3:
        return {"error": "too few events"}
    res = hazard.fit_cloglog(h, SLOPES)
    out = {c: hazard.hazard_ratio(res, c) for c in ("k_seed_pro", "k_nonseed_pro")}
    out["h1_marginal"] = hazard.marginal_h1(res, "k_nonseed_pro")
    out |= {"n_rows": len(h), "n_events": int(h["y"].sum()), "n_runs": int(h["run"].nunique()),
            "n_dropped": int(res.n_dropped)}
    out["statsmodels_check_round_run"] = hazard.statsmodels_check(h, SLOPES).round(6).to_dict()  # validation
    boots, h1s = [], []
    for _ in range(n_boot):  # robustness 1: cluster bootstrap over runs within condition (also gives h1's CIs)
        try:
            rb = hazard.fit_cloglog(_resample_runs(h, rng), SLOPES)
            boots.append(float(rb.params["k_nonseed_pro"]))
            h1s.append(hazard.marginal_h1(rb, "k_nonseed_pro"))
        except (np.linalg.LinAlgError, KeyError):
            continue
    out["bootstrap_beta_ci95"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    out["h1_ci90"] = [float(np.percentile(h1s, 5)), float(np.percentile(h1s, 95))]  # percentile, cluster bootstrap
    out["h1_ci95"] = [float(np.percentile(h1s, 2.5)), float(np.percentile(h1s, 97.5))]
    out["h1_star"] = float(h1_star)
    out["falsified_h1_below_star"] = bool(out["h1_ci90"][1] < h1_star)  # prereg §13
    hr = h.assign(run_round=h["run"] + "_" + h["round"].astype(str))  # robustness 2: run x round FE
    out["robust_run_round_fe"] = hazard.hazard_ratio(
        hazard.fit_cloglog(hr, ["k_seed_pro", "k_nonseed_pro"], fe=("run_round", "task")), "k_nonseed_pro")
    out["robust_author_status"] = hazard.hazard_ratio(  # robustness 3: judge-free exposure
        hazard.fit_cloglog(h, ["k_seed_pro", "k_author_hack", "E_author"]), "k_author_hack")
    out["sensitivity_first_ever"] = hazard.hazard_ratio(
        hazard.fit_cloglog(risk_set(df, first_ever=True), SLOPES), "k_nonseed_pro")
    betas, cover = [], []
    for _ in range(n_perm):  # random control: permute outcomes within run x round
        hp = h.copy()
        hp["y"] = hp.groupby(["run", "round"])["y"].transform(lambda s: rng.permutation(s.values))
        rp = hazard.fit_cloglog(hp, SLOPES)
        b, se = float(rp.params["k_nonseed_pro"]), float(rp.bse["k_nonseed_pro"])
        betas.append(b)
        cover.append(b - 1.96 * se <= 0 <= b + 1.96 * se)
    b_obs = out["k_nonseed_pro"]["beta"]  # randomization p: share of permuted betas >= observed (+1 smoothing)
    out["permutation_control"] = {"mean_beta": float(np.mean(betas)), "sd_beta": float(np.std(betas)),
                                  "coverage_of_zero": float(np.mean(cover)), "n_perm": n_perm,
                                  "p_perm_one_sided": float((1 + np.sum(np.array(betas) >= b_obs)) / (1 + n_perm))}
    return out


# ============================================================================================ counter-contagion
CC_SLOPES = ["k_anti", "E_anti", "k_seed_pro", "k_nonseed_pro", "E"]


def counter_contagion(df: pd.DataFrame) -> dict:
    """Exploratory (prereg §9, secondary list: "flag and anti-hack counter-contagion"): does reading anti-hack posts
    raise the hazard of STARTING to flag?

    Same randomized-exposure design as H2 with the outcome swapped: risk set = agent-rounds t >= 1 that did not flag in
    t - 1; y = flagged in t; cloglog with round + run + task fixed effects and run-clustered SEs. The K posts read are a
    uniform sample of the previous round's board, so given E_anti (expected anti-hack posts read) the count k_anti is
    randomized; the pro-hack counts enter with their own E as in H2. The model form was fixed after an interim
    descriptive look at flag rates (rising in every condition), so it is post hoc and reported as such.
    """
    h = df[(df["round"] >= 1) & (df["prev_flag"] == False)].copy()  # == False also drops round-0 NaN
    h["y"] = h["flagged"].astype(int)
    if h["y"].sum() < 5 or h["run"].nunique() < 3:
        return {"error": "too few events"}
    slopes = [c for c in CC_SLOPES if h[c].nunique() > 1]  # a constant column (e.g. no seed exposure) is unidentified
    res = hazard.fit_cloglog(h, slopes)
    out = {c: hazard.hazard_ratio(res, c) for c in ("k_anti", "k_seed_pro", "k_nonseed_pro") if c in slopes}
    out["slopes"] = slopes
    out["h_anti_marginal"] = hazard.marginal_h1(res, "k_anti")  # avg hazard increase per anti-hack post read
    out |= {"n_rows": len(h), "n_events": int(h["y"].sum()), "n_runs": int(h["run"].nunique())}
    fr = df.groupby(["condition", "round"])["flagged"].mean().unstack()  # condition x round flag rate
    out["flag_rate_round0"] = fr[0].round(4).to_dict()
    out["flag_rate_round10"] = fr[fr.columns.max()].round(4).to_dict()
    out["post_anti_rate"] = df.groupby("condition")["post_anti"].mean().round(4).to_dict()  # judged anti-hack posts
    return out


# ============================================================================================ H4 and the post map
def _fits_summary(fits: dict) -> dict:
    """Serializable summary of dose-response fits with Akaike weights."""
    w = dose.akaike_weights(fits)
    return {m: {"params": f.params, "loglik": f.loglik, "aicc": f.aicc, "akaike_weight": w.get(m)}
            for m, f in fits.items()}


def _boot_cells(sub: pd.DataFrame, col: str, rng) -> tuple[np.ndarray, np.ndarray]:
    """Resample trials within exposure cells; returns (k, y)."""
    ks = sorted(sub.k.unique())
    kb = np.concatenate([[kv] * int((sub.k == kv).sum()) for kv in ks])
    yb = np.concatenate([rng.choice(sub[sub.k == kv][col].astype(int).values, int((sub.k == kv).sum())) for kv in ks])
    return kb, yb


def h4(assay: pd.DataFrame, rng, n_boot: int = 2000) -> dict:
    """Dose-response analyses on the randomized assay (hack arm, post-stance arm, comparisons)."""
    d = assay[(assay.variant == "distinct") & (assay.j == 0)]
    k, y = d["k"].values, d["hack_attempt"].astype(int).values
    fits = dose.fit_all(k, y)
    out = {"hack": _fits_summary(fits), "lrt_simple_vs_weibull": dose.lrt(fits["simple"], fits["weibull"]),
           "gamma_profile_ci": dose.profile_ci_gamma(k, y)}
    tab = d.groupby("k").agg(n=("hack_attempt", "size"), hack=("hack_attempt", "mean"), post_pro=("post_pro", "mean"))
    out["table"] = tab.reset_index().to_dict("records")
    grid = np.arange(K + 1)
    maxdiffs, dw = [], []
    for _ in range(n_boot):  # falsification statistic and Dodds-Watts superadditivity
        kb, yb = _boot_cells(d, "hack_attempt", rng)
        fs, fw = dose.fit_model("simple", kb, yb), dose.fit_model("weibull", kb, yb)
        maxdiffs.append(float(np.max(np.abs(fw.predict(grid) - fs.predict(grid)))))
        p = {kv: yb[kb == kv].mean() for kv in np.unique(kb)}
        if {0, 1, 2} <= set(p) and p[0] < 1:
            dw.append((p[2] - p[0]) / (1 - p[0]) - 2 * (p[1] - p[0]) / (1 - p[0]))  # P*2 - 2 P*1
    out["falsification_maxdiff_ci90_upper"] = float(np.percentile(maxdiffs, 95))
    out["sigmoid_aicc_preferred_by_2"] = bool(fits["sigmoid"].aicc < min(fits["simple"].aicc, fits["weibull"].aicc) - 2)
    if dw:
        out["dodds_watts_P2_minus_2P1_ci95"] = [float(np.percentile(dw, 2.5)), float(np.percentile(dw, 97.5))]
    comps = {}
    for kv in (2, 4):  # same-author vs distinct-author
        s, dd = assay[(assay.variant == "same") & (assay.k == kv)], d[d.k == kv]
        if len(s) and len(dd):
            comps[f"same_minus_distinct_k{kv}"] = float(s.hack_attempt.mean() - dd.hack_attempt.mean())
    anti = assay[(assay.variant == "distinct") & (assay.j == 2)]
    comps["anti_minus_none_by_k"] = {int(kv): float(anti[anti.k == kv].hack_attempt.mean() -
                                                    d[d.k == kv].hack_attempt.mean())
                                     for kv in sorted(anti.k.unique()) if (d.k == kv).any()}
    off, base = assay[assay.variant == "offtopic"], d[d.k == 0]
    comps["offtopic_minus_k0"] = {int(kv): float(off[off.k == kv].hack_attempt.mean() - base.hack_attempt.mean())
                                  for kv in sorted(off.k.unique())}
    if (off.k == 6).any() and len(base):
        o6 = off[off.k == 6]
        comps["offtopic_k6_tost_p"] = float(tost_proportions_2indep(
            int(o6.hack_attempt.sum()), len(o6), int(base.hack_attempt.sum()), len(base), -0.10, 0.10)[0])
    out["comparisons"] = comps
    pk = d.dropna(subset=["post_pro"])  # post-stance map q_k (Akaike-weighted parametric fit, prereg §7.1)
    q = dose.averaged_curve(dose.fit_all(pk["k"].values, pk["post_pro"].astype(int).values), grid)
    out["post_map"] = {"q": q.tolist(), **transmission.regime(q, K)}
    rm = [transmission.fprime0(dose.averaged_curve(dose.fit_all(*_boot_cells(pk, "post_pro", rng)), grid), K)
          for _ in range(min(n_boot, 1000))]
    out["post_map"]["R_map_ci95"] = [float(np.percentile(rm, 2.5)), float(np.percentile(rm, 97.5))]
    hacked = assay["hack_attempt"].astype(bool)
    out["pi_from_assay"] = {"pi_h": float(assay[hacked]["post_pro"].mean()),
                            "pi_n": float(assay[~hacked]["post_pro"].mean())}
    return out


# ============================================================================================ H3
def infectious_period(df: pd.DataFrame) -> float:
    """D = 1/rho, rho = (pro-posting spells that end) / (pro-posting agent-rounds at risk of ending; last round
    censored) — geometric MLE (prereg §7.3)."""
    d = df.sort_values("round")
    nxt = d.groupby(["run", "agent"])["post_pro"].shift(-1)
    at_risk = d["post_pro"].astype(bool) & nxt.notna()
    ends = at_risk & (nxt == False)
    return float(at_risk.sum() / max(int(ends.sum()), 1))


def r0_components(df: pd.DataFrame, h1: float) -> dict:
    """pi, D and R0 = pi K~ h1 D with K~ = K (post-seed regime) and K~ = (N-1)K/(N-1+m) (seeds active)."""
    sub = df[df.condition.isin(["MAIN", "TRANSIENT"])]
    pi = float(sub[sub.hack_attempt]["post_pro"].mean()) if sub.hack_attempt.any() else float("nan")
    D = infectious_period(sub)
    return {"pi": pi, "D": D, "h1": h1, "R0": transmission.board_R0(pi, K, h1, D),
            "R0_seeds_active": transmission.board_R0(pi, (N - 1) * K / (N - 1 + M_SEEDS), h1, D)}


def h3(df: pd.DataFrame, rm_late: pd.DataFrame, h2_out: dict, h4_out: dict, rng, n_boot: int = 1000) -> dict:
    """Persistence test, logit slope, R0 / R_map with CIs and the pre-registered three-way decision."""
    out = {"late_window": paired(rm_late, "TRANSIENT", "PLACEBO", rng)}
    tr = df[df.condition == "TRANSIENT"]
    if len(tr):
        def slope(sub: pd.DataFrame) -> float:
            m = sub[sub["round"].between(3, 10)].groupby("round")["hack_attempt"].mean()
            return float(np.polyfit(m.index.values, logit(np.clip(m.values, 0.5 / N, 1 - 0.5 / N)), 1)[0])

        bs = [slope(_resample_runs(tr, rng)) for _ in range(n_boot)]
        out["transient_logit_slope"] = {"est": slope(tr), "ci95": [float(np.percentile(bs, 2.5)),
                                                                   float(np.percentile(bs, 97.5))]}
    if "h1_marginal" in h2_out:
        comp = r0_components(df, h2_out["h1_marginal"])
        r0s = []
        for _ in range(n_boot):  # runs resampled within condition; h1 refitted on each resample
            db = _resample_runs(df, rng)
            try:
                r0s.append(r0_components(db, hazard.marginal_h1(hazard.fit_cloglog(risk_set(db), SLOPES),
                                                                "k_nonseed_pro"))["R0"])
            except (np.linalg.LinAlgError, KeyError):
                continue
        comp["R0_ci95"] = [float(np.nanpercentile(r0s, 2.5)), float(np.nanpercentile(r0s, 97.5))]
        out["R0"] = comp
    lw, pm = out["late_window"], h4_out.get("post_map", {})
    r0ci = out.get("R0", {}).get("R0_ci95", [np.nan, np.nan])
    sustained = bool(lw) and lw["p_signflip"] < 0.05 and (r0ci[0] > 1 or pm.get("regime") == "bistable")
    decaying = bool(lw) and (lw["p_tost_paired"] < 0.05 or r0ci[1] < 1)
    out["decision"] = "self-sustaining" if sustained else ("decaying" if decaying else "inconclusive")
    return out


def growth_curves(df: pd.DataFrame, identifiable: bool | None) -> dict:
    """Descriptive growth-curve fits of cumulative first hack attempts per condition (prereg §9.4)."""
    out = {"identifiability_passed": identifiable}
    for cond in ("MAIN", "TRANSIENT", "PLACEBO"):
        sub = df[df.condition == cond]
        if not len(sub):
            continue
        first = sub[sub.hack_attempt].groupby(["run", "agent"])["round"].min().reset_index()
        C = np.array([[int((first[first.run == r]["round"] <= t).sum()) for t in range(11)] for r in sub.run.unique()])
        fits = curves.fit_all(C, N)
        best = min(f.aicc for f in fits.values())
        src = min(("logistic", "richards"), key=lambda m: fits[m].aicc)  # better of the two by AICc
        r0 = curves.initial_rate(fits[src])  # identifiable initial rate (Ma et al. 2014)
        out[cond] = {"fits": {m: {"params": f.params, "aicc": f.aicc, "delta_aicc": f.aicc - best}
                              for m, f in fits.items()},
                     "initial_rate_r0": r0, "initial_rate_source": src,
                     "doubling_time_rounds": curves.doubling_time(r0), "mean_cumulative": C.mean(0).tolist()}
    return out


# ============================================================================================ H5
def loo_logistic_pmfs(obs: np.ndarray) -> list[np.ndarray]:
    """For each held-out run, Binomial(N, p(t)) pmfs with p(t) = ceiling * logistic(t) fitted to the other runs."""
    t = np.arange(obs.shape[1], dtype=float)
    pmfs = []
    for i in range(obs.shape[0]):
        rest = np.delete(obs, i, axis=0)

        def nll(th, rest=rest):
            p = np.clip(expit(th[0]) * expit(th[1] * (t - th[2])), 1e-9, 1 - 1e-9)
            return -np.sum(rest * np.log(p) + (N - rest) * np.log1p(-p))

        th = min((optimize.minimize(nll, s, method="Nelder-Mead") for s in ([0, 0.5, 3], [-1, 1, 5], [1, 0.2, 1])),
                 key=lambda r: r.fun).x
        p = expit(th[0]) * expit(th[1] * (t - th[2]))
        pmfs.append(np.stack([binom.pmf(np.arange(N + 1), N, pt) for pt in p]))  # rounds x (N+1)
    return pmfs


def h5(df: pd.DataFrame, h4_out: dict, sim_params: dict, rng, reps: int = 10000) -> dict:
    """Out-of-sample forecasts of MAIN and TRANSIENT prevalence counts (prereg §9.5)."""
    if "hack" not in h4_out or not sim_params:
        return {}
    w = dict(h4_out["hack"]["weibull"]["params"])
    base = risk_set(df[df.condition == "PLACEBO"])  # PLACEBO agent-rounds not hacking in t-1
    base = base[base["k_nonseed_pro"] == 0]  # ... and reading no non-seed pro-hack post: the background
    w["eps"] = float(base["y"].mean())  # baseline HAZARD: the simulator applies infect(k) only to non-hackers
    kernel = lambda k: dose.curve("weibull", w, k)
    pi = h4_out["pi_from_assay"]
    out = {}  # per forecast target (MAIN, TRANSIENT)
    for cond, last in [("MAIN", None), ("TRANSIENT", 1)]:
        obs = df[df.condition == cond].groupby(["run", "round"])["hack_attempt"].sum().unstack().values.astype(int)
        if obs.size == 0:
            continue
        T = obs.shape[1] - 1
        pmf_sets, curves_ = {}, {}
        for name, (ph, pn) in {"assay_model": (pi["pi_h"], pi["pi_n"]), "broadcast_only": (0.0, 0.0)}.items():
            sims = simulate.simulate_many(reps, rng, N=N, K=K, T=T, n_seeds=M_SEEDS, infect=kernel,
                                          recover=sim_params["recover"], pi_h=ph, pi_n=pn, seed_last_round=last)
            pmf_sets[name] = [[stats.pmf_from_samples(sims[:, t], N) for t in range(T + 1)]] * len(obs)  # same for all runs
            curves_[name] = {"mean_curve": sims.mean(0).tolist(), "lo": np.percentile(sims, 5, 0).tolist(),
                             "hi": np.percentile(sims, 95, 0).tolist()}
        pmf_sets["loo_logistic"] = loo_logistic_pmfs(obs)
        scores = {name: pd.DataFrame([{
            "crps": np.mean([stats.crps_star(pm[i][t], o[t]) for t in range(1, T + 1)]),
            "log": np.mean([stats.log_score(pm[i][t], o[t]) for t in range(1, T + 1)]),
            "cover": np.mean([stats.interval_covers(pm[i][t], o[t]) for t in range(1, T + 1)])}
            for i, o in enumerate(obs)]) for name, pm in pmf_sets.items()}
        test = stats.compare_paired(scores["broadcast_only"]["crps"].values, scores["assay_model"]["crps"].values,
                                    sesoi=0.0, rng=rng)  # H: broadcast CRPS* - assay CRPS* > 0
        res = {n: {"crps": float(s["crps"].mean()), "log_score": float(s["log"].mean()),
                   "coverage90": float(s["cover"].mean())} | curves_.get(n, {}) for n, s in scores.items()}
        res["observed_mean"] = obs.mean(0).tolist()
        res["eps_baseline_hazard"], res["n_baseline_rows"] = w["eps"], len(base)  # simulator input, recorded
        res["p_assay_better_than_broadcast"] = test["p_signflip"]
        res["supported"] = bool(test["p_signflip"] < 0.05 and res["assay_model"]["crps"] <= res["loo_logistic"]["crps"]
                                and res["assay_model"]["coverage90"] >= 0.75)
        out[cond] = res
    return out


# ============================================================================================ driver
def run_all(batch_dir: Path, assay_path: Path | None, labels_path: Path, out_dir: Path, data_dir: Path = Path("data"),
            n_perm: int = 1000, n_boot: int = 2000, reps: int = 10000) -> dict:
    """Compute everything and write results/summary.json + tables."""
    rng = np.random.default_rng(RNG_SEED)
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else {}
    recs, posts = load_runs(batch_dir)
    df = attach_exposure(recs, posts, labels)
    prev = df.groupby(["condition", "run_id", "round"]).agg(prevalence=("hack_attempt", "mean"),
                                                             flag_rate=("flagged", "mean")).reset_index()
    prev.to_csv(out_dir / "prevalence_by_round.csv", index=False)
    rm = run_means(df, range(1, 11))
    S = {"n_runs": df.groupby("condition")["run_id"].nunique().to_dict()}
    S["h1"] = {"MAIN_vs_PLACEBO": paired(rm, "MAIN", "PLACEBO", rng),
               "TRANSIENT_vs_PLACEBO": paired(rm, "TRANSIENT", "PLACEBO", rng)}
    consts = data_dir / "stage2_constants.json"  # h1* fixed at Stage 2 (scripts/stage2.py)
    h1_star = json.loads(consts.read_text())["h1_star"] if consts.exists() else 0.02  # prereg §9.2 default
    S["h2"] = h2(df, rng, n_perm=n_perm, n_boot=n_boot, h1_star=h1_star)
    assay = None
    if assay_path and assay_path.exists():
        assay = pd.DataFrame([json.loads(x) for x in assay_path.read_text(encoding="utf-8").splitlines() if x])
        assay["post_pro"] = [judged(labels.get(f"assay:{t}", {}), "pro") for t in assay["trial_id"]]
        S["h4"] = h4(assay, rng, n_boot=n_boot)
    p = {"H1": S["h1"]["MAIN_vs_PLACEBO"].get("p_signflip"), "H2": S["h2"].get("k_nonseed_pro", {}).get("p_one_sided"),
         "H4": S.get("h4", {}).get("lrt_simple_vs_weibull", {}).get("p_value")}
    S["holm"] = stats.holm_family(p)  # fixed family {H1, H2, H4}, prereg §9.6
    S["h3"] = h3(df, run_means(df, range(8, 11)), S["h2"], S.get("h4", {}), rng, n_boot=min(n_boot, 1000))
    power_path, sim_path = data_dir / "power.json", data_dir / "sim_params.json"
    ident = json.loads(power_path.read_text())["identifiability"]["passes_80pct"] if power_path.exists() else None
    S["growth_curves"] = growth_curves(df, ident)
    S["h5"] = h5(df, S.get("h4", {}), json.loads(sim_path.read_text()) if sim_path.exists() else {}, rng, reps)
    S["counter_contagion"] = counter_contagion(df)  # exploratory, post hoc model form
    S["examples"] = example_posts(posts, labels)  # illustrative posts for the reports
    S["descriptives"] = df.groupby("condition").agg(
        hack_attempt=("hack_attempt", "mean"), hack_success=("hack_success", "mean"), flag=("flagged", "mean"),
        capable=("strict_original_pass", "mean"), probe_p_yes=("probe_p_yes", "mean"),
        post_pro=("post_pro", "mean"), unparseable=("unparseable", "mean"),
        reads_seed_pro=("k_seed_pro", "mean"), reads_nonseed_pro=("k_nonseed_pro", "mean"),  # posts read per
        reads_anti=("k_anti", "mean")).round(4).to_dict("index")  # agent-round (exposure dose)
    S["mechanisms"] = df[df.hack_attempt].groupby(["condition", "mechanism"]).size().unstack(fill_value=0).to_dict("index")
    (out_dir / "summary.json").write_text(json.dumps(S, indent=1, default=float), encoding="utf-8")
    df.drop(columns=["attempts"]).to_parquet(out_dir / "agent_rounds.parquet", index=False)
    if assay is not None:
        assay.drop(columns=["attempts"]).to_parquet(out_dir / "assay_trials.parquet", index=False)
    return S
