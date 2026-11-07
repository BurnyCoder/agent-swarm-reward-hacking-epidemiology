"""Shared message board with uniform K-of-last-round sampling and full exposure logging.

Local context: each round every author (N agents + active seed slots) writes one post; in round t each agent reads K
posts drawn uniformly WITHOUT replacement from the round t-1 posts of others. This is the random-mixing contact
process assumed by the Reed-Frost chain binomial (Britton 2018, https://arxiv.org/abs/1801.09594) and by Hu et al.'s
binomial-mixture transmission map T(x)=sum_j Bin(j;k,x) theta_j (arXiv 2610.12822), so the fitted epidemic models
match the mechanism exactly (user decision: minimal custom board instead of OASIS ranking feeds).
Global context: because exposure is randomized by `rng`, the number of pro-hack posts an agent sees is an
exogenous treatment — the basis of the causal per-post hazard estimate (H2) in `epi/hazard.py`.
"""

from __future__ import annotations  # forward references

from dataclasses import asdict, dataclass  # post record

import numpy as np  # sampling


@dataclass(frozen=True)
class Post:
    """One board post."""

    post_id: str  # "<round>:<author>" unique within a run
    round: int  # round in which it was written
    author: str  # "a<idx>" for agents, "s<idx>" for seed slots
    text: str  # message body shown to readers
    is_seed: bool  # True for seed-slot posts (drawn from a frozen pool)
    pool_id: str = ""  # stimulus-pool item id for seed posts (provenance)

    def to_dict(self) -> dict:
        """JSON-serializable view."""
        return asdict(self)


class Board:
    """Append-only, round-indexed message board."""

    def __init__(self) -> None:
        self.rounds: dict[int, list[Post]] = {}  # round -> posts written that round (deterministic order)

    def add(self, post: Post) -> None:
        """Append a post to its round."""
        self.rounds.setdefault(post.round, []).append(post)

    def candidates(self, round_t: int, reader: str) -> list[Post]:
        """Posts readable in round `round_t`: all round t-1 posts except the reader's own, in a fixed order."""
        prev = self.rounds.get(round_t - 1, [])  # previous-round posts
        ordered = sorted(prev, key=lambda p: (not p.is_seed, p.author))  # seeds first, then authors: stable order
        return [p for p in ordered if p.author != reader]  # exclude own post

    def sample(self, round_t: int, reader: str, k: int, rng: np.random.Generator) -> list[Post]:
        """Uniform sample of min(k, available) posts without replacement; order = presentation order."""
        cand = self.candidates(round_t, reader)  # readable posts
        if not cand:  # warm-up round 0
            return []
        idx = rng.choice(len(cand), size=min(k, len(cand)), replace=False)  # random positions => random order too
        return [cand[i] for i in idx]  # presentation order is the sampled order (position randomized)


def rng_for(base_seed: int, replicate: int, round_t: int, slot: int, purpose: int) -> np.random.Generator:
    """Independent, reproducible RNG stream per (replicate, round, slot, purpose) — common random numbers.

    numpy's SeedSequence hashes the integer list into a well-mixed seed, so streams for different purposes
    (board sampling, seed-post choice, LLM seeds) are statistically independent yet identical across conditions.
    """
    return np.random.default_rng([base_seed, replicate, round_t, slot, purpose])  # SeedSequence entropy list
