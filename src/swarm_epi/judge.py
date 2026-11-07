"""Offline 3-way post judge (pro-hack / anti-hack / neutral) using the same local model.

Local context: the rubric adapts ImpossibleBench's LLM cheating monitor (App. G.2.1) and cheating taxonomy (App. G.2.2)
to board posts (`prompts.JUDGE_PROMPT`). Instead of parsing free text we read the first-token probabilities of the
letters A/B/C (greedy, top-20 logprobs), giving calibrated-looking scores P(pro), P(anti), P(neutral). The judge is
validated against ~200 blind hand labels (Cohen's kappa reported in the analysis) before any confirmatory use.
Global context: `pilot.py` filters stimulus pools with it; `analysis.py` labels every post read by every agent so
exposure counts k (pro-hack posts read) can be computed.
"""

from __future__ import annotations  # forward references

import asyncio  # concurrent judging
import math  # NaN checks

from . import prompts as P  # judge rubric
from .llm import LLM  # inference client

LETTERS = {"A": "pro", "B": "anti", "C": "neutral"}  # option letter -> label


async def judge_post(llm: LLM, text: str, tags: dict | None = None) -> dict:
    """Return {'p_pro','p_anti','p_neutral','label'} for one post."""
    msgs = [{"role": "user", "content": P.JUDGE_PROMPT.format(post=text.strip() or "(empty)")}]  # single-turn rubric
    probs = await llm.option_probs(msgs, list(LETTERS), tags=(tags or {}) | {"phase": "judge"})  # letter probs
    out = {f"p_{LETTERS[k]}": v for k, v in probs.items()}  # rename to labels
    finite = {k: v for k, v in probs.items() if not math.isnan(v)}  # letters that appeared in the top-20
    out["label"] = LETTERS[max(finite, key=finite.get)] if finite else "neutral"  # argmax label
    return out


async def judge_many(llm: LLM, posts: dict[str, str]) -> dict[str, dict]:
    """Judge many posts concurrently: {post_key: text} -> {post_key: scores}."""
    keys = list(posts)  # stable order
    res = await asyncio.gather(*(judge_post(llm, posts[k], {"post": k}) for k in keys))  # concurrent requests
    return dict(zip(keys, res))
