"""Publish results to Hugging Face, all PUBLIC: a dataset (results, pilot data, reports, paper, optionally raw logs),
a static Space (the interactive site), and one collection holding both.

Usage:
  uv run python scripts/publish_hf.py --create-only      # create the public repos and collection (or make them public)
  uv run python scripts/publish_hf.py [--raw RUNS_DIR]   # upload everything (raw runs/logs only if --raw is given)
Local context: huggingface_hub 2.x `HfApi` (https://huggingface.co/docs/huggingface_hub/package_reference/hf_api):
`create_repo(repo_id, private=False, repo_type=..., space_sdk="static", exist_ok=True)`, `upload_folder(...)`,
`create_collection(title, private=False, exists_ok=True)`, `add_collection_item(slug, item_id, item_type, exists_ok=True)`.
`create_repo`/`create_collection` with `exist_ok` return an existing item unchanged, so a repo or collection created
private earlier is switched with `update_repo_settings(repo_id, private=False, repo_type=...)` and
`update_collection_metadata(slug, private=False)`, then re-read; the script stops if anything is still private
(user decision 2026-11-15: the GitHub repo is public, so the data, site and collection are public too). The token
comes from the local `hf auth login`; it is never printed. `.env`, caches and virtualenvs are excluded from every upload.
Global context: run after `scripts/analyze.py`, `scripts/make_reports.py` and `scripts/make_paper.py`.
"""

from __future__ import annotations  # forward references

import argparse  # CLI
import shutil  # copy site files
import tempfile  # staging dir for the Space
from pathlib import Path  # paths

from huggingface_hub import HfApi  # Hub client (uses the cached login token)

ROOT = Path(__file__).resolve().parents[1]  # repo root
NAME = "agent-swarm-reward-hacking-epidemiology"  # same name for the dataset and the Space (different repo types)
TITLE = "Reward-hacking epidemics in a local LLM agent swarm"  # collection title
IGNORE = [".env", "*.env", "**/.venv/**", "**/__pycache__/**", "**/.cache/**", "**/*.pyc", "**/trackio_data/**"]
DATASET_CARD = f"""---
license: cc-by-4.0
pretty_name: Reward-hacking epidemics in a local LLM agent swarm
tags: [reward-hacking, multi-agent, contagion, epidemiology, impossiblebench]
---
# Reward-hacking epidemics in a local LLM agent swarm — data

Results, pilot files, reports and the paper for the project of the same name. Code:
[github.com/BurnyCoder/{NAME}](https://github.com/BurnyCoder/{NAME}); interactive results explorer:
[GitHub Pages](https://burnycoder.github.io/{NAME}/) and the
[Hugging Face Space](https://huggingface.co/spaces/BurnyCoder/{NAME}). Layout: `results/` (analysis outputs: `summary.json`, tables, figures), `data/` (frozen
pilot files: capability filter, pools, calibration, audits), `reports/` (preregistration, deviations, experiment
reports), `paper/` (PDF), and, when uploaded, `raw/` (per-run `rounds.jsonl`/`board.jsonl` and complete LLM call logs).
Task data derive from `AlignmentResearch/mbpp-honeypot-impossible-oneoff` (CC-BY-4.0); seed beliefs adapt
`longtermrisk/school-of-reward-hacks` (CC-BY-4.0).
"""
SPACE_CARD = """---
title: Reward-hacking epidemics (results explorer)
sdk: static
app_file: index.html
pinned: false
---
Interactive results explorer for the reward-hacking contagion experiments.
Code, data and paper: https://github.com/BurnyCoder/agent-swarm-reward-hacking-epidemiology
"""


def ensure_public(api: HfApi, repo_id: str, repo_type: str, **kw) -> str:
    """Create the repo as public if missing, switch it to public if it exists as private, verify; returns its URL."""
    url = api.create_repo(repo_id, private=False, repo_type=repo_type, exist_ok=True, **kw)  # no-op if it exists
    if api.repo_info(repo_id, repo_type=repo_type).private:  # created private earlier: flip the visibility
        api.update_repo_settings(repo_id, private=False, repo_type=repo_type)  # huggingface_hub >= 0.25 API
    if api.repo_info(repo_id, repo_type=repo_type).private:  # re-read: the flip must have taken effect
        raise SystemExit(f"{repo_type} {repo_id} is still private; refusing to continue")
    return str(url)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--create-only", action="store_true")
    ap.add_argument("--raw", type=Path, help="RUNS_DIR with raw runs and logs to upload under raw/")
    a = ap.parse_args()
    api = HfApi()
    user = api.whoami()["name"]  # e.g. BurnyCoder
    ds, sp = f"{user}/{NAME}", f"{user}/{NAME}"
    print("dataset:", ensure_public(api, ds, "dataset"))
    print("space:  ", ensure_public(api, sp, "space", space_sdk="static"))
    coll = api.create_collection(TITLE, private=False, exists_ok=True,  # returns the existing one unchanged
                                 description="Data, results explorer and paper for the swarm contagion study.")
    if coll.private:  # created private earlier: flip it (returns the updated Collection)
        coll = api.update_collection_metadata(coll.slug, private=False)
    if coll.private:  # the collection must be public too
        raise SystemExit(f"collection {coll.slug} is still private")
    for item, kind in ((ds, "dataset"), (sp, "space")):
        api.add_collection_item(coll.slug, item, kind, exists_ok=True)  # one collection for this research
    print("collection:", coll.url)
    if a.create_only:
        return
    with tempfile.TemporaryDirectory() as tmp:  # dataset staging: card + the folders that exist
        card = Path(tmp) / "README.md"
        card.write_text(DATASET_CARD, encoding="utf-8")
        api.upload_file(path_or_fileobj=str(card), path_in_repo="README.md", repo_id=ds, repo_type="dataset")
    for folder in ("results", "data", "reports", "paper"):
        if (ROOT / folder).exists():
            api.upload_folder(repo_id=ds, repo_type="dataset", folder_path=ROOT / folder, path_in_repo=folder,
                              ignore_patterns=IGNORE, commit_message=f"Update {folder}/")
            print("uploaded", folder)
    if a.raw:  # raw runs + full LLM call logs (large)
        api.upload_folder(repo_id=ds, repo_type="dataset", folder_path=a.raw, path_in_repo="raw",
                          ignore_patterns=IGNORE, commit_message="Update raw runs and logs")
        print("uploaded raw from", a.raw)
    site = ROOT / "site"
    if (site / "index.html").exists():  # static Space = the interactive site
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(site, tmp, dirs_exist_ok=True)
            (Path(tmp) / "README.md").write_text(SPACE_CARD, encoding="utf-8")
            api.upload_folder(repo_id=sp, repo_type="space", folder_path=tmp, commit_message="Update site")
        print("uploaded site to the Space")


if __name__ == "__main__":
    main()
