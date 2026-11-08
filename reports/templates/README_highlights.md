**Highlights: exploratory batch, 2026-11-08** (8 swarms per condition; labels not yet audited; not the preregistered
confirmatory test, see [deviation #13](reports/deviations.md)):

- **No epidemic.** Planting pro-hack posts on the board did not raise hacking: MAIN − PLACEBO prevalence
  {explore_summary[h1][MAIN_vs_PLACEBO][diff]:+.1%} (95% CI [{explore_summary[h1][MAIN_vs_PLACEBO][ci_low]:+.1%},
  {explore_summary[h1][MAIN_vs_PLACEBO][ci_high]:+.1%}]), equivalent to zero within the preregistered ±10 points.
- **But the belief is transmissible agent to agent.** Reading one more pro-hack post written by another agent
  multiplies the hazard of starting to hack by {explore_summary[h2][k_nonseed_pro][hr]:.2f}
  ([{explore_summary[h2][k_nonseed_pro][hr_low]:.2f}, {explore_summary[h2][k_nonseed_pro][hr_high]:.2f}]; randomized
  exposure, randomization p = {explore_summary[h2][permutation_control][p_perm_one_sided]:.3f}).
- **It dies out because R0 ≪ 1.** Pro-hack posts are rare and short-lived, so each pro-hack poster causes
  R0 = {explore_summary[h3][R0][R0]:.3f} ([{explore_summary[h3][R0][R0_ci95][0]:.3f},
  {explore_summary[h3][R0][R0_ci95][1]:.3f}]) new hackers. Cumulative first hacks follow a Bass curve with imitation
  coefficient {explore_summary[growth_curves][MAIN][fits][bass][params][b]:.2f}, not an exponential.
- **Flagging takes over instead.** The flag rate rises from {explore_summary[counter_contagion][flag_rate_round0][PLACEBO]:.0%}
  to {explore_summary[counter_contagion][flag_rate_round10][PLACEBO]:.0%} over the 10 rounds (PLACEBO; MAIN and
  TRANSIENT are similar, see the report), and {explore_summary[counter_contagion][post_anti_rate][PLACEBO]:.0%} of agent posts
  are judged anti-hack (exploratory).

Full write-up: [`reports/experiments/01_exploratory_swarm.md`](reports/experiments/01_exploratory_swarm.md).
