"""Tests for dose-response trial construction (prereg §2.3)."""

from collections import Counter

from swarm_epi.dose_response import make_trials

POOLS = {
    "pro": [{"pool_id": f"r1:{i}", "text": f"hack {i}", "author": f"r1:a{i % 5}"} for i in range(40)],
    "anti": [{"pool_id": f"an{i}", "text": f"flag it {i}"} for i in range(10)],
    "neutral": [{"pool_id": f"ne{i}", "text": f"tip {i}"} for i in range(30)],
}
CELLS = [(k, 0, "distinct") for k in (0, 1, 2, 3, 4, 6)] + [(k, 2, "distinct") for k in (0, 1, 2, 3, 4)] + \
        [(k, 0, "same") for k in (2, 4)] + [(k, 0, "offtopic") for k in (2, 4, 6)]


def test_cells_counts_kinds_and_balance():
    trials = make_trials(CELLS, 10, POOLS, [(1, "n1"), (5, "n5")], n_tasks=50, K=6, seed=0)
    assert len(trials) == len(CELLS) * 10
    for t in trials:
        kinds = Counter(p[2] for p in t.posts)
        assert len(t.posts) == 6 and kinds["anti"] == t.j
        assert kinds["pro" if t.variant != "offtopic" else "offtopic"] == t.k or t.k == 0
        if t.variant == "same" and t.k:
            ids = [p[3] for p in t.posts if p[2] == "pro"]
            authors = {POOLS["pro"][int(i.split(":")[1])]["author"] for i in ids}
            assert len(set(ids)) == t.k and len(authors) == 1  # distinct posts, one author
    counts = Counter(t.task_idx for t in trials)
    assert max(counts.values()) - min(counts.values()) <= 1  # tasks balanced (without replacement, cycling)
