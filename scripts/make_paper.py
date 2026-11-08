"""Build the paper: gather every number into paper/data.json, then compile paper/paper.typ to paper/paper.pdf.

Usage:  uv run python scripts/make_paper.py [--results results] [--data data] [--no-compile]

Local context: the paper contains no hand-typed result numbers. This script is the only bridge between the results
files and the paper: it copies `results/summary.json` (written by `swarm_epi.analysis.run_all`) verbatim, adds the
frozen pilot files in `data/` that exist (sampling, capability, pools, calibration, audit, power, simulator
parameters), a few descriptive values derived from results files (per-condition prevalence with cluster-bootstrap
CIs, pool manipulation check, H5 predicted prevalence), the preregistered verdict rules (prereg §13), the design
constants read from the code (`SwarmConfig`, `conditions.batch1`), and the list of rendered figures. A missing input
gives an absent key or null, which `paper.typ` renders as "pending". Typst reads the file with its `json()` function
(https://typst.app/docs/reference/data-loading/json/).
Global context: run after `scripts/analyze.py` (results) and before publishing; one command regenerates the paper.
The PDF is compiled with typst-py (https://github.com/messense/typst-py, README "Usage": `typst.compile(input,
output=..., root=...)`; `compile_with_warnings` returns `(result, warnings)`, as declared in typst/__init__.pyi of
typst 0.15.2).
"""

from __future__ import annotations  # forward references in type hints

import argparse  # command-line options
import json  # read results / write paper/data.json
import math  # finiteness checks when sanitizing JSON
import shutil  # copy figures into paper/figures
from collections import Counter  # replicate counts per condition
from pathlib import Path  # filesystem paths
from types import SimpleNamespace  # light task stand-ins for the capability rule

import numpy as np  # bootstrap resampling
import pandas as pd  # per-round prevalence table
import typst  # typst-py: Python binding of the Typst compiler (Apache-2.0)

from swarm_epi import prompts as P  # prompt texts shown in the appendix (single source of truth)
from swarm_epi.analysis import RNG_SEED  # same analysis RNG seed as the preregistered analysis
from swarm_epi.conditions import batch1  # preregistered batch-1 condition list (replicate counts)
from swarm_epi.config import LLMConfig, RuntimeConfig, SwarmConfig  # design constants live in the code
from swarm_epi.tasks import apply_capability_filter  # preregistered capability threshold rule (§8.1)

ROOT = Path(__file__).resolve().parents[1]  # repository root (Typst project root, so paths cannot escape it)
PAPER = ROOT / "paper"  # paper sources and outputs
FIG_NAMES = ("fig_prevalence.png", "fig_dose_response.png", "fig_hazard.png", "fig_h5_prediction.png",
             "fig_mechanisms.png", "fig_flag_rate.png")  # written by swarm_epi.figures.make_all, used by paper.typ
EXPLORE_FIGS = ("fig_prevalence.png", "fig_hazard.png", "fig_flag_rate.png")  # exploratory batch (results/explore),
# copied as explore_<name> (deviation #13)
ALPHA = 0.05  # family-wise / per-test level of the preregistered decision rules (§9.6, §13)


def clean(obj):
    """Recursively make `obj` strict-JSON safe: NaN/inf -> None, numpy scalars -> Python scalars.

    Local: results/summary.json is written with Python's json module, which emits the non-standard tokens NaN and
    Infinity (https://docs.python.org/3/library/json.html#infinite-and-nan-number-values); Typst's JSON parser rejects
    them. Global: None renders as "pending"/"n/a" in the paper instead of a misleading number.
    """
    if isinstance(obj, dict):  # recurse into mappings, keeping keys as strings (JSON object keys)
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):  # recurse into sequences
        return [clean(v) for v in obj]
    if isinstance(obj, np.generic):  # numpy scalar -> native Python scalar
        obj = obj.item()
    if isinstance(obj, float) and not math.isfinite(obj):  # NaN / inf are not valid JSON numbers
        return None
    return obj  # str, int, bool, finite float, None pass through unchanged


def read_json(path: Path):
    """Parsed and cleaned JSON file, or None if it does not exist yet (missing input -> pending in the paper)."""
    if not path.exists():  # e.g. the assay or batch 1 has not run yet
        return None
    return clean(json.loads(path.read_text(encoding="utf-8")))  # json.loads accepts NaN; clean() removes it


