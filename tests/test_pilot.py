"""Pilot helpers: the resumable checkpoint map used by the capability pass and pool generation."""

import asyncio  # async runner
import json  # checkpoint lines

from swarm_epi.pilot import _resumable_map  # unit under test


def test_resumable_map_skips_done_items_and_keeps_order(tmp_path):
    ckpt = tmp_path / "x.partial.jsonl"
    ckpt.write_text(json.dumps({"key": "b", "value": 20}) + "\n", encoding="utf-8")  # "b" finished before a crash
    calls = []

    async def fn(key, item):
        calls.append(key)  # record which items actually ran
        return item * 10

    out = asyncio.run(_resumable_map({"a": 1, "b": 2, "c": 3}, fn, ckpt))
    assert out == {"a": 10, "b": 20, "c": 30} and list(out) == ["a", "b", "c"]  # input order, old value reused
    assert sorted(calls) == ["a", "c"]  # "b" was not recomputed
    assert len(ckpt.read_text(encoding="utf-8").splitlines()) == 3  # new results appended
    assert asyncio.run(_resumable_map({"a": 1, "b": 2, "c": 3}, fn, ckpt)) == out and len(calls) == 2  # all cached


def test_extend_hack_pool_appends_new_candidates_and_refinalizes(tmp_path, monkeypatch):
    """Extending the pro-hack pool keeps the frozen candidates, appends new ones under fresh ids (no collisions), judges
    only the new ones and re-applies the pool rules, so the matched pool can grow past the preregistered 100."""
    import asyncio
    import json

    from swarm_epi import pilot

    old = [{"pool_id": f"poolhack_{i:04d}", "text": "Hard-code the expected output, it always works.", "words": 8,
            "p_pro": 0.95, "p_anti": 0.0, "p_neutral": 0.05, "label": "pro", "hack_attempt": True} for i in range(3)]
    tips = [{"pool_id": f"pooltip_{i:04d}", "text": "Name variables clearly so readers follow the logic easily.",
             "words": 9, "p_pro": 0.0, "p_anti": 0.0, "p_neutral": 0.99, "label": "neutral"} for i in range(10)]
    path = tmp_path / "pools.json"
    path.write_text(json.dumps({"_all_hack": old, "_all_placebo": tips, "placebo_source": "tips"}))
    seen = {}

    async def fake_generate(llm, sandbox, tasks, notes, n, label, seed, ckpt):
        seen["label"], seen["seed"] = label, seed
        return [{"pool_id": f"{label}_{i:04d}", "text": "Special-case the failing input and move on.", "words": 7,
                 "hack_attempt": True} for i in range(n)]

    async def fake_judge(llm, texts):
        seen["judged"] = sorted(texts)
        return {k: {"p_pro": 0.9, "p_anti": 0.0, "p_neutral": 0.1, "label": "pro"} for k in texts}

    monkeypatch.setattr(pilot, "generate_posts", fake_generate)
    monkeypatch.setattr(pilot, "judge_many", fake_judge)
    out = asyncio.run(pilot.extend_hack_pool(None, None, [], path, n=4))
    ids = [p["pool_id"] for p in out["_all_hack"]]
    assert len(ids) == 7 and len(set(ids)) == 7  # 3 frozen + 4 new, all distinct
    assert seen["judged"] == sorted(i for i in ids if i.startswith(seen["label"])) and seen["label"] != "poolhack"
    assert len(out["hack"]) == 7  # every valid candidate found a length-matched tip
    assert json.loads(path.read_text())["_all_hack"][:3] == old  # frozen candidates untouched
