"""Post-hoc sensitivity of the exploratory R0 to the judge's miss rate on pro-hack posts (reads results files only).

Usage: uv run python scripts/judge_sensitivity.py   -> results/explore/judge_sensitivity.json

Local context: the blinded judge audit (data/audit_results.json, deviation #7) samples up to 70 posts per JUDGE label
from the exploratory batch, so P(blind = pro | judge = L) is estimated within each judge label L. Weighting these
rates by the batch's judge-label counts (results/explore/post_labels.json, non-seed posts only) estimates the number
of truly pro-hack posts, and the judge's sensitivity for pro-hack posts = (judged pro AND blind pro) / (estimated
truly pro). Standard stratified estimator of a misclassification rate; e.g. Lohr, Sampling: Design and Analysis, §3.
R0 = pi*K*h1*D is linear in pi = P(pro-hack post | author hacked). If every missed pro-hack post came from a hacking
author, pi would be at most pi / sensitivity, so R0_pi_corrected = R0 * min(1, pi / sensitivity) / pi is a first-order upper value with
h1 and D held fixed. It ignores that h1 itself is estimated with misclassified exposure; the judge-free exposure in
H2 (posts by authors who hacked) is the check that does not depend on the judge.
Global context: an exploratory, post-hoc analysis added after the audit (reports/deviations.md #17); it changes no
preregistered quantity.
"""

from __future__ import annotations  # forward references

import json  # results files
from collections import Counter  # label counts
from pathlib import Path  # paths

from statsmodels.stats.proportion import proportion_confint  # Wilson bounds (Brown, Cai & DasGupta 2001)

ROOT = Path(__file__).resolve().parents[1]  # repo root


def main() -> None:
    audit = json.loads((ROOT / "data" / "audit_results.json").read_text(encoding="utf-8"))["judge"]
    conf = audit["confusion_judge_x_blind"]  # {judge label: {blind label: count}}
    labels = json.loads((ROOT / "results" / "explore" / "post_labels.json").read_text(encoding="utf-8"))
    counts = Counter(v["label"] for k, v in labels.items() if not k.startswith("pool:"))  # non-seed agent posts
    p_pro = {L: row.get("pro", 0) / sum(row.values()) for L, row in conf.items()}  # P(blind pro | judge L)
    est_true_pro = sum(counts[L] * p_pro.get(L, 0.0) for L in counts)  # stratified estimate
    sens = counts["pro"] * p_pro.get("pro", 0.0) / est_true_pro if est_true_pro else None
    # worst case for the judge: upper 95% Wilson bound of P(blind pro | judge L) for the labels that are not "pro"
    # (0/70 among judge-anti still allows a few percent of 7,000+ posts)
    hi = {L: (p_pro[L] if L == "pro" else proportion_confint(row.get("pro", 0), sum(row.values()), method="wilson")[1])
          for L, row in conf.items()}
    est_hi = sum(counts[L] * hi.get(L, 0.0) for L in counts)
    sens_lo = counts["pro"] * p_pro.get("pro", 0.0) / est_hi if est_hi else None
    s = json.loads((ROOT / "results" / "explore" / "summary.json").read_text(encoding="utf-8"))["h3"]["R0"]
    f = lambda se: min(1.0, s["pi"] / se) / s["pi"] if se else None  # R0 scale factor; pi is a probability, so <= 1
    out = {"judge_label_counts": dict(counts), "p_blind_pro_given_judge": p_pro,
           "estimated_true_pro_posts": est_true_pro, "judge_pro_sensitivity": sens,
           "pi": s["pi"], "pi_corrected_upper": min(1.0, s["pi"] / sens) if sens else None,
           "R0": s["R0"], "R0_pi_corrected_upper": s["R0"] * f(sens) if sens else None,
           "R0_ci95_high_pi_corrected": s["R0_ci95"][1] * f(sens) if sens else None,
           "judge_pro_sensitivity_worst_case": sens_lo,
           "R0_pi_corrected_worst_case": s["R0"] * f(sens_lo) if sens_lo else None,
           "R0_ci95_high_pi_corrected_worst_case": s["R0_ci95"][1] * f(sens_lo) if sens_lo else None}
    path = ROOT / "results" / "explore" / "judge_sensitivity.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
