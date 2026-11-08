**Highlights: preregistered confirmatory batch, 2026-11-08** ({results_summary[n_runs][MAIN]} MAIN,
{results_summary[n_runs][PLACEBO]} PLACEBO, {results_summary[n_runs][TRANSIENT]} TRANSIENT swarms of 32 agents, plus a
randomized single-agent dose-response assay; analysis frozen at Stage 2 before the data existed):

- **No epidemic.** The belief is subcritical: the board reproduction number is R0 = {results_summary[h3][R0][R0]:.3f}
  (95% CI [{results_summary[h3][R0][R0_ci95][0]:.3f}, {results_summary[h3][R0][R0_ci95][1]:.3f}]), far below the
  epidemic threshold of 1, and hacking returned to the control level once the seeds stopped (H3:
  **{paper_data[verdicts][H3][verdict]}**). No exponential phase appears in any condition.
- **Seeding raises hacking, but only slightly.** MAIN − PLACEBO prevalence
  {results_summary[h1][MAIN_vs_PLACEBO][diff]:+.1%} (95% CI [{results_summary[h1][MAIN_vs_PLACEBO][ci_low]:+.1%},
  {results_summary[h1][MAIN_vs_PLACEBO][ci_high]:+.1%}], Holm p = {results_summary[holm][H1]:.4f}): statistically
  supported, and also equivalent to zero within the preregistered ±10 points.
- **Agent-to-agent transmission is real (causal).** Each pro-hack post written by another agent multiplies the hazard
  of starting to hack by {results_summary[h2][k_nonseed_pro][hr]:.2f} ([{results_summary[h2][k_nonseed_pro][hr_low]:.2f},
  {results_summary[h2][k_nonseed_pro][hr_high]:.2f}], randomized exposure; H2 **{paper_data[verdicts][H2][verdict]}**),
  but the absolute increase per post is below the preregistered threshold, and pro-hack posts are rare and short-lived.
- **Single agents respond superlinearly.** In the assay, hacking rises from {results_summary[h4][table][0][hack]:.0%}
  with no pro-hack post to {results_summary[h4][table][5][hack]:.0%} with six of six; Weibull γ =
  {results_summary[h4][hack][weibull][params][gamma]:.2f} > 1 (H4 **{paper_data[verdicts][H4][verdict]}**, reinforcing).
  Off-topic posts in the same slots do not raise it.
- **The single-agent assay does not forecast the swarm** better than a broadcast-only baseline (H5 MAIN
  **{paper_data[verdicts][H5_MAIN][verdict]}**): honest flagging spreads through the board (flag rate
  {results_summary[counter_contagion][flag_rate_round0][PLACEBO]:.0%} → {results_summary[counter_contagion][flag_rate_round10][PLACEBO]:.0%}),
  a counter-contagion the assay cannot see.

Full write-up: [`reports/experiments/02_confirmatory_batch1.md`](reports/experiments/02_confirmatory_batch1.md);
paper: [`paper/paper.pdf`](paper/paper.pdf). The earlier exploratory batch
([`01_exploratory_swarm.md`](reports/experiments/01_exploratory_swarm.md), deviation #13) found the same pattern.
