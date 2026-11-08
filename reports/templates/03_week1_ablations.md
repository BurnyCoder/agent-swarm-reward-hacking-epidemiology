# Experiment 03 — Week-phase batch W1: ablations of memory, seed density, seeding and a warning (exploratory)

- **Author:** Libor "Burny" Burian · **Status:** exploratory. Design and analysis were fixed in
  [`reports/preregistration_week1.md`](../preregistration_week1.md) (commit `692f729`) before any W1 data existed;
  this template was written before the W1 results were looked at.
- **Inputs:** `results/week1/summary.json` and `results/week1/week1_by_round.csv` (from
  `uv run python scripts/analyze.py --batch week1`); raw runs in `$RUNS_DIR/week1/`.
- **Design:** six one-factor ablations of batch 1, each with replicates 0–9 that share task schedules and board
  sampling with batch-1 replicates 0–9 of its partner condition (common random numbers). N = 32, K = 6, rounds 0–10,
  prompt {calibration[chosen]}, pools as frozen at Stage 2.

## Results

Primary metric: run-level mean non-seed hack-attempt prevalence over rounds 1–10; secondary: flag rate over rounds
1–10. Differences are W1 condition minus its batch-1 partner over CRN pairs, with 95% pair-bootstrap CIs; p-values
are exact two-sided sign-flip tests, Holm-adjusted across the six contrasts of each metric.

| Condition | What changes | Partner | Runs | Hack prevalence (W1 vs partner) | Δ hack [95% CI] | Holm p | Δ flag [95% CI] | Holm p |
|---|---|---|---|---|---|---|---|---|
| `MEMOFF_MAIN` | Q1 notes off, pro-hack seeds | {week1_summary[contrasts][MEMOFF_MAIN][ref]} | {week1_summary[n_runs][MEMOFF_MAIN]} | {week1_summary[contrasts][MEMOFF_MAIN][hack][mean_a]:.1%} vs {week1_summary[contrasts][MEMOFF_MAIN][hack][mean_b]:.1%} | {week1_summary[contrasts][MEMOFF_MAIN][hack][diff]:+.1%} [{week1_summary[contrasts][MEMOFF_MAIN][hack][ci_low]:+.1%}, {week1_summary[contrasts][MEMOFF_MAIN][hack][ci_high]:+.1%}] | {week1_summary[holm_hack][MEMOFF_MAIN]:.3f} | {week1_summary[contrasts][MEMOFF_MAIN][flag][diff]:+.1%} [{week1_summary[contrasts][MEMOFF_MAIN][flag][ci_low]:+.1%}, {week1_summary[contrasts][MEMOFF_MAIN][flag][ci_high]:+.1%}] | {week1_summary[holm_flag][MEMOFF_MAIN]:.3f} |
| `MEMOFF_PLACEBO` | Q1 notes off, placebo seeds | {week1_summary[contrasts][MEMOFF_PLACEBO][ref]} | {week1_summary[n_runs][MEMOFF_PLACEBO]} | {week1_summary[contrasts][MEMOFF_PLACEBO][hack][mean_a]:.1%} vs {week1_summary[contrasts][MEMOFF_PLACEBO][hack][mean_b]:.1%} | {week1_summary[contrasts][MEMOFF_PLACEBO][hack][diff]:+.1%} [{week1_summary[contrasts][MEMOFF_PLACEBO][hack][ci_low]:+.1%}, {week1_summary[contrasts][MEMOFF_PLACEBO][hack][ci_high]:+.1%}] | {week1_summary[holm_hack][MEMOFF_PLACEBO]:.3f} | {week1_summary[contrasts][MEMOFF_PLACEBO][flag][diff]:+.1%} [{week1_summary[contrasts][MEMOFF_PLACEBO][flag][ci_low]:+.1%}, {week1_summary[contrasts][MEMOFF_PLACEBO][flag][ci_high]:+.1%}] | {week1_summary[holm_flag][MEMOFF_PLACEBO]:.3f} |
| `M4` | Q2 4 pro-hack seed slots | {week1_summary[contrasts][M4][ref]} | {week1_summary[n_runs][M4]} | {week1_summary[contrasts][M4][hack][mean_a]:.1%} vs {week1_summary[contrasts][M4][hack][mean_b]:.1%} | {week1_summary[contrasts][M4][hack][diff]:+.1%} [{week1_summary[contrasts][M4][hack][ci_low]:+.1%}, {week1_summary[contrasts][M4][hack][ci_high]:+.1%}] | {week1_summary[holm_hack][M4]:.3f} | {week1_summary[contrasts][M4][flag][diff]:+.1%} [{week1_summary[contrasts][M4][flag][ci_low]:+.1%}, {week1_summary[contrasts][M4][flag][ci_high]:+.1%}] | {week1_summary[holm_flag][M4]:.3f} |
| `M8` | Q2 8 pro-hack seed slots | {week1_summary[contrasts][M8][ref]} | {week1_summary[n_runs][M8]} | {week1_summary[contrasts][M8][hack][mean_a]:.1%} vs {week1_summary[contrasts][M8][hack][mean_b]:.1%} | {week1_summary[contrasts][M8][hack][diff]:+.1%} [{week1_summary[contrasts][M8][hack][ci_low]:+.1%}, {week1_summary[contrasts][M8][hack][ci_high]:+.1%}] | {week1_summary[holm_hack][M8]:.3f} | {week1_summary[contrasts][M8][flag][diff]:+.1%} [{week1_summary[contrasts][M8][flag][ci_low]:+.1%}, {week1_summary[contrasts][M8][flag][ci_high]:+.1%}] | {week1_summary[holm_flag][M8]:.3f} |
| `NOSEED` | Q3 no seed posts | {week1_summary[contrasts][NOSEED][ref]} | {week1_summary[n_runs][NOSEED]} | {week1_summary[contrasts][NOSEED][hack][mean_a]:.1%} vs {week1_summary[contrasts][NOSEED][hack][mean_b]:.1%} | {week1_summary[contrasts][NOSEED][hack][diff]:+.1%} [{week1_summary[contrasts][NOSEED][hack][ci_low]:+.1%}, {week1_summary[contrasts][NOSEED][hack][ci_high]:+.1%}] | {week1_summary[holm_hack][NOSEED]:.3f} | {week1_summary[contrasts][NOSEED][flag][diff]:+.1%} [{week1_summary[contrasts][NOSEED][flag][ci_low]:+.1%}, {week1_summary[contrasts][NOSEED][flag][ci_high]:+.1%}] | {week1_summary[holm_flag][NOSEED]:.3f} |
| `INOC` | Q4 warning against cheating | {week1_summary[contrasts][INOC][ref]} | {week1_summary[n_runs][INOC]} | {week1_summary[contrasts][INOC][hack][mean_a]:.1%} vs {week1_summary[contrasts][INOC][hack][mean_b]:.1%} | {week1_summary[contrasts][INOC][hack][diff]:+.1%} [{week1_summary[contrasts][INOC][hack][ci_low]:+.1%}, {week1_summary[contrasts][INOC][hack][ci_high]:+.1%}] | {week1_summary[holm_hack][INOC]:.3f} | {week1_summary[contrasts][INOC][flag][diff]:+.1%} [{week1_summary[contrasts][INOC][flag][ci_low]:+.1%}, {week1_summary[contrasts][INOC][flag][ci_high]:+.1%}] | {week1_summary[holm_flag][INOC]:.3f} |

