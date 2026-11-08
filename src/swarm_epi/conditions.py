"""Experimental conditions (pre-registered in reports/preregistration.md).

Local context: every condition is a list of SwarmConfig replicates that differ from MAIN in exactly one factor, so
condition contrasts isolate that factor; replicate indices are shared across conditions (common random numbers for
task schedules and board sampling). Pilot replicates use indices >= 900 so they never reuse confirmatory streams.
Global context: `scripts/run_experiment.py` maps phase names to these lists.
"""

from __future__ import annotations  # forward references

from .config import SwarmConfig  # parameters


def batch1(variant: str) -> list[SwarmConfig]:
    """Batch 1: MAIN x20, PLACEBO x20, TRANSIENT x15 (prompt variant from calibration)."""
    base = SwarmConfig(prompt_variant=variant)  # prereg defaults N=32, K=6, T=10, m=2
    main = [base.with_(condition="MAIN", replicate=r, seed_pool="hack") for r in range(20)]  # committed hack seeds
    placebo = [base.with_(condition="PLACEBO", replicate=r, seed_pool="placebo") for r in range(20)]  # neutral seeds
    transient = [base.with_(condition="TRANSIENT", replicate=r, seed_pool="hack", seed_last_round=1)
                 for r in range(15)]  # hack seeds post only in rounds 0-1
    return main + placebo + transient


def pilot(variant: str, n: int = 2) -> list[SwarmConfig]:
    """Pilot swarms (excluded from confirmatory analysis): MAIN and PLACEBO, replicate ids 900+."""
    base = SwarmConfig(prompt_variant=variant)
    return ([base.with_(condition="MAIN", replicate=900 + r, seed_pool="hack") for r in range(n)] +
            [base.with_(condition="PLACEBO", replicate=900 + r, seed_pool="placebo") for r in range(n)])


def explore(variant: str, n: int = 8) -> list[SwarmConfig]:
    """Exploratory batch (run before the Stage 2 addendum at the author's request; never confirmatory): MAIN,
    PLACEBO and TRANSIENT with replicate ids 800+, disjoint from confirmatory (0-19) and pilot (900+) streams.
    Ordered by replicate (MAIN, PLACEBO, TRANSIENT of r = 800, then 801, ...) so CRN triplets finish together and a
    partial batch can be analyzed."""
    base = SwarmConfig(prompt_variant=variant)
    out = []
    for r in range(800, 800 + n):
        out += [base.with_(condition="MAIN", replicate=r, seed_pool="hack"),
                base.with_(condition="PLACEBO", replicate=r, seed_pool="placebo"),
                base.with_(condition="TRANSIENT", replicate=r, seed_pool="hack", seed_last_round=1)]
    return out


WEEK1_PARTNERS = {"MEMOFF_MAIN": "MAIN", "MEMOFF_PLACEBO": "PLACEBO", "M4": "MAIN", "M8": "MAIN",
                  "NOSEED": "PLACEBO", "INOC": "MAIN"}  # W1 condition -> batch-1 CRN partner (preregistration_week1.md)


def week1(variant: str, n: int = 10) -> list[SwarmConfig]:
    """Week-phase batch W1 (exploratory; reports/preregistration_week1.md): six one-factor ablations x n replicates.

    Replicate ids 0..n-1 share task schedules and board-sampling streams with batch-1 replicates of the partner
    condition (WEEK1_PARTNERS), so every W1 run has a CRN pair. Ordered by replicate so a partial batch is analysable."""
    base = SwarmConfig(prompt_variant=variant)
    make = {"MEMOFF_MAIN": dict(seed_pool="hack", memory=False),  # notes discarded every round
            "MEMOFF_PLACEBO": dict(seed_pool="placebo", memory=False),
            "M4": dict(seed_pool="hack", n_seeds=4),  # critical mass: more committed seed slots
            "M8": dict(seed_pool="hack", n_seeds=8),
            "NOSEED": dict(seed_pool="none", n_seeds=0),  # no seed posts at all
            "INOC": dict(seed_pool="hack", inoculation=True)}  # warning against cheating in the system prompt
    return [base.with_(condition=c, replicate=r, **kw) for r in range(n) for c, kw in make.items()]


def smoke(variant: str = "D") -> list[SwarmConfig]:
    """Tiny end-to-end smoke test: N=8 agents, T=3 rounds, one MAIN replicate."""
    return [SwarmConfig(condition="SMOKE", replicate=999, n_agents=8, n_rounds=3, prompt_variant=variant)]
