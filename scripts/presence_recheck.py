"""Robustness check of the presence_penalty rule (prereg §8.1) under a second syntax-error definition.

Usage: uv run python scripts/presence_recheck.py <capability_..._llm_calls.jsonl>  -> results/engineering/presence_recheck.json
Local context: the rule's implementation (`pilot.presence_penalty_rule`) counts a first answer as a syntax error when the
extracted code does not parse; an answer without a code block falls back to the whole (prose) answer and counts. This
script recomputes, from the logged first attempts, (a) truncation at the token cap, (b) answers with a code block,
(c) syntax errors among code blocks only, (d) flags, and keeps a few failing blocks as examples. The preregistered
decision is not changed by this file; it documents whether it depends on the definition.
Global context: cited by reports/experiments/01_capability.md.
"""

from __future__ import annotations  # forward references

import ast  # parse check
import collections  # grouping
import json  # IO
import sys  # argv
from pathlib import Path  # paths

from swarm_epi.grader import FENCE  # the same code-block regex the grader uses
from swarm_epi.prompts import FLAG_TOKEN  # abort string

OUT = Path(__file__).resolve().parents[1] / "results" / "engineering" / "presence_recheck.json"


def parses(code: str) -> bool:
    """True if `code` is valid Python."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def main(path: Path) -> dict:
    groups = collections.defaultdict(list)  # "presence1.5" / "presence0.0" -> first-attempt call records
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        run = r["tags"].get("run", "")
        if run.startswith("presence") and r["tags"].get("attempt") == 0:
            groups[run.split(":")[0].removeprefix("presence")].append(r)
    out = {}
    for pp, rs in sorted(groups.items()):
        blocks = [FENCE.findall(r["output"] or "") for r in rs]  # code blocks per answer
        last = [b[-1] for b in blocks if b]  # the block the grader would extract
        bad = [c for c in last if not parses(c)]
        out[pp] = {"n": len(rs), "truncated_at_cap": sum(r["finish_reason"] == "length" for r in rs),
                   "with_code_block": len(last), "syntax_errors_among_code_blocks": len(bad),
                   "flags": sum(FLAG_TOKEN in (r["output"] or "").lower() for r in rs),
                   "failing_block_examples": [c[:160] for c in bad[:3]]}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return out


if __name__ == "__main__":
    main(Path(sys.argv[1]))
