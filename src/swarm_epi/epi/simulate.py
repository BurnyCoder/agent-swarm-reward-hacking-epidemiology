"""Matched agent-based chain-binomial simulator of the board epidemic (null models, power analysis, H5 predictions).

Local context: mirrors the swarm mechanics exactly — N agents, m seed slots (pro-hack posts while active), each agent
reads K of the previous round's other posts uniformly without replacement; an infected agent's post is pro-hack with
probability pi; a susceptible agent becomes infected with probability infect(k) given k pro-hack posts read (the
dose-response kernel, background rate included as infect(0)); an infected agent recovers with probability `recover`
per round. This is the Reed-Frost chain binomial (Britton 2018, https://arxiv.org/abs/1801.09594, §2.3) generalized
from "contacts with infectives" to "infected posts read", which none of EoN/NDlib/epydemic implement directly.
Global context: `analysis.py` (H5 envelopes and scores) and the pilot power/identifiability study.
"""

from __future__ import annotations  # forward references

from collections.abc import Callable  # kernel type

import numpy as np  # numerics


def simulate(N: int, K: int, T: int, n_seeds: int, infect: Callable[[np.ndarray], np.ndarray], recover: float,
             pi: float, rng: np.random.Generator, seed_last_round: int | None = None,
             cumulative: bool = False) -> np.ndarray:
    """One run; returns infected counts (or, if `cumulative`, ever-infected counts) among N agents for rounds 0..T."""
    infected = rng.random(N) < infect(np.zeros(N))  # round 0 (empty board): background infections only
    ever = infected.copy()  # agents infected at least once
    pro = infected & (rng.random(N) < pi)  # which agents' round-0 posts are pro-hack
    seeds_active = n_seeds > 0 and (seed_last_round is None or seed_last_round >= 0)  # seeds post in round 0
    out = [int(ever.sum() if cumulative else infected.sum())]  # trajectory
    for t in range(1, T + 1):
        posts_pro = np.concatenate([pro, np.ones(n_seeds if seeds_active else 0, bool)])  # agents then seed slots
        n_posts = posts_pro.size  # readable posts this round (minus own)
        k = np.empty(N, int)  # pro-hack posts read by each agent
        for i in range(N):  # sample K of the other posts uniformly without replacement
            others = np.delete(np.arange(n_posts), i)  # exclude own post
            idx = rng.choice(others, size=min(K, others.size), replace=False)
            k[i] = posts_pro[idx].sum()
        new_inf = (~infected) & (rng.random(N) < infect(k))  # infections among susceptibles
        stay = infected & (rng.random(N) >= recover)  # infected who do not recover
        infected = new_inf | stay  # SIS update
        ever |= infected  # cumulative incidence
        pro = infected & (rng.random(N) < pi)  # posts written this round
        seeds_active = n_seeds > 0 and (seed_last_round is None or t <= seed_last_round)  # seed posts this round
        out.append(int(ever.sum() if cumulative else infected.sum()))
    return np.array(out)


def simulate_many(reps: int, rng: np.random.Generator, **kw) -> np.ndarray:
    """`reps` independent runs stacked as an array (reps x T+1)."""
    return np.stack([simulate(rng=rng, **kw) for _ in range(reps)])
