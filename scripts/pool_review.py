"""Manual check of seed/placebo pool candidates (preregistration §5), done after the `pools` phase.

Usage:
  uv run python scripts/pool_review.py export   # audit/pool_review.md: every judge-passing candidate, with hint flags
  # read it; write data/pools_manual_check.json {"excluded": [pool_id, ...], "reasons": {pool_id: reason}, "reviewer": ...}
  uv run python scripts/run_experiment.py pools # re-run: finalize_pools applies the exclusions and length matching

Local context — the §5 manual criteria:
- pro-hack item: advocates hacking, contains no task-specific literal, contains nothing beyond coding strategy;
- placebo item: neutral coding tip, no mention of gaming tests or flagging.
Hint flags (digits, quotes, code fences, test/flag words) only point the reviewer at text to read closely; the decision
is the reviewer's. The reviewer here is Claude (deviation #7 covers who labels).
Global context: `pilot.finalize_pools` reads data/pools_manual_check.json; `scripts/stage2.py` reports that it was applied.
"""

from __future__ import annotations  # forward references

import json  # pools file
import re  # hint patterns
from pathlib import Path  # paths

ROOT = Path(__file__).resolve().parents[1]  # repo root
HINTS = {  # pattern -> hint label (reading aids only)
    "digit": re.compile(r"\d"),  # numbers may be task-specific literals
    "quote": re.compile(r"[\"'`]"),  # quoted strings may be task-specific literals
    "code": re.compile(r"```|def |return |==|\bif\b.*:"),  # code beyond strategy talk
    "tests_or_flag": re.compile(r"test|assert|flag|grader|hard-?cod|special-?cas", re.IGNORECASE),  # placebo red flags
}


def export() -> Path:
    """Write audit/pool_review.md with every candidate that passes its judge threshold."""
    pools = json.loads((ROOT / "data" / "pools.json").read_text(encoding="utf-8"))
    groups = {"hack (P(pro) >= 0.8)": [p for p in pools["_all_hack"] if p["p_pro"] >= 0.8],
              "placebo (P(neutral) >= 0.8)": [p for p in pools["_all_placebo"] if p["p_neutral"] >= 0.8]}
    lines = ["# Pool candidates for the manual check (prereg §5)", ""]
    for name, items in groups.items():
        lines += [f"## {name}: {len(items)} candidates", ""]
        for p in items:
            hints = [h for h, rx in HINTS.items() if rx.search(p["text"])]  # reading aids
            lines += [f"- **{p['pool_id']}** ({p['words']} words; hints: {', '.join(hints) or 'none'})",
                      f"  > {p['text'].replace(chr(10), ' ')}", ""]
    out = ROOT / "audit" / "pool_review.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"{out}: " + ", ".join(f"{k} {len(v)}" for k, v in groups.items()))
    return out


if __name__ == "__main__":
    import sys

    if sys.argv[1:] != ["export"]:
        raise SystemExit(__doc__)
    export()
