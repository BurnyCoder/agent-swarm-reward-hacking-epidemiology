"""Engineering diagnostic: natural length of solve answers, to choose the code-answer token cap (deviation #9).

Usage: uv run python scripts/length_probe.py  -> results/engineering/length_probe.json (+ full call log in RUNS_DIR/logs)
Local context: 40 random filtered tasks (impossible versions), prompts D (strictest) and A (loosest), empty notes and
board, one solve call each with a 2,048-token cap. Reports length percentiles, the share of answers that end below
candidate caps, and how many run into the 2,048 cap. Seeds are fixed; vLLM is not batch-invariant, so a rerun can
differ slightly (docs/serving.md §7).
Global context: not part of any confirmatory analysis; it only justifies `SwarmConfig.max_code_tokens`.
"""

from __future__ import annotations  # forward references

import asyncio  # concurrent calls
import json  # output
import os  # env
from pathlib import Path  # paths

import numpy as np  # sampling + percentiles

from swarm_epi import prompts as P  # instructions and context block
from swarm_epi.config import LLMConfig  # server settings
from swarm_epi.llm import LLM, setup_logging  # client with full call logging
from swarm_epi.tasks import format_task_input, load_tasks  # ImpossibleBench task input

OUT = Path(__file__).resolve().parents[1] / "results" / "engineering" / "length_probe.json"
CAP, N_TASKS, VARIANTS = 2048, 40, ("D", "A")


async def main() -> None:
    jsonl = setup_logging(Path(os.environ.get("RUNS_DIR", "runs")) / "logs", "lengthprobe")  # timestamped logs
    llm = LLM(LLMConfig(), jsonl_path=jsonl, echo=False)  # every call stored in full in the JSONL
    tasks = load_tasks()
    pick = [tasks[i] for i in np.random.default_rng(1).choice(len(tasks), N_TASKS, replace=False)]  # fixed subset

    async def one(i: int, t, v: str) -> dict:
        msgs = [{"role": "system", "content": P.system_prompt(i, 32) + P.context_block("", [])},  # swarm layout
                {"role": "user", "content": format_task_input(t, P.instruction(v, True))}]
        r = await llm.chat(msgs, CAP, {"phase": "lengthprobe", "variant": v, "task": t.task_id}, seed=i)
        return {"variant": v, "tokens": r.completion_tokens, "hit_cap": r.finish_reason == "length",
                "fence": "```" in r.text, "flag": P.FLAG_TOKEN in r.text.lower()}

    rows = await asyncio.gather(*(one(i, t, v) for i, t in enumerate(pick) for v in VARIANTS))
    out = {}
    for v in VARIANTS:
        rs = [r for r in rows if r["variant"] == v]
        ct = np.array([r["tokens"] for r in rs])
        out[v] = {"n": len(rs), "p50": float(np.percentile(ct, 50)), "p75": float(np.percentile(ct, 75)),
                  "share_le_384": float((ct <= 384).mean()), "share_le_768": float((ct <= 768).mean()),
                  "share_le_1024": float((ct <= 1024).mean()), "share_hit_2048": float(np.mean([r["hit_cap"] for r in rs])),
                  "share_code_fence": float(np.mean([r["fence"] for r in rs])),
                  "share_flag": float(np.mean([r["flag"] for r in rs]))}
    out["_meta"] = {"cap": CAP, "n_tasks": N_TASKS, "task_rng_seed": 1, "calls_log": str(jsonl)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    asyncio.run(main())
