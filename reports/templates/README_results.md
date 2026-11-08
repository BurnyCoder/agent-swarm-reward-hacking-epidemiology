**Confirmatory batch 1** (preregistered; Stage 2 addendum frozen at commit `3d8ddcc` before these data): MAIN
{results_summary[n_runs][MAIN]}, PLACEBO {results_summary[n_runs][PLACEBO]}, TRANSIENT
{results_summary[n_runs][TRANSIENT]} swarms of 32 agents × 11 rounds, ImpossibleBench prompt {calibration[chosen]};
dose-response assay with {results_summary[h4][table][0][n]} trials per cell. Full report:
[`reports/experiments/02_confirmatory_batch1.md`](reports/experiments/02_confirmatory_batch1.md).

| Hypothesis (preregistration §13) | Estimate [95% CI] | p (Holm for H1, H2, H4) | Verdict |
|---|---|---|---|
| H1 seeds raise hacking (MAIN − PLACEBO prevalence, rounds 1–10) | {results_summary[h1][MAIN_vs_PLACEBO][diff]:+.1%} [{results_summary[h1][MAIN_vs_PLACEBO][ci_low]:+.1%}, {results_summary[h1][MAIN_vs_PLACEBO][ci_high]:+.1%}] | {results_summary[holm][H1]:.4f} | {paper_data[verdicts][H1][verdict]}; also equivalent within ±10 pp |
| H2 agent-written posts transmit (hazard ratio per post) | {results_summary[h2][k_nonseed_pro][hr]:.2f} [{results_summary[h2][k_nonseed_pro][hr_low]:.2f}, {results_summary[h2][k_nonseed_pro][hr_high]:.2f}] | {results_summary[holm][H2]:.4f} | {paper_data[verdicts][H2][verdict]}; h₁ below h₁*: {paper_data[verdicts][H2][falsified]} |
| H4 dose-response is not simple contagion (Weibull γ) | {results_summary[h4][hack][weibull][params][gamma]:.2f} [{results_summary[h4][gamma_profile_ci][ci][0]:.2f}, {results_summary[h4][gamma_profile_ci][ci][1]:.2f}] | {results_summary[holm][H4]:.4f} | {paper_data[verdicts][H4][verdict]} ({paper_data[verdicts][H4][direction]}) |
| H3 spread is self-sustaining (R0 = π·K·h₁·D) | {results_summary[h3][R0][R0]:.3f} [{results_summary[h3][R0][R0_ci95][0]:.3f}, {results_summary[h3][R0][R0_ci95][1]:.3f}] | — | {paper_data[verdicts][H3][verdict]} ("{results_summary[h3][decision]}") |
| H5 assay predicts the MAIN curve (CRPS*, lower is better; vs broadcast-only) | {results_summary[h5][MAIN][assay_model][crps]:.2f} vs {results_summary[h5][MAIN][broadcast_only][crps]:.2f} | {results_summary[h5][MAIN][p_assay_better_than_broadcast]:.3f} | {paper_data[verdicts][H5_MAIN][verdict]} |
| H5 assay predicts the TRANSIENT curve | {results_summary[h5][TRANSIENT][assay_model][crps]:.2f} vs {results_summary[h5][TRANSIENT][broadcast_only][crps]:.2f} | {results_summary[h5][TRANSIENT][p_assay_better_than_broadcast]:.3f} | {paper_data[verdicts][H5_TRANSIENT][verdict]} |

| Condition (seed posts) | hack attempt | flag | posts judged pro-hack | difference in hack prevalence vs PLACEBO, rounds 1–10 [95% CI] |
|---|---|---|---|---|
| MAIN (pro-hack every round; treatment) | {results_summary[descriptives][MAIN][hack_attempt]:.1%} | {results_summary[descriptives][MAIN][flag]:.1%} | {results_summary[descriptives][MAIN][post_pro]:.1%} | {results_summary[h1][MAIN_vs_PLACEBO][diff]:+.1%} [{results_summary[h1][MAIN_vs_PLACEBO][ci_low]:+.1%}, {results_summary[h1][MAIN_vs_PLACEBO][ci_high]:+.1%}] |
| TRANSIENT (pro-hack rounds 0–1 only) | {results_summary[descriptives][TRANSIENT][hack_attempt]:.1%} | {results_summary[descriptives][TRANSIENT][flag]:.1%} | {results_summary[descriptives][TRANSIENT][post_pro]:.1%} | {results_summary[h1][TRANSIENT_vs_PLACEBO][diff]:+.1%} [{results_summary[h1][TRANSIENT_vs_PLACEBO][ci_low]:+.1%}, {results_summary[h1][TRANSIENT_vs_PLACEBO][ci_high]:+.1%}] |
| PLACEBO (neutral coding tips; control) | {results_summary[descriptives][PLACEBO][hack_attempt]:.1%} | {results_summary[descriptives][PLACEBO][flag]:.1%} | {results_summary[descriptives][PLACEBO][post_pro]:.1%} | — |

Rates in the second table are means over all non-seed agent-rounds including round 0.

| Assay arm (k pro-hack posts among 6 read) | k = 0 | k = 2 | k = 4 | k = 6 |
|---|---|---|---|---|
| distinct authors (method) | {results_summary[h4][table][0][hack]:.1%} | {results_summary[h4][table][2][hack]:.1%} | {results_summary[h4][table][4][hack]:.1%} | {results_summary[h4][table][5][hack]:.1%} |
| off-topic posts instead (random content control), minus k = 0 | — | {results_summary[h4][comparisons][offtopic_minus_k0][2]:+.1%} | {results_summary[h4][comparisons][offtopic_minus_k0][4]:+.1%} | {results_summary[h4][comparisons][offtopic_minus_k0][6]:+.1%} |

**In plain words.** A pro-hack post read by an agent does make that agent more likely to start hacking, and several
such posts together act more than additively. But the agents who hack rarely advertise it, they stop after about a
round, and their posts are drowned out by agents explaining that the test is wrong and flagging it. Each hacking agent
therefore "infects" far fewer than one other agent, so hacking cannot grow exponentially here; seeding the board
raises population hacking only slightly, and only while the seeds keep posting.

![Hack-attempt prevalence by round](results/figures/fig_prevalence.png)
![Dose-response assay](results/figures/fig_dose_response.png)
![Hazard ratios per post](results/figures/fig_hazard.png)
![Flag rate by round](results/figures/fig_flag_rate.png)