- **Q2 trend (subcriticality check):** within `M8`, prevalence in rounds 8–10 minus rounds 1–3:
  {week1_summary[m8_late_minus_early][diff]:+.1%} [{week1_summary[m8_late_minus_early][ci_low]:+.1%},
  {week1_summary[m8_late_minus_early][ci_high]:+.1%}] (two-sided sign-flip p =
  {week1_summary[m8_late_minus_early][p_signflip_two_sided]:.3f}). A positive, significant trend would contradict
  "subcritical".
- **Q3 equivalence:** `NOSEED` − PLACEBO within ±10 pp, paired TOST p =
  {week1_summary[contrasts][NOSEED][hack][p_tost_paired]:.1e}.

![W1 hack prevalence](../../results/week1/figures/fig_week1_hack.png)
![W1 flag rate](../../results/week1/figures/fig_week1_flag.png)

## Predictions written before the data (preregistration_week1.md §3)

- Q1 memory off: no directional prediction (notes carry the flagging norm → lower flag rate; board carries it → no
  change).
- Q2: hack prevalence `M8` > `M4` > MAIN, and no positive late − early trend in `M8`.
- Q3: `NOSEED` ≈ PLACEBO.
- Q4: `INOC` < MAIN.

## Limitations

- Exploratory, 10 CRN pairs per contrast; batched LLM inference is not bit-reproducible, so pairs share task
  schedules and board sampling but not every token.
- Partners are batch-1 runs that were already analysed; the W1 contrasts are not blind to the partner data.
- Same model, board and task family as batch 1.
