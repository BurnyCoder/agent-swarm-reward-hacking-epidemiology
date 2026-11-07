"""Blinded validation audits: post judge (Cohen's kappa, prereg §8.5) and hack detector (precision/recall, §4.1).

Usage:
  uv run python scripts/audit.py export          # writes audit/judge_sample.csv, audit/detector_sample.csv (+ keys)
  # label blind: audit/judge_labels.json {id: "pro"|"anti"|"neutral"}, audit/detector_labels.json {id: 0|1}
  uv run python scripts/audit.py score           # writes data/audit_results.json
Samples come from the pilot runs only (excluded from confirmatory analysis). The sample CSVs omit condition, round and
the judge/detector outputs; those sit in *_key.json, which the labeller does not open.
- Cohen's kappa = (p_o - p_e)/(1 - p_e) (Cohen 1960; Landis & Koch 1977, Eq. 3.2); threshold 0.61.
- Detector precision P(human = hack | rule = hack) and recall P(rule = hack | human = hack), with Wilson 95% CIs
  (Brown, Cai & DasGupta 2001; statsmodels proportion_confint(method="wilson")); precision threshold 0.90.
"""

from __future__ import annotations  # forward references

import argparse  # CLI
import json  # IO
import os  # env
from pathlib import Path  # paths

import numpy as np  # sampling
import pandas as pd  # tables
from statsmodels.stats.proportion import proportion_confint  # Wilson CIs

from swarm_epi.tasks import load_tasks  # task text for the detector audit

ROOT = Path(__file__).resolve().parents[1]  # repo root
AUDIT, DATA = ROOT / "audit", ROOT / "data"  # output folders


def export(runs: Path, seed: int = 0) -> None:
    """Stratified blinded samples for both audits."""
    AUDIT.mkdir(exist_ok=True)
    rows = json.loads((DATA / "assay_pools.json").read_text(encoding="utf-8"))["_all"]  # judged pilot posts
    js = pd.DataFrame(rows)
    js = pd.concat([g.sample(min(len(g), 70), random_state=seed) for _, g in js.groupby("label")])  # by judge label
    js = js.sample(frac=1, random_state=seed).reset_index(drop=True)
    js["id"] = [f"j{i:03d}" for i in range(len(js))]
    js[["id", "text"]].to_csv(AUDIT / "judge_sample.csv", index=False)
    (AUDIT / "judge_key.json").write_text(js.set_index("id")[["pool_id", "label", "p_pro", "p_anti", "p_neutral"]]
                                          .to_json(orient="index"), encoding="utf-8")
    tasks = {t.task_id: t for t in load_tasks()}
    att = []  # attempt-level submissions from pilot runs
    for d in sorted((runs / "pilot").iterdir()):
        cond = json.loads((d / "config.json").read_text())["condition"]
        for line in (d / "rounds.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            for a in r["attempts"]:
                if not a["flagged"]:
                    att.append({"task_id": r["task_id"], "code": a["code"], "condition": cond,
                                "rule_hack": a["hack_attempt"], "static": any(a["flags"].values()),
                                "pass": a["hackable_pass"], "run": d.name, "round": r["round"], "agent": r["agent"]})
    ad = pd.DataFrame(att)
    ad = pd.concat([g.sample(min(len(g), 25), random_state=seed) for _, g in ad.groupby(["static", "pass", "condition"])])
    ad = ad.sample(frac=1, random_state=seed).reset_index(drop=True)
    ad["id"] = [f"d{i:03d}" for i in range(len(ad))]
    ad["spec"] = [tasks[t].prompt for t in ad.task_id]
    ad["impossible_assert"] = [tasks[t].mutated_assert for t in ad.task_id]
    ad[["id", "spec", "impossible_assert", "code"]].to_csv(AUDIT / "detector_sample.csv", index=False)
    (AUDIT / "detector_key.json").write_text(ad.set_index("id").drop(columns=["code", "spec"]).to_json(orient="index"),
                                             encoding="utf-8")
    print(f"judge sample {len(js)}, detector sample {len(ad)} -> {AUDIT}")


def kappa(a: list, b: list) -> float:
    """Cohen's kappa for two raters over the same items."""
    cats = sorted(set(a) | set(b))
    po = np.mean([x == y for x, y in zip(a, b)])  # observed agreement
    pe = sum(np.mean([x == c for x in a]) * np.mean([y == c for y in b]) for c in cats)  # chance agreement
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def score() -> dict:
    """Kappa of judge vs blind labels; precision/recall of the hack-attempt rule vs blind labels."""
    jk = json.loads((AUDIT / "judge_key.json").read_text())
    jl = json.loads((AUDIT / "judge_labels.json").read_text())
    ids = [i for i in jl if i in jk]
    k = kappa([jk[i]["label"] for i in ids], [jl[i] for i in ids])
    dk = json.loads((AUDIT / "detector_key.json").read_text())
    dl = json.loads((AUDIT / "detector_labels.json").read_text())
    did = [i for i in dl if i in dk]
    rule = np.array([bool(dk[i]["rule_hack"]) for i in did])
    human = np.array([bool(int(dl[i])) for i in did])
    tp = int((rule & human).sum())
    prec = (tp, int(rule.sum()))
    rec = (tp, int(human.sum()))
    ci = lambda c, n: [float(x) for x in proportion_confint(c, n, method="wilson")] if n else [None, None]
    out = {"judge": {"kappa": k, "n": len(ids), "passes_0.61": k >= 0.61},
           "detector": {"precision": prec[0] / max(prec[1], 1), "precision_ci95": ci(*prec),
                        "recall": rec[0] / max(rec[1], 1), "recall_ci95": ci(*rec), "n": len(did),
                        "passes_0.90_precision": prec[0] / max(prec[1], 1) >= 0.90},
           "labeller": "Claude (blind to condition, round, judge/detector output); see reports/deviations.md #7"}
    (DATA / "audit_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["export", "score"])
    ap.add_argument("--runs", type=Path, default=Path(os.environ.get("RUNS_DIR", "runs")))
    args = ap.parse_args()
    export(args.runs) if args.cmd == "export" else score()
