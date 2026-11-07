"""Pre-registered analysis: reads results files only and regenerates every table/number in results/ (one command).

Local context — maps each hypothesis to its estimator (reports/preregistration.md):
- H1 contagion: run-level mean non-seed hack-attempt prevalence over rounds 1..T, MAIN vs PLACEBO
  (`epi.stats.compare_runs`: permutation + Welch + bootstrap CI + TOST).
- H2 secondary transmission: cloglog hazard on randomized counts of pro-hack posts read, seed vs non-seed authors,
  round fixed effects, run-clustered SEs (`epi.hazard`); plus the within-round label-permutation random control.
- H4 dose-response shape: simple vs Weibull (LRT on gamma=1) vs sigmoid vs saturated on the assay (`epi.dose`).
- Holm correction over the confirmatory family {H1, H2, H4}.
- H3 / H5 (exploratory): TRANSIENT trajectory, f'(0) and R0 (`epi.transmission`), growth-curve AICc table
  (`epi.curves`), and out-of-sample prediction of MAIN/TRANSIENT curves by the assay-calibrated simulator scored with
  CRPS / log score against a broadcast-only baseline (`epi.simulate`, `epi.stats`).
Global context: `scripts/analyze.py` calls `run_all`; `figures.py` and `site.py` read the JSON/CSV written here.
"""

from __future__ import annotations  # forward references

import json  # IO
from pathlib import Path  # paths

import numpy as np  # numerics
import pandas as pd  # tables

from .epi import curves, dose, hazard, simulate, stats, transmission  # statistics

RNG_SEED = 20261107  # analysis RNG seed (bootstrap / permutation / simulation)


