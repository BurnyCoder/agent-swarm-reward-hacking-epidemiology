"""One command regenerates every table, number and figure from results files (no hand-typed numbers).

Usage: uv run python scripts/analyze.py [--runs $RUNS_DIR] [--batch week1]
Reads $RUNS_DIR/batch1 (swarm runs), $RUNS_DIR/assay/assay.jsonl (dose-response assay) and results/post_labels.json
(judge labels); writes results/summary.json, results/*.csv|parquet, results/figures/*.png and site/index.html.
"""

from __future__ import annotations  # forward references

import argparse  # CLI
import json  # pretty print
from pathlib import Path  # paths

from swarm_epi import analysis, conditions, figures, site  # analysis, W1 partners, figures, site
from swarm_epi.config import RuntimeConfig  # default paths

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, default=RuntimeConfig().runs_dir, help="raw runs root")
    ap.add_argument("--batch", default="batch1", help="batch sub-directory")
    ap.add_argument("--results", type=Path, default=None,
                    help="output dir (default results/ for batch1, else results/<batch>/)")
    args = ap.parse_args()
    args.results = args.results or (Path("results") if args.batch == "batch1" else Path("results") / args.batch)
    if args.batch == "week1":  # week-phase ablations: paired contrasts with batch-1 partners (preregistration_week1.md)
        summary = analysis.run_week1(args.runs / "week1", args.runs / "batch1", args.results, conditions.WEEK1_PARTNERS)
        print(json.dumps({k: summary.get(k) for k in ("n_runs", "holm_hack", "holm_flag")}, indent=1, default=float))
        print("figures:", figures.make_week1(args.results, conditions.WEEK1_PARTNERS) if summary else [])
        raise SystemExit(0)
    summary = analysis.run_all(args.runs / args.batch, args.runs / "assay" / "assay.jsonl",
                               args.results / "post_labels.json", args.results)
    print(json.dumps({k: summary.get(k) for k in ("n_runs", "holm")}, indent=1, default=float))  # headline only
    print("figures:", figures.make_all(args.results))
    print("site:", site.build(args.results, Path("site")))  # private HF Space page
