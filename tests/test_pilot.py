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
