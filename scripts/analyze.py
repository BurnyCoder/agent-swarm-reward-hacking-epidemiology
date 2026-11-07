"""One command regenerates every table, number and figure from results files (no hand-typed numbers).

Usage: uv run python scripts/analyze.py [--runs $RUNS_DIR]
Reads $RUNS_DIR/batch1 (swarm runs), $RUNS_DIR/assay/assay.jsonl (dose-response assay) and results/post_labels.json
(judge labels); writes results/summary.json, results/*.csv|parquet and results/figures/*.png.
"""

from __future__ import annotations  # forward references

import argparse  # CLI
import json  # pretty print
from pathlib import Path  # paths

from swarm_epi import analysis, figures  # analysis + figures
from swarm_epi.config import RuntimeConfig  # default paths

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, default=RuntimeConfig().runs_dir, help="raw runs root")
    ap.add_argument("--batch", default="batch1", help="batch sub-directory")
    ap.add_argument("--results", type=Path, default=Path("results"), help="output directory (git-tracked)")
    args = ap.parse_args()
    summary = analysis.run_all(args.runs / args.batch, args.runs / "assay" / "assay.jsonl",
                               args.results / "post_labels.json", args.results)
    print(json.dumps({k: summary[k] for k in ("n_runs", "holm", "epi_parameters")}, indent=1, default=float))
    print("figures:", figures.make_all(args.results))
