"""Single entry point: run any phase of the study by name.

Usage (inside WSL, with the vLLM server up):  uv run python scripts/run_experiment.py <phase> [--parallel 4]
Phases, in pre-registered order:
  smoke       tiny end-to-end run (N=8, T=3) to check wiring, logging, grading and the dashboard
  capability  capability filter on the ORIGINAL tasks           -> data/capability.json
  pools       hack/placebo seed pools (generated, judged)        -> data/pools.json
  calibrate   ImpossibleBench prompt-variant calibration         -> data/calibration.json
  pilot       2 MAIN + 2 PLACEBO pilot swarms                    -> $RUNS_DIR/pilot/
  harvest     assay pools + PLACEBO note snapshots from pilot    -> data/assay_pools.json
  assay       randomized dose-response assay                     -> $RUNS_DIR/assay/assay.jsonl
  batch1      MAIN x20, PLACEBO x20, TRANSIENT x15 swarms        -> $RUNS_DIR/batch1/
  judge       label every post (batch1 board, seed pools, assay)  -> results/post_labels.json
Each phase is resumable: re-running skips finished work.
"""

from __future__ import annotations  # forward references

import argparse  # CLI
import asyncio  # event loop
import json  # data files
import logging  # progress
from pathlib import Path  # paths

from swarm_epi import conditions, pilot  # condition lists + pilot phases
from swarm_epi import prompts as P  # provisional smoke pools
from swarm_epi.config import LLMConfig, RuntimeConfig, SwarmConfig  # settings
from swarm_epi.dose_response import make_trials, run_trials  # assay
from swarm_epi.grader import Sandbox  # code execution
from swarm_epi.judge import judge_many  # post judge
from swarm_epi.llm import LLM, setup_logging  # inference + logging
from swarm_epi.swarm import run_swarm  # one replicate
from swarm_epi.tasks import apply_capability_filter, load_tasks  # tasks

DATA = Path(__file__).resolve().parents[1] / "data"  # frozen inputs committed to git
log = logging.getLogger("run_experiment")  # script logger


def read_json(name: str) -> dict:
    """Load a frozen data file from data/."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


async def run_many(cfgs: list[SwarmConfig], llm: LLM, sandbox: Sandbox, tasks, pools, out_dir: Path,
                   parallel: int) -> None:
    """Run swarm replicates with at most `parallel` in flight (keeps the GPU batch full while rounds synchronize)."""
    sem = asyncio.Semaphore(parallel)  # concurrency cap

    async def one(cfg: SwarmConfig) -> None:
        async with sem:
            await run_swarm(cfg, llm, sandbox, tasks, pools, out_dir)

    await asyncio.gather(*(one(c) for c in cfgs))


async def main(args: argparse.Namespace) -> None:
    rt = RuntimeConfig()  # paths + sandbox
    runs = rt.runs_dir  # raw output root
    jsonl = setup_logging(runs / "logs", args.phase)  # timestamped log + LLM-call JSONL
    llm = LLM(LLMConfig(), jsonl_path=jsonl, echo=not args.quiet)  # inference client
    sandbox = Sandbox(rt.sandbox, rt.sandbox_concurrency, rt.exec_timeout_s)  # isolation backend
    DATA.mkdir(exist_ok=True)
    all_tasks = load_tasks()  # 954 impossible MBPP tasks (setup-free)
    cap = DATA / "capability.json"
    tasks = apply_capability_filter(all_tasks, cap) if cap.exists() else all_tasks  # prereg capability filter
    log.info("phase=%s tasks=%d (filtered=%s) runs_dir=%s", args.phase, len(tasks), cap.exists(), runs)
    variant = read_json("calibration.json")["chosen"] if (DATA / "calibration.json").exists() else "D"

    if args.phase == "smoke":
        pools = {"hack": [{"pool_id": f"smoke{i}", "text": P.SEED_NOTES_HACK} for i in range(2)]}  # provisional
        await run_many(conditions.smoke(variant), llm, sandbox, all_tasks, pools, runs / "smoke", 1)
    elif args.phase == "capability":
        await pilot.capability_pass(llm, sandbox, all_tasks, cap)
    elif args.phase == "pools":
        await pilot.build_pools(llm, sandbox, tasks, DATA / "pools.json", n=args.n or 200)
    elif args.phase == "calibrate":
        res = await pilot.calibrate(llm, sandbox, tasks, read_json("pools.json"), runs / "calibration", n=args.n or 50)
        (DATA / "calibration.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    elif args.phase == "pilot":
        await run_many(conditions.pilot(variant), llm, sandbox, tasks, read_json("pools.json"), runs / "pilot",
                       args.parallel)
    elif args.phase == "harvest":
        dirs = sorted(p for p in (runs / "pilot").iterdir() if (p / "board.jsonl").exists())
        await pilot.harvest(llm, dirs, read_json("pools.json"), DATA / "assay_pools.json")
    elif args.phase == "assay":
        ap = read_json("assay_pools.json")  # pro / anti / neutral pools + snapshots
        cells = [(k, 0, "distinct") for k in (0, 1, 2, 3, 4, 6)] + [(k, 2, "distinct") for k in (0, 1, 2, 3, 4)]
        cells += [(k, 0, "same") for k in (2, 4)] + [(k, 0, "offtopic") for k in (2, 4)]  # Centola + random control
        trials = make_trials(cells, args.n or 150, ap, [tuple(s) for s in ap["snapshots"]], len(tasks), 6, seed=7)
        (runs / "assay").mkdir(parents=True, exist_ok=True)
        await run_trials(trials, llm, sandbox, SwarmConfig(condition="ASSAY", prompt_variant=variant), tasks,
                         runs / "assay" / "assay.jsonl", "assay")
    elif args.phase == "batch1":
        await run_many(conditions.batch1(variant), llm, sandbox, tasks, read_json("pools.json"), runs / "batch1",
                       args.parallel)
    elif args.phase == "judge":
        labels = {}  # post key -> judge scores
        for item in read_json("pools.json")["hack"] + read_json("pools.json")["placebo"]:
            labels[f"pool:{item['pool_id']}"] = {k: item[k] for k in ("p_pro", "p_anti", "p_neutral", "label")}
        todo = {}  # unlabeled texts
        for d in sorted(p for p in (runs / "batch1").iterdir() if (p / "board.jsonl").exists()):
            for line in (d / "board.jsonl").read_text(encoding="utf-8").splitlines():
                post = json.loads(line)
                if not post["is_seed"]:
                    todo[f"{d.name}:{post['post_id']}"] = post["text"]
        assay = runs / "assay" / "assay.jsonl"
        if assay.exists():
            for line in assay.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                todo[f"assay:{row['trial_id']}"] = row["post_text"]
        labels |= await judge_many(llm, todo)
        out = Path("results") / "post_labels.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(labels, indent=0), encoding="utf-8")
    log.info("phase %s finished; generated tokens: %d", args.phase, llm.tokens_out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["smoke", "capability", "pools", "calibrate", "pilot", "harvest", "assay",
                                      "batch1", "judge"])
    ap.add_argument("--parallel", type=int, default=4, help="concurrent swarm replicates")
    ap.add_argument("--n", type=int, default=None, help="override trial/pool counts (pilot use)")
    ap.add_argument("--quiet", action="store_true", help="do not echo every LLM call to the terminal")
    asyncio.run(main(ap.parse_args()))
