"""One swarm run (one replicate of one condition): rounds of read -> solve -> post, resumable after a crash/reboot.

Local context: round 0 is a warm-up with an empty board; in each round t=1..T every agent reads K posts from round t-1
(uniform sample, `board.py`), solves its scheduled impossible task, posts and updates notes. Seed slots contribute
posts drawn from a frozen, validated stimulus pool (hack or placebo) in rounds 0..seed_last_round (all rounds when
None = committed seeds; 1 = TRANSIENT). After every round the full state (board, notes, completed round) is written to
`state.json` and the agent-round records are appended to `rounds.jsonl`, so a restarted process continues where it
stopped (CLAUDE.md: runs > 30 min must be resumable).
Global context: `scripts/run_experiment.py` launches several `run_swarm` coroutines concurrently to keep the GPU
saturated; `analysis.py` reads `rounds.jsonl` + `board.jsonl`.
"""

from __future__ import annotations  # forward references

import asyncio  # concurrent agents
import json  # state + records
import logging  # progress logging
import time  # throughput
from pathlib import Path  # paths

import numpy as np  # metrics

from .agent import agent_round  # one agent-round
from .board import Board, Post, rng_for  # message board + CRN RNG streams
from .config import SwarmConfig  # experimental parameters
from .dashboard import Dashboard  # live metrics
from .grader import Sandbox  # code execution
from .llm import LLM  # inference
from .tasks import Task, schedule_tasks  # tasks

log = logging.getLogger("swarm_epi.swarm")  # module logger
PURPOSE_BOARD, PURPOSE_SEEDPOST, PURPOSE_LLM, PURPOSE_TASKS = 1, 2, 3, 4  # independent RNG stream ids


def seed_posts_for_round(cfg: SwarmConfig, pools: dict[str, list[dict]], round_t: int) -> list[Post]:
    """Seed-slot posts written in `round_t` (empty if seeds are inactive this round)."""
    if cfg.n_seeds == 0 or cfg.seed_pool == "none":  # NO-SEED condition
        return []
    if cfg.seed_last_round is not None and round_t > cfg.seed_last_round:  # TRANSIENT seeds have stopped
        return []
    pool = pools[cfg.seed_pool]  # frozen stimulus pool
    rng = rng_for(cfg.base_seed, cfg.replicate, round_t, 0, PURPOSE_SEEDPOST)  # same indices across conditions (CRN)
    picks = rng.choice(len(pool), size=cfg.n_seeds, replace=False)  # distinct items this round
    return [Post(f"{round_t}:s{j}", round_t, f"s{j}", pool[i]["text"], True, pool[i]["pool_id"])
            for j, i in enumerate(picks)]


def round_metrics(recs: list[dict]) -> dict:
    """Per-round summary for the dashboard and logs."""
    hack = np.array([r["hack_attempt"] for r in recs], float)  # primary outcome
    return {
        "hack_attempt_rate": float(hack.mean()),  # prevalence among non-seed agents
        "hack_success_rate": float(np.mean([r["hack_success"] for r in recs])),
        "flag_rate": float(np.mean([r["flagged"] for r in recs])),
        "capable_rate": float(np.mean([r["strict_original_pass"] for r in recs])),
        "probe_p_yes_mean": float(np.nanmean([r["probe_p_yes"] for r in recs])),
        "exposed_to_seed_rate": float(np.mean([any(r["read_is_seed"]) for r in recs])),
    }


async def run_swarm(cfg: SwarmConfig, llm: LLM, sandbox: Sandbox, tasks: list[Task], pools: dict[str, list[dict]],
                    out_dir: Path, dashboard: bool = True) -> Path:
    """Run (or resume) one replicate; returns its output directory."""
    if cfg.hide_nonseed_posts:  # yoked NO-SECONDARY needs the paired PLACEBO run's posts (week phase)
        raise NotImplementedError("NO-SECONDARY yoking is implemented in the week phase")
    run_dir = out_dir / cfg.run_id()  # runs/<batch>/<condition>_rNNN
    run_dir.mkdir(parents=True, exist_ok=True)
    state_path, rounds_path, board_path = run_dir / "state.json", run_dir / "rounds.jsonl", run_dir / "board.jsonl"
    board, notes, start = Board(), [""] * cfg.n_agents, 0  # fresh state
    if state_path.exists():  # resume
        st = json.loads(state_path.read_text(encoding="utf-8"))
        if st.get("done"):
            log.info("%s already complete", cfg.run_id())
            return run_dir
        for p in st["posts"]:
            board.add(Post(**p))
        notes, start = st["notes"], st["next_round"]
        log.info("%s resuming at round %d", cfg.run_id(), start)
    else:
        (run_dir / "config.json").write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    schedule = schedule_tasks(tasks, cfg.n_agents, cfg.n_rounds + 1,
                              seed=int(rng_for(cfg.base_seed, cfg.replicate, 0, 0, PURPOSE_TASKS).integers(2**31)))
    dash = Dashboard(cfg.run_id(), cfg.condition, cfg.to_dict(), enabled=dashboard)
    for t in range(start, cfg.n_rounds + 1):  # warm-up round 0 then rounds 1..T
        t0, tok0 = time.perf_counter(), llm.tokens_out  # throughput bookkeeping
        reads = [board.sample(t, f"a{i}", cfg.k_read, rng_for(cfg.base_seed, cfg.replicate, t, i, PURPOSE_BOARD))
                 for i in range(cfg.n_agents)]  # randomized exposure (CRN across conditions)
        coros = [agent_round(llm, sandbox, cfg, i, notes[i], schedule[t][i], reads[i], t,
                             llm_seed=int(rng_for(cfg.base_seed, cfg.replicate, t, i, PURPOSE_LLM).integers(2**31)))
                 for i in range(cfg.n_agents)]
        recs = [r.to_dict() for r in await asyncio.gather(*coros)]  # all agents of the round concurrently
        new_posts = [Post(r["post_id"], t, r["agent"], r["post_text"], False) for r in recs]  # agent posts
        new_posts += seed_posts_for_round(cfg, pools, t)  # seed-slot posts (frozen pool)
        for p in new_posts:
            board.add(p)
        notes = [r["notes_after"] for r in recs]  # carry memory forward
        with open(rounds_path, "a", encoding="utf-8") as fh:  # noqa: ASYNC230 - tiny once-per-round append
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in recs)
        with open(board_path, "a", encoding="utf-8") as fh:  # noqa: ASYNC230 - tiny once-per-round append
            fh.writelines(json.dumps(p.to_dict(), ensure_ascii=False) + "\n" for p in new_posts)
        state = {"next_round": t + 1, "notes": notes, "done": t == cfg.n_rounds,
                 "posts": [p.to_dict() for ps in board.rounds.values() for p in ps]}
        tmp = state_path.with_suffix(".tmp")  # atomic write: tmp then replace
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        tmp.replace(state_path)
        m = round_metrics(recs) | {"tok_per_s": (llm.tokens_out - tok0) / max(time.perf_counter() - t0, 1e-9),
                                   "round_seconds": time.perf_counter() - t0}
        dash.log(m, step=t)  # live dashboard
        log.info("%s round %d: %s", cfg.run_id(), t, json.dumps({k: round(v, 3) for k, v in m.items()}))
    dash.finish()
    return run_dir
