**Exploratory batch (2026-11-08; not the preregistered confirmatory test, see
[deviation #13](reports/deviations.md)):** MAIN {explore_summary[n_runs][MAIN]}, PLACEBO
{explore_summary[n_runs][PLACEBO]}, TRANSIENT {explore_summary[n_runs][TRANSIENT]} swarms of 32 agents × 11 rounds,
ImpossibleBench prompt {calibration[chosen]}. Full report:
[`reports/experiments/01_exploratory_swarm.md`](reports/experiments/01_exploratory_swarm.md).

| Condition (seed posts) | non-seed hack-attempt prevalence, rounds 1–10 | difference vs PLACEBO [95% CI] | exact sign-flip p (one-sided) |
|---|---|---|---|
| MAIN (pro-hack every round) | {explore_summary[h1][MAIN_vs_PLACEBO][mean_a]:.1%} | {explore_summary[h1][MAIN_vs_PLACEBO][diff]:+.1%} [{explore_summary[h1][MAIN_vs_PLACEBO][ci_low]:+.1%}, {explore_summary[h1][MAIN_vs_PLACEBO][ci_high]:+.1%}] | {explore_summary[h1][MAIN_vs_PLACEBO][p_signflip]:.4f} |
| TRANSIENT (pro-hack rounds 0–1 only) | {explore_summary[h1][TRANSIENT_vs_PLACEBO][mean_a]:.1%} | {explore_summary[h1][TRANSIENT_vs_PLACEBO][diff]:+.1%} [{explore_summary[h1][TRANSIENT_vs_PLACEBO][ci_low]:+.1%}, {explore_summary[h1][TRANSIENT_vs_PLACEBO][ci_high]:+.1%}] | {explore_summary[h1][TRANSIENT_vs_PLACEBO][p_signflip]:.4f} |
| PLACEBO (neutral coding tips; control) | {explore_summary[h1][MAIN_vs_PLACEBO][mean_b]:.1%} | — | — |

| Transmission quantity | estimate [95% CI] |
|---|---|
| Hazard ratio per pro-hack post written by another (non-seed) agent | {explore_summary[h2][k_nonseed_pro][hr]:.2f} [{explore_summary[h2][k_nonseed_pro][hr_low]:.2f}, {explore_summary[h2][k_nonseed_pro][hr_high]:.2f}] |
| Hazard ratio per pro-hack seed post | {explore_summary[h2][k_seed_pro][hr]:.2f} [{explore_summary[h2][k_seed_pro][hr_low]:.2f}, {explore_summary[h2][k_seed_pro][hr_high]:.2f}] |
| Board reproduction number R0 = π·K·h₁·D | {explore_summary[h3][R0][R0]:.3f} [{explore_summary[h3][R0][R0_ci95][0]:.3f}, {explore_summary[h3][R0][R0_ci95][1]:.3f}] |
| Persistence after seeds stop (TRANSIENT − PLACEBO, rounds 8–10) | {explore_summary[h3][late_window][diff]:+.1%} [{explore_summary[h3][late_window][ci_low]:+.1%}, {explore_summary[h3][late_window][ci_high]:+.1%}] |
| Preregistered self-sustainability decision | {explore_summary[h3][decision]} |

**Counter-contagion (exploratory, model chosen after an interim look; [deviation #15](reports/deviations.md)):**
the flag rate went from {explore_summary[counter_contagion][flag_rate_round0][PLACEBO]:.0%} in round 0 (empty
board) to {explore_summary[counter_contagion][flag_rate_round10][PLACEBO]:.0%} in round 10 in PLACEBO
(MAIN {explore_summary[counter_contagion][flag_rate_round0][MAIN]:.0%} →
{explore_summary[counter_contagion][flag_rate_round10][MAIN]:.0%}). Hazard ratio of starting to flag per anti-hack
post read: {explore_summary[counter_contagion][k_anti][hr]:.2f}
[{explore_summary[counter_contagion][k_anti][hr_low]:.2f}, {explore_summary[counter_contagion][k_anti][hr_high]:.2f}].

![Hack-attempt prevalence by round](results/explore/figures/fig_prevalence.png)
![Flag rate by round](results/explore/figures/fig_flag_rate.png)