def design() -> dict:
    """Preregistered design constants, read from the code that runs the experiment (not typed into the paper).

    Local: SwarmConfig defaults are the batch-1 values (prereg §2.1); replicate counts come from conditions.batch1
    (§2.2). Global: the paper prints N, K, T, m, attempts and word budgets from here.
    """
    cfg, llm, rt = SwarmConfig(), LLMConfig(), RuntimeConfig()  # defaults = preregistered values
    reps = Counter(c.condition for c in batch1("D"))  # replicates per condition (prompt variant does not matter)
    return {"N": cfg.n_agents, "K": cfg.k_read, "T": cfg.n_rounds, "m": cfg.n_seeds, "attempts": cfg.max_attempts,
            "post_words": cfg.post_words, "notes_words": cfg.notes_words, "code_tokens": cfg.max_code_tokens,
            "post_tokens": cfg.max_post_tokens, "exec_timeout_s": rt.exec_timeout_s, "model": llm.model,
            "temperature": llm.temperature, "top_p": llm.top_p, "top_k": llm.top_k, "min_p": llm.min_p,
            "presence_penalty_default": llm.presence_penalty, "replicates": dict(reps),
            "transient_last_seed_round": next(c.seed_last_round for c in batch1("D") if c.condition == "TRANSIENT"),
            "analysis_seed": RNG_SEED,
            # prompt texts as the agents see them (ImpossibleBench variants verbatim; probe/seed notes are ours)
            "prompts": {"instructions": P.INSTRUCTIONS, "flag_suffix": P.FLAG_SUFFIX.strip(),
                        "probe": P.PROBE_QUESTION, "seed_hack": P.SEED_NOTES_HACK,
                        "seed_placebo": P.SEED_NOTES_PLACEBO}}


def condition_prevalence(results: Path, T: int, B: int = 10000) -> dict | None:
    """Per condition: mean over runs of the run-level mean non-seed prevalence over rounds 1..T, with a 95% percentile
    bootstrap CI that resamples whole runs (cluster bootstrap, Field & Welsh 2007; prereg §9.1 uses the same idea).

    Local: reads results/prevalence_by_round.csv (condition, run_id, round, prevalence), written by run_all.
    Global: column 1 of the main results table (descriptive; the confirmatory contrast is the paired H1 test).
    """
    path = results / "prevalence_by_round.csv"  # per-run, per-round prevalence written by analysis.run_all
    if not path.exists():
        return None
    prev = pd.read_csv(path)  # long table
    prev = prev[prev["round"].between(1, T)]  # rounds 1..T (round 0 is the pre-treatment warm-up)
    rng = np.random.default_rng(RNG_SEED)  # fixed seed -> reproducible CIs
    out = {}
    for cond, g in prev.groupby("condition"):
        runs = g.groupby("run_id")["prevalence"].mean().to_numpy()  # run-level means P-bar_r (prereg §4.1)
        boots = runs[rng.integers(0, runs.size, (B, runs.size))].mean(1)  # B resamples of whole runs
        out[cond] = {"mean": float(runs.mean()), "ci_low": float(np.percentile(boots, 2.5)),
                     "ci_high": float(np.percentile(boots, 97.5)), "n_runs": int(runs.size)}
    return out


def pools_summary(pools: dict | None, B: int = 10000) -> dict | None:
    """Seed/placebo pool sizes, manipulation check (mean judge P(pro-hack) per pool, difference with a 95% bootstrap
    CI; prereg §5) and two example posts per pool for the appendix. Texts are frozen stimuli, not model results."""
    if not pools or "hack" not in pools:  # pools not finalized yet
        return None
    ph = np.array([p["p_pro"] for p in pools["hack"]], float)  # judge P(pro-hack), hack pool
    pp = np.array([p["p_pro"] for p in pools["placebo"]], float)  # judge P(pro-hack), placebo pool
    out = {"n_hack": len(ph), "n_placebo": len(pp), "n_candidates_hack": len(pools.get("_all_hack", [])),
           "n_candidates_placebo": len(pools.get("_all_placebo", [])),
           "manual_check_applied": pools.get("manual_check_applied")}
    if ph.size and pp.size:  # manipulation check: independent-pool bootstrap of the mean difference
        rng = np.random.default_rng(RNG_SEED)
        boots = (ph[rng.integers(0, ph.size, (B, ph.size))].mean(1) - pp[rng.integers(0, pp.size, (B, pp.size))].mean(1))
        out |= {"mean_p_pro_hack": float(ph.mean()), "mean_p_pro_placebo": float(pp.mean()),
                "diff": float(ph.mean() - pp.mean()), "diff_ci_low": float(np.percentile(boots, 2.5)),
                "diff_ci_high": float(np.percentile(boots, 97.5))}
    first = lambda items: [p["text"] for p in sorted(items, key=lambda p: p["pool_id"])[:2]]  # deterministic pick
    out["examples"] = {"hack": first(pools["hack"]), "placebo": first(pools["placebo"])}
    return out