# ----------------------------------------------------------------------------------------------- loading
def load_runs(batch_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Concatenate rounds.jsonl (agent-rounds) and board.jsonl (posts) of every completed run in `batch_dir`."""
    recs, posts = [], []  # accumulators
    for d in sorted(p for p in batch_dir.iterdir() if (p / "state.json").exists()):
        if not json.loads((d / "state.json").read_text(encoding="utf-8")).get("done"):
            continue  # only completed runs enter the analysis
        cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))  # run config
        recs += [json.loads(x) for x in (d / "rounds.jsonl").read_text(encoding="utf-8").splitlines() if x]
        posts += [json.loads(x) | {"run_id": d.name, "condition": cfg["condition"]}
                  for x in (d / "board.jsonl").read_text(encoding="utf-8").splitlines() if x]
    return pd.DataFrame(recs), pd.DataFrame(posts)


def post_key(run_id: str, post_id: str, is_seed: bool, pool_id: str) -> str:
    """Key into the judge-label table: seed posts are labeled once per pool item, agent posts per run."""
    return f"pool:{pool_id}" if is_seed else f"{run_id}:{post_id}"


def attach_exposure(recs: pd.DataFrame, posts: pd.DataFrame, labels: dict[str, dict], thr: float = 0.5) -> pd.DataFrame:
    """Add k_seed_pro / k_nonseed_pro / k_anti (counts of judged posts read) and previous-round state per agent."""
    lab = {}  # (run_id, post_id) -> label scores
    for p in posts.itertuples():
        lab[(p.run_id, p.post_id)] = labels.get(post_key(p.run_id, p.post_id, p.is_seed, p.pool_id), {})
    rows = []
    for r in recs.itertuples():
        ks = kn = ka = 0  # exposure counters
        for pid, seed in zip(r.read_post_ids, r.read_is_seed):
            s = lab.get((r.run_id, pid), {})  # judge scores of the read post
            pro = s.get("p_pro", 0.0) >= thr  # pro-hack label (P(A) >= 0.5)
            ks += int(pro and seed)
            kn += int(pro and not seed)
            ka += int(s.get("p_anti", 0.0) >= thr)
        rows.append((ks, kn, ka))
    out = recs.copy()
    out[["k_seed_pro", "k_nonseed_pro", "k_anti"]] = np.array(rows, int) if rows else np.zeros((0, 3), int)
    out = out.sort_values(["run_id", "agent", "round"])  # previous-round state per agent
    out["prev_hack"] = out.groupby(["run_id", "agent"])["hack_attempt"].shift(1)  # NaN in round 0
    out["post_pro"] = [labels.get(f"{r}:{p}", {}).get("p_pro", np.nan) >= thr
                       for r, p in zip(out.run_id, out.post_id)]  # own post judged pro-hack
    return out


# ----------------------------------------------------------------------------------------------- H1
def prevalence_table(df: pd.DataFrame) -> pd.DataFrame:
    """Non-seed hack-attempt prevalence per run and round."""
    return df.groupby(["condition", "run_id", "round"])["hack_attempt"].mean().rename("prevalence").reset_index()


def h1(prev: pd.DataFrame, rng: np.random.Generator) -> dict:
    """Run-level mean prevalence over rounds >= 1; MAIN vs PLACEBO (confirmatory) and TRANSIENT vs PLACEBO."""
    run_means = prev[prev["round"] >= 1].groupby(["condition", "run_id"])["prevalence"].mean()  # one value per run
    get = lambda c: run_means.loc[c].values if c in run_means.index.get_level_values(0) else np.array([])
    out = {}
    for a, b in [("MAIN", "PLACEBO"), ("TRANSIENT", "PLACEBO"), ("MAIN", "TRANSIENT")]:
        if len(get(a)) >= 2 and len(get(b)) >= 2:
            out[f"{a}_vs_{b}"] = stats.compare_runs(get(a), get(b), sesoi=0.10, rng=rng)
    return out


# ----------------------------------------------------------------------------------------------- H2
def hazard_table(df: pd.DataFrame) -> pd.DataFrame:
    """Susceptible agent-rounds (not hacking in the previous round), rounds >= 1, outcome y = hack attempt now."""
    h = df[(df["round"] >= 1) & (df["prev_hack"] == False)].copy()
    h["y"] = h["hack_attempt"].astype(int)
    h["run"] = h["run_id"]
    return h


def h2(df: pd.DataFrame, rng: np.random.Generator) -> dict:
    """Cloglog hazard fit on MAIN + TRANSIENT susceptible agent-rounds, plus the label-permutation random control."""
    h = hazard_table(df[df["condition"].isin(["MAIN", "TRANSIENT"])])
    if h["y"].sum() < 5 or h["run"].nunique() < 3:
        return {"error": "too few events"}
    res = hazard.fit_cloglog(h, ["k_seed_pro", "k_nonseed_pro"])
    out = {c: hazard.hazard_ratio(res, c) for c in ("k_seed_pro", "k_nonseed_pro")}
    perm = h.copy()  # random control: shuffle outcomes within round (breaks exposure-outcome link only)
    perm["y"] = perm.groupby("round")["y"].transform(lambda s: rng.permutation(s.values))
    res0 = hazard.fit_cloglog(perm, ["k_seed_pro", "k_nonseed_pro"])
    out["permutation_control"] = {c: hazard.hazard_ratio(res0, c) for c in ("k_seed_pro", "k_nonseed_pro")}
    out["n_rows"], out["n_events"], out["n_runs"] = len(h), int(h["y"].sum()), int(h["run"].nunique())
    return out


# ----------------------------------------------------------------------------------------------- H4 + map
def assay_analysis(assay: pd.DataFrame, labels: dict[str, dict], rng: np.random.Generator, B: int = 2000) -> dict:
    """Dose-response fits (hack and own-post-pro arms), anti-post effect, same-vs-distinct, off-topic control."""
    a = assay.copy()
    a["post_pro"] = [labels.get(f"assay:{t}", {}).get("p_pro", np.nan) >= 0.5 for t in a["trial_id"]]
    d = a[(a["variant"] == "distinct") & (a["j"] == 0)]  # main dose-response cells
    fits = dose.fit_all(d["k"].values, d["hack_attempt"].astype(int).values)
    out = {"hack": {m: {"params": f.params, "loglik": f.loglik, "aicc": f.aicc} for m, f in fits.items()},
           "lrt_simple_vs_weibull": dose.lrt(fits["simple"], fits["weibull"])}
    tab = d.groupby("k").agg(n=("hack_attempt", "size"), hack=("hack_attempt", "mean"), post_pro=("post_pro", "mean"))
    out["table"] = tab.reset_index().to_dict("records")
    K = 6
    P_post = np.array([tab["post_pro"].get(k, np.nan) for k in range(K + 1)])  # saturated P(post pro | k)
    if not np.isnan(P_post[[0, 1]]).any():  # f'(0) needs k=0 and k=1 cells
        boot = []
        for _ in range(B):  # bootstrap trials within cells
            p0 = rng.choice(d[d.k == 0]["post_pro"].values, (d.k == 0).sum()).mean()
            p1 = rng.choice(d[d.k == 1]["post_pro"].values, (d.k == 1).sum()).mean()
            boot.append(K * (p1 - p0))
        out["fprime0"] = {"est": transmission.fprime0(P_post, K), "ci": list(np.percentile(boot, [2.5, 97.5]))}
    for name, sub in [("anti_j2", a[(a.variant == "distinct") & (a.j == 2)]), ("same", a[a.variant == "same"]),
                      ("offtopic", a[a.variant == "offtopic"])]:
        out[name] = sub.groupby("k")["hack_attempt"].agg(["size", "mean"]).reset_index().to_dict("records")
    return out


# ----------------------------------------------------------------------------------------------- H3 / H5
def cumulative_matrix(df: pd.DataFrame, condition: str, N: int) -> np.ndarray:
    """runs x rounds matrix of cumulative non-seed agents that have ever attempted a hack."""
    sub = df[df.condition == condition].sort_values("round")
    mats = []
    for _, g in sub.groupby("run_id"):
        first = g[g.hack_attempt].groupby("agent")["round"].min()  # first hack round per agent
        T = int(g["round"].max())
        mats.append([int((first <= t).sum()) for t in range(T + 1)])
    return np.array(mats)


def curve_table(df: pd.DataFrame, N: int) -> dict:
    """Pooled growth-curve fits (descriptive) per condition."""
    out = {}
    for cond in df.condition.unique():
        C = cumulative_matrix(df, cond, N)
        if C.size:
            fits = curves.fit_all(C, N)
            best = min(fits.values(), key=lambda f: f.aicc).aicc
            out[cond] = {m: {"params": f.params, "aicc": f.aicc, "delta_aicc": f.aicc - best} for m, f in fits.items()}
    return out


def epi_parameters(df: pd.DataFrame, assay_out: dict) -> dict:
    """gamma (recovery), pi (P(post pro | hacking)), h1 and R0 = pi K h1 / gamma for MAIN."""
    m = df[df.condition == "MAIN"]
    inf_prev = m[m.prev_hack == True]
    gamma = float(1 - inf_prev["hack_attempt"].mean()) if len(inf_prev) else float("nan")  # P(stop hacking)
    pi = float(m[m.hack_attempt]["post_pro"].mean()) if m.hack_attempt.any() else float("nan")
    tab = {r["k"]: r for r in assay_out.get("table", [])}
    h1v = (tab[1]["hack"] - tab[0]["hack"]) if 0 in tab and 1 in tab else float("nan")
    return {"gamma": gamma, "pi": pi, "h1": h1v, "R0": transmission.board_R0(pi, 6, h1v, gamma)}


def h5(df: pd.DataFrame, assay_out: dict, par: dict, N: int, rng: np.random.Generator, reps: int = 500) -> dict:
    """Simulate MAIN/TRANSIENT with the assay kernel; score observed run curves (CRPS, log score) vs broadcast-only."""
    if "hack" not in assay_out:
        return {}
    w = dict(assay_out["hack"]["weibull"]["params"])  # assay-fitted Weibull kernel (nests the simple model)
    w["eps"] = float(df[(df.condition == "PLACEBO") & (df["round"] >= 1)]["hack_attempt"].mean())  # background
    kernel = lambda k: dose.curve("weibull", w, k)
    out = {}
    for cond, last in [("MAIN", None), ("TRANSIENT", 1)]:
        obs = df[df.condition == cond].groupby(["run_id", "round"])["hack_attempt"].sum().unstack().values
        if obs.size == 0:
            continue
        T = obs.shape[1] - 1
        sims = {name: simulate.simulate_many(reps, rng, N=N, K=6, T=T, n_seeds=2, infect=kernel,
                                             recover=par["gamma"], pi=pi_, seed_last_round=last)
                for name, pi_ in [("assay_model", par["pi"]), ("broadcast_only", 0.0)]}
        out[cond] = {name: {"crps": float(np.mean([stats.crps_ensemble(s[:, t], o[t]) for o in obs
                                                    for t in range(1, T + 1)])),
                            "log_score": float(np.mean([stats.log_score_counts(s[:, t], int(o[t]), N) for o in obs
                                                        for t in range(1, T + 1)])),
                            "mean_curve": s.mean(0).tolist(), "lo": np.percentile(s, 2.5, 0).tolist(),
                            "hi": np.percentile(s, 97.5, 0).tolist()}
                     for name, s in sims.items()}
        out[cond]["observed_mean"] = obs.mean(0).tolist()
    return out


# ----------------------------------------------------------------------------------------------- driver
def run_all(batch_dir: Path, assay_path: Path | None, labels_path: Path, out_dir: Path, N: int = 32) -> dict:
    """Compute everything and write results/summary.json + CSV tables."""
    rng = np.random.default_rng(RNG_SEED)  # one stream for all resampling (reproducible)
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else {}
    recs, posts = load_runs(batch_dir)
    df = attach_exposure(recs, posts, labels)
    prev = prevalence_table(df)
    prev.to_csv(out_dir / "prevalence_by_round.csv", index=False)
    summary = {"n_runs": df.groupby("condition")["run_id"].nunique().to_dict(), "h1": h1(prev, rng), "h2": h2(df, rng)}
    if assay_path and assay_path.exists():
        assay = pd.DataFrame([json.loads(x) for x in assay_path.read_text(encoding="utf-8").splitlines() if x])
        summary["assay"] = assay_analysis(assay, labels, rng)
    p = {"H1": summary["h1"].get("MAIN_vs_PLACEBO", {}).get("p_perm"),
         "H2": summary["h2"].get("k_nonseed_pro", {}).get("p_one_sided"),
         "H4": summary.get("assay", {}).get("lrt_simple_vs_weibull", {}).get("p_value")}
    avail = {k: v for k, v in p.items() if v is not None}
    summary["holm"] = dict(zip(avail, map(float, stats.holm(list(avail.values()))))) if avail else {}
    summary["curves"] = curve_table(df, N)
    summary["epi_parameters"] = epi_parameters(df, summary.get("assay", {}))
    summary["h5"] = h5(df, summary.get("assay", {}), summary["epi_parameters"], N, rng)
    summary["descriptives"] = (df.groupby("condition").agg(
        hack_attempt=("hack_attempt", "mean"), hack_success=("hack_success", "mean"), flag=("flagged", "mean"),
        capable=("strict_original_pass", "mean"), probe_p_yes=("probe_p_yes", "mean")).round(4).to_dict("index"))
    summary["mechanisms"] = df[df.hack_attempt].groupby(["condition", "mechanism"]).size().unstack(fill_value=0) \
        .to_dict("index")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    df.drop(columns=["attempts"]).to_parquet(out_dir / "agent_rounds.parquet", index=False)  # analysis table
    return summary
