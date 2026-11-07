"""Matched agent-based chain-binomial simulator of the board epidemic (power analysis, H5 forecasts), vectorized.

Local context: mirrors the swarm mechanics — N agents and m seed slots (pro-hack posts while active); each round every
agent reads K of the previous round's OTHER posts uniformly without replacement (random keys + argpartition, i.e. a
uniform K-subset); a susceptible agent starts hacking with probability infect(k) given k pro-hack posts read (the
dose-response kernel, background included as infect(0)); a hacking agent stops with probability `recover` per round;
an agent's post is pro-hack with probability pi_h if it is hacking and pi_n otherwise. This is the Reed-Frost chain
binomial (Britton 2018, https://arxiv.org/abs/1801.09594, §2.3) with exposure to K of the board's posts instead of
contact with every infective (our adaptation; EoN / NDlib / epydemic have no K-of-N board process).
Global context: `epi.power` (pre-registered power/identifiability) and `analysis.h5` (out-of-sample forecasts).
"""

from __future__ import annotations  # forward references

from collections.abc import Callable  # kernel type

import numpy as np  # numerics


def simulate_many(reps: int, rng: np.random.Generator, N: int, K: int, T: int, n_seeds: int,
                  infect: Callable[[np.ndarray], np.ndarray], recover: float, pi_h: float, pi_n: float = 0.0,
                  seed_last_round: int | None = None, cumulative: bool = False) -> np.ndarray:
    """`reps` independent runs; returns hacking counts (or ever-hacked counts if `cumulative`), shape reps x (T+1)."""
    hack = rng.random((reps, N)) < infect(np.zeros((reps, N)))  # round 0 (empty board): background only
    ever = hack.copy()  # cumulative incidence
    pro = np.where(hack, rng.random((reps, N)) < pi_h, rng.random((reps, N)) < pi_n)  # round-0 post stance
    seeds = n_seeds if n_seeds > 0 and (seed_last_round is None or seed_last_round >= 0) else 0  # active slots
    out = [(ever if cumulative else hack).sum(1)]
    agents = np.arange(N)
    for t in range(1, T + 1):
        posts = np.concatenate([pro, np.ones((reps, seeds), bool)], axis=1)  # agents' posts then seed posts
        P = posts.shape[1]
        keys = rng.random((reps, N, P))  # random sort keys per reader
        keys[:, agents, agents] = np.inf  # never read own post (agent i wrote post i)
        idx = np.argpartition(keys, K, axis=2)[:, :, :K]  # uniform K-subset of the other posts
        k = np.take_along_axis(np.broadcast_to(posts[:, None, :], (reps, N, P)), idx, axis=2).sum(2)  # pro read
        start = ~hack & (rng.random((reps, N)) < infect(k))  # new hackers among susceptibles
        stay = hack & (rng.random((reps, N)) >= recover)  # hackers who continue
        hack = start | stay  # SIS update
        ever |= hack
        pro = np.where(hack, rng.random((reps, N)) < pi_h, rng.random((reps, N)) < pi_n)  # posts of round t
        seeds = n_seeds if n_seeds > 0 and (seed_last_round is None or t <= seed_last_round) else 0
        out.append((ever if cumulative else hack).sum(1))
    return np.stack(out, axis=1)


def simulate(rng: np.random.Generator, **kw) -> np.ndarray:
    """Single run (convenience wrapper)."""
    return simulate_many(1, rng, **kw)[0]