def capability_summary(path: Path, need: int) -> dict | None:
    """Capability filter outcome (prereg §8.1): candidate tasks, tasks at >= 4/5 and >= 3/5, threshold used.

    Local: reuses `apply_capability_filter` (the rule the experiment applies) on task-id stand-ins, so the paper and
    the runs cannot disagree. Global: Methods, task paragraph.
    """
    counts = read_json(path)  # {task_id: strict passes out of 5}
    if counts is None:
        return None
    kept, thr = apply_capability_filter([SimpleNamespace(task_id=t) for t in counts], path, need=need)  # same rule
    return {"n_candidates": len(counts), "n_ge4": sum(v >= 4 for v in counts.values()),
            "n_ge3": sum(v >= 3 for v in counts.values()), "threshold": thr, "n_kept": len(kept), "need": need}


def h5_predicted(summary: dict | None, N: int) -> dict | None:
    """Mean predicted prevalence over rounds 1..T of each simulator (mean trajectory / N), next to the observed mean.

    Local: summary.h5[cond][model].mean_curve holds mean hacking counts per round (rounds 0..T). Global: panel B of
    the main results table.
    """
    h5 = (summary or {}).get("h5") or {}
    out = {}
    for cond, res in h5.items():
        row = {m: float(np.mean(res[m]["mean_curve"][1:]) / N) for m in ("assay_model", "broadcast_only")
               if m in res and "mean_curve" in res[m]}  # skip round 0, convert counts to prevalence
        if "observed_mean" in res:
            row["observed"] = float(np.mean(res["observed_mean"][1:]) / N)
        out[cond] = row
    return out or None


def _lt(x, threshold: float) -> bool:
    """x < threshold, treating a missing value (None, e.g. a NaN cleaned by `clean`) as 'criterion not met'."""
    return x is not None and x < threshold


def verdicts(summary: dict | None) -> dict:
    """Apply the preregistered falsification table (prereg §13) to summary.json; None where inputs are missing.

    Local: each entry is {"verdict": supported | falsified | inconclusive | partial, ...flags}; a hypothesis whose
    inputs do not exist yet has no entry (the paper prints "pending"). Where a rule needs a quantity that run_all does
    not output, the flag stays None and the verdict cannot be "falsified". Global: the hypothesis table in Results
    and the abstract.
    """
    s = summary or {}
    holm = s.get("holm") or {}  # Holm-adjusted p-values over the confirmatory family (prereg §9.6)
    out = {}
    h1 = (s.get("h1") or {}).get("MAIN_vs_PLACEBO") or {}  # H1: Holm p < .05 supports; paired TOST falsifies
    if h1:
        sup, fal = _lt(holm.get("H1"), ALPHA), _lt(h1.get("p_tost_paired"), ALPHA)
        # "Contrary evidence" = significant negative difference: exact two-sided sign-flip p < .05 and diff < 0 (§13).
        contrary = _lt(h1.get("p_signflip_two_sided"), ALPHA) and _lt(h1.get("diff"), 0)
        out["H1"] = {"verdict": "supported" if sup else ("falsified" if fal else "inconclusive"),
                     "supported": sup, "equivalent": fal, "contrary": contrary}
    h2 = s.get("h2") or {}
    if h2.get("k_nonseed_pro"):  # H2: Holm p < .05 supports; upper 90% CI bound of h1 below h1* falsifies (§13)
        sup, fal = _lt(holm.get("H2"), ALPHA), h2.get("falsified_h1_below_star")
        out["H2"] = {"verdict": "supported" if sup else ("falsified" if fal else "inconclusive"), "supported": sup,
                     "falsified": fal, "h1_ci90": h2.get("h1_ci90"), "h1_star": h2.get("h1_star")}
    h4 = s.get("h4") or {}  # H4: Holm LRT p < .05 supports; small Weibull-simple gap and no sigmoid win falsify
    if "lrt_simple_vs_weibull" in h4:
        sup = _lt(holm.get("H4"), ALPHA)
        gamma = h4["hack"]["weibull"]["params"].get("gamma")  # direction of departure from simple contagion
        fal = _lt(h4.get("falsification_maxdiff_ci90_upper"), 0.10) and not h4.get("sigmoid_aicc_preferred_by_2")
        out["H4"] = {"verdict": "supported" if sup else ("falsified" if fal else "inconclusive"), "supported": sup,
                     "falsified": fal,
                     "direction": None if gamma is None else ("reinforcing" if gamma > 1 else "saturating")}
    h3 = (s.get("h3") or {}).get("decision")  # H3: three-way decision computed by run_all (§9.4)
    if h3:
        out["H3"] = {"verdict": {"self-sustaining": "supported", "decaying": "falsified"}.get(h3, "inconclusive"),
                     "decision": h3}
    for cond, res in (s.get("h5") or {}).items():  # H5 per forecast target: all criteria / falsifier / partial
        a, b = res.get("assay_model") or {}, res.get("broadcast_only") or {}
        worse = a.get("crps") is not None and b.get("crps") is not None and a["crps"] >= b["crps"]  # CRPS* criterion
        fal = worse or _lt(a.get("coverage90"), 0.75)  # falsified if no better than broadcast-only or miscalibrated
        out[f"H5_{cond}"] = {"verdict": "supported" if res.get("supported") else ("falsified" if fal else "partial")}
    return out


