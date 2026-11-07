"""Per-phase statistics of logged LLM calls: finish reasons, token lengths, code-fence rate, common openings.

Usage: uv run python scripts/llm_call_stats.py <run_logs/..._llm_calls.jsonl> [--json out.json]
Local context: reads the JSONL written by `swarm_epi.llm.LLM._record` (one object per call with `tags.phase`,
`finish_reason`, `prompt_tokens`, `completion_tokens`, `output`). Used to check truncation (finish_reason "length")
and answer format in every phase; the smoke-test report (reports/experiments/00_smoke_test.md) cites its output.
Global context: diagnostic only; no experimental number in the paper comes from here.
"""

from __future__ import annotations  # forward references

import argparse  # CLI
import collections  # counters
import json  # JSONL
from pathlib import Path  # paths

import numpy as np  # percentiles


def stats(path: Path) -> dict:
    """Group calls by tags.phase and summarize each group."""
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]  # all calls
    groups = collections.defaultdict(list)  # phase -> calls
    for r in rows:
        groups[r["tags"].get("phase", "?")].append(r)
    out = {}
    for phase, rs in groups.items():
        ct = np.array([r["completion_tokens"] or 0 for r in rs])  # generated tokens per call
        pt = np.array([r["prompt_tokens"] or 0 for r in rs])  # prompt tokens per call
        out[phase] = {
            "n": len(rs),
            "finish_reason": dict(collections.Counter(r["finish_reason"] for r in rs)),  # "length" = hit the cap
            "completion_tokens_p50_p90_max": [float(np.percentile(ct, 50)), float(np.percentile(ct, 90)), int(ct.max())],
            "prompt_tokens_p50_max": [float(np.percentile(pt, 50)), int(pt.max())],
            "has_code_fence": int(sum("```" in (r["output"] or "") for r in rs)),  # answers containing a code block
            "opens_with_notes_header": int(sum((r["output"] or "").lstrip().lower().startswith(("[your private notes",
                                                "[private notes")) for r in rs)),  # echo of the context-block header
            "top_openings": collections.Counter((r["output"] or "")[:24] for r in rs).most_common(3),  # format check
        }
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jsonl", type=Path)
    ap.add_argument("--json", type=Path, help="also write the summary to this file")
    a = ap.parse_args()
    s = stats(a.jsonl)
    print(json.dumps(s, indent=1, ensure_ascii=False))
    if a.json:
        a.json.write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")
