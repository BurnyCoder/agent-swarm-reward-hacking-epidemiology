# Preregistration addendum: week-phase batch W1 (exploratory ablations)

- **Author:** Libor "Burny" Burian · **Date:** 2026-11-08 · **Status:** written and pushed before any W1 data exist.
- **Parent documents:** [`preregistration.md`](preregistration.md) §2.4 lists these conditions as exploratory
  week-phase conditions without fixing their sample size or analysis; [`preregistration_stage2.md`](preregistration_stage2.md)
  fixes every other constant (prompt variant, pools, task filter). This addendum fixes the W1 design and analysis.
- **Status of the results:** exploratory (preregistration §10). The confirmatory hypotheses H1–H5 are already decided
  ([`experiments/02_confirmatory_batch1.md`](experiments/02_confirmatory_batch1.md)); W1 is chosen to explain them.

## 1. Why these conditions

Batch 1 found a transmissible but subcritical belief: agent-written pro-hack posts raise the onset hazard, the
single-agent dose-response is reinforcing (Weibull γ > 1), yet R0 ≪ 1, and flagging rises to about nine in ten agents
in every condition. W1 asks four questions that the batch-1 design cannot answer:

| Question | Condition (label) | Changed factor (everything else as batch-1 MAIN or PLACEBO) | CRN partner in batch 1 |
|---|---|---|---|
| Q1. Is the rise of flagging (and the fall of hacking) carried by private notes or by the board? | `MEMOFF_MAIN`, `MEMOFF_PLACEBO` | `memory=False`: notes are discarded after every round (serial-passage chain, prereg §2.4) | MAIN, PLACEBO |
| Q2. Does denser pro-hack exposure push spread toward criticality (critical mass, [Ashery et al. 2025](https://doi.org/10.1126/sciadv.adu9368))? | `M4`, `M8` | `n_seeds` = 4 or 8 committed pro-hack seed slots instead of 2 | MAIN |
| Q3. Do the placebo seed posts themselves change behaviour? | `NOSEED` | `n_seeds=0`: no seed posts at all | PLACEBO |
| Q4. Does a one-sentence warning against cheating in the system prompt block transmission? | `INOC` | `inoculation=True` (warning text in `prompts.system_prompt`), pro-hack seeds as in MAIN | MAIN |

Expected seed exposure per agent-round under uniform K-of-pool reading: K·m/(N − 1 + m) = 6·2/33 ≈ 0.36 (MAIN),
6·4/35 ≈ 0.69 (M4), 6·8/39 ≈ 1.23 (M8). The warning in Q4 is a pre-bunking message in the spirit of the inoculation
condition of [Papadopoulos et al. 2026](https://arxiv.org/abs/2608.10218) (Fig. 8) and of ImpossibleBench's finding
that stricter instructions reduce cheating ([Zhong et al. 2025](https://arxiv.org/abs/2510.20270), Fig. 6). It is not
the "inoculation prompting" of [MacDiarmid et al. 2025](https://arxiv.org/abs/2511.18397), which frames hacking as
acceptable during training to stop misaligned generalization; preregistration §2.4 cites both, and this addendum
records that the W1 intervention is the warning, not the permission framing.

Not in W1 (later batches, same design rules): yoked NO-SECONDARY (needs code for yoking), K ∈ {2, 12}, N ∈ {16, 64},
50%-solvable tasks, whistleblower seeds, grader feedback off, temperature and seed sweeps, other models.

## 2. Design

- **Runs:** 10 replicates per condition, replicate ids 0–9, so each W1 run shares its task schedule and board-sampling
  random streams with batch-1 replicate r of its partner condition (common random numbers). 60 runs, 4 in parallel,
  ordered by replicate so that a partial batch is analysable. N = 32, K = 6, T = 10 (+ warm-up round 0), prompt
  variant and pools as frozen at Stage 2. Raw data: `$RUNS_DIR/week1/`.
- **Why 10 replicates:** compute (about 9 hours for 60 runs at the batch-1 throughput). With exact sign-flip tests
  the smallest attainable two-sided p for 10 pairs is 2/2¹⁰ ≈ 0.002, below the Holm threshold 0.05/6.
- **Exclusions:** none on outcomes; only completed runs enter the analysis (as prereg §9.8).

## 3. Outcomes and analysis (fixed now)

- **Primary metric:** run-level mean non-seed hack-attempt prevalence over rounds 1–10 (the H1 metric), compared with
  the batch-1 CRN partner by the mean paired difference, a 95% pair-bootstrap CI and the exact two-sided sign-flip test
  (`epi.stats.compare_paired`). Holm correction across the six primary contrasts (family-wise α = 0.05).
- **Secondary metric:** run-level mean flag rate over rounds 1–10, same comparison, Holm across its six contrasts.
- **Q2 trend check:** within `M8`, the paired difference late − early (mean prevalence rounds 8–10 minus rounds 1–3,
  per run), with the same test. A positive, significant trend would contradict "subcritical"; a CI including or below
  zero is consistent with it.
- **Q3 equivalence:** for `NOSEED` − PLACEBO also the paired TOST against ±10 pp (as H1).
- **Descriptive:** prevalence and flag-rate curves by round for each condition and its partner (95% bootstrap bands).
- **Predictions (written before data; none is confirmatory):**
  - Q1: no directional prediction. If notes carry the flagging norm, memory-off lowers the flag rate; if the board
    carries it, the flag rate stays close to its partner's.
  - Q2: hack prevalence `M8` > `M4` > MAIN (more seed exposure, reinforcing dose-response), with no positive late −
    early trend in `M8` (subcritical secondary spread).
  - Q3: `NOSEED` ≈ PLACEBO (placebo posts are neutral coding tips).
  - Q4: `INOC` < MAIN.
- **Reporting:** one report `reports/experiments/03_week1_ablations.md` rendered from `results/week1/summary.json` by
  `scripts/make_reports.py`; negative and null results are reported the same way as positive ones.