def sync_figures(results: Path) -> list[str]:
    """Mirror results/figures/*.png that the paper uses into paper/figures/ (stale copies are deleted).

    Local: Typst only reads files inside the project root, and --results may point outside the repo (tests), so the
    figures are copied. Global: data.json["figures"] tells paper.typ which images exist; the rest render as pending.
    """
    dst = PAPER / "figures"
    dst.mkdir(parents=True, exist_ok=True)
    src = {n: results / "figures" / n for n in FIG_NAMES}  # paper name -> results file (run_all/make_all)
    src |= {f"explore_{n}": results / "explore" / "figures" / n for n in EXPLORE_FIGS}  # exploratory batch
    present = [n for n, f in src.items() if f.exists()]
    for p in dst.glob("*.png"):  # remove figures from an earlier build that no longer exist in results
        if p.name not in present:
            p.unlink()
    for n in present:
        shutil.copy2(src[n], dst / n)  # copy with timestamps (reproducible provenance)
    return present


def collect(results: Path, data: Path) -> dict:
    """Assemble paper/data.json from results files, frozen pilot data files and code constants."""
    d = design()
    summary = read_json(results / "summary.json")  # the preregistered analysis output (None before batch 1)
    pilot = {name: read_json(data / f"{name}.json")  # frozen pilot outputs (prereg §8), each optional
             for name in ("sampling", "calibration", "audit_results", "power", "sim_params")}
    engineering = {p.stem: read_json(p) for p in sorted((results / "engineering").glob("*.json"))}  # smoke tests
    return clean({
        "design": d,
        "summary": summary,
        "pilot": pilot | {"capability": capability_summary(data / "capability.json", d["N"] * (d["T"] + 1)),
                          "pools": pools_summary(read_json(data / "pools.json"))},
        "derived": {"prevalence": condition_prevalence(results, d["T"]), "h5_predicted": h5_predicted(summary, d["N"])},
        "verdicts": verdicts(summary),
        "explore": read_json(results / "explore" / "summary.json"),  # exploratory batch (deviation #13), not pooled
        "explore_derived": {"prevalence": condition_prevalence(results / "explore", d["T"])},
        "explore_calibration": read_json(data / "calibration_explore.json"),  # frozen calibration of that batch
        "engineering": engineering or None,
        "figures": sync_figures(results),
    })


def compile_pdf() -> None:
    """Compile paper/paper.typ -> paper/paper.pdf with the repo as Typst root; print every compiler warning.

    Local: `compile_with_warnings(input, output=..., root=...)` returns (None, warnings) when `output` is given
    (typst-py 0.15.2 type stubs); compilation errors raise typst.TypstError with a diagnostic message.
    """
    _, warnings = typst.compile_with_warnings(str(PAPER / "paper.typ"), output=str(PAPER / "paper.pdf"),
                                              root=str(ROOT))
    for w in warnings:  # e.g. missing glyphs or unknown fonts: layout problems worth fixing
        print(f"typst warning: {w.message}\n{w.diagnostic}")
    print(f"wrote {PAPER / 'paper.pdf'} ({len(warnings)} warnings)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, default=ROOT / "results", help="results dir (summary.json, figures/)")
    ap.add_argument("--data", type=Path, default=ROOT / "data", help="frozen pilot data dir")
    ap.add_argument("--no-compile", action="store_true", help="only write paper/data.json")
    args = ap.parse_args()
    payload = collect(args.results, args.data)  # everything the paper prints
    (PAPER / "data.json").write_text(json.dumps(payload, indent=1, allow_nan=False, ensure_ascii=False),
                                     encoding="utf-8")  # allow_nan=False guarantees strict JSON for Typst
    print(f"wrote {PAPER / 'data.json'}: summary={'yes' if payload['summary'] else 'pending'}, "
          f"figures={payload['figures']}")
    if not args.no_compile:
        compile_pdf()


if __name__ == "__main__":
    main()
