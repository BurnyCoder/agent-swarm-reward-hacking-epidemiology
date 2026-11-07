"""Tests for board sampling: no self-reads, previous round only, uniform exposure, common random numbers."""

import numpy as np  # statistics

from swarm_epi.board import Board, Post, rng_for  # units under test


def make_board(n_agents=10, n_seeds=2, round_t=0):
    """Board with one post per agent and seed slot in `round_t`."""
    b = Board()
    for i in range(n_seeds):
        b.add(Post(f"{round_t}:s{i}", round_t, f"s{i}", "seed text", True, f"pool{i}"))
    for i in range(n_agents):
        b.add(Post(f"{round_t}:a{i}", round_t, f"a{i}", f"post {i}", False))
    return b


def test_reads_only_previous_round_and_never_own_post():
    b = make_board()
    b.add(Post("1:a0", 1, "a0", "later", False))  # round-1 post must not be readable in round 1
    posts = b.sample(1, "a3", 6, np.random.default_rng(0))
    assert len(posts) == 6 and all(p.round == 0 and p.author != "a3" for p in posts)
    assert len({p.post_id for p in posts}) == 6  # without replacement


def test_warmup_round_has_no_posts():
    assert Board().sample(0, "a0", 6, np.random.default_rng(0)) == []


def test_exposure_is_uniform():
    # Each of the 11 readable posts should be read with probability K/11 (uniform sampling without replacement).
    b = make_board()
    counts = {}
    for s in range(20000):
        for p in b.sample(1, "a0", 6, np.random.default_rng(s)):
            counts[p.author] = counts.get(p.author, 0) + 1
    freq = np.array(list(counts.values())) / 20000
    assert np.allclose(freq, 6 / 11, atol=0.015)


def test_common_random_numbers_identical_across_conditions():
    # Same replicate/round/slot/purpose -> identical draws, different purpose -> different draws.
    a = rng_for(1, 3, 2, 5, 0).integers(0, 10**9, 5)
    b = rng_for(1, 3, 2, 5, 0).integers(0, 10**9, 5)
    c = rng_for(1, 3, 2, 5, 1).integers(0, 10**9, 5)
    assert (a == b).all() and not (a == c).all()


def test_task_schedule_unique_and_reuse_rule():
    from collections import Counter

    from swarm_epi.tasks import Task, schedule_tasks
    mk = lambda n: [Task(f"t/{i}", "", "f", "", "", "", "", "t") for i in range(n)]
    s = schedule_tasks(mk(400), 32, 11, seed=3)
    assert len({t.task_id for row in s for t in row}) == 352  # unique within a run
    assert schedule_tasks(mk(400), 32, 11, seed=3) == s  # same replicate seed -> same schedule (CRN)
    s2 = schedule_tasks(mk(200), 32, 11, seed=3)  # fallback: 200 tasks for 352 slots
    uses = {}
    for r, row in enumerate(s2):
        for a, t in enumerate(row):
            uses.setdefault(t.task_id, []).append((r, a))
    assert max(Counter({k: len(v) for k, v in uses.items()}).values()) <= 2
    for v in uses.values():
        if len(v) == 2:
            (r1, a1), (r2, a2) = v
            assert abs(r2 - r1) >= 5 and a1 != a2
