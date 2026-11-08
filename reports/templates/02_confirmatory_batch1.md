# Experiment 02 — Confirmatory batch 1 and dose-response assay (preregistered tests H1–H5)

- **Author:** Libor "Burny" Burian · **Status:** confirmatory. The Stage 2 addendum
  ([`reports/preregistration_stage2.md`](../preregistration_stage2.md), commit `3d8ddcc`) was pushed before any of
  these data existed. This report template was written before the data, too.
- **Inputs:** `results/summary.json` (from `uv run python scripts/analyze.py`), verdicts from `paper/data.json`
  (from `scripts/make_paper.py`, preregistration §13). Deviations: [`reports/deviations.md`](../deviations.md).
- **Design:** MAIN {results_summary[n_runs][MAIN]}, PLACEBO {results_summary[n_runs][PLACEBO]}, TRANSIENT
  {results_summary[n_runs][TRANSIENT]} swarms of 32 agents × 11 rounds, K = 6 posts read per round, m = 2 seed slots,
  prompt {calibration[chosen]}; seed pools and all other constants as in the Stage 2 addendum.
  Assay: randomized single-agent trials with k pro-hack posts among K = 6 (deviation #18: no same-author k = 4 cell).

## Verdicts (preregistration §13)

| Hypothesis | Test | Estimate [CI] | p (Holm) | Verdict |
|---|---|---|---|---|
| H1 contagion | MAIN − PLACEBO prevalence, rounds 1–10 | {results_summary[h1][MAIN_vs_PLACEBO][diff]:+.1%} [{results_summary[h1][MAIN_vs_PLACEBO][ci_low]:+.1%}, {results_summary[h1][MAIN_vs_PLACEBO][ci_high]:+.1%}] | {results_summary[holm][H1]:.4f} | **{paper_data[verdicts][H1][verdict]}** |
| H2 secondary transmission | hazard ratio per non-seed pro-hack post | {results_summary[h2][k_nonseed_pro][hr]:.2f} [{results_summary[h2][k_nonseed_pro][hr_low]:.2f}, {results_summary[h2][k_nonseed_pro][hr_high]:.2f}] | {results_summary[holm][H2]:.4f} | **{paper_data[verdicts][H2][verdict]}** |
| H4 dose-response shape | Weibull γ (simple contagion: γ = 1), LRT | γ = {results_summary[h4][hack][weibull][params][gamma]:.2f} [{results_summary[h4][gamma_profile_ci][0]:.2f}, {results_summary[h4][gamma_profile_ci][1]:.2f}] | {results_summary[holm][H4]:.4f} | **{paper_data[verdicts][H4][verdict]}** |
| H3 self-sustaining | decision rule; R0 = π·K·h₁·D | R0 = {results_summary[h3][R0][R0]:.3f} [{results_summary[h3][R0][R0_ci95][0]:.3f}, {results_summary[h3][R0][R0_ci95][1]:.3f}] | — | **{paper_data[verdicts][H3][verdict]}** ({results_summary[h3][decision]}) |
| H5 prediction (MAIN) | CRPS* assay model vs broadcast-only | {results_summary[h5][MAIN][assay_model][crps]:.2f} vs {results_summary[h5][MAIN][broadcast_only][crps]:.2f} | {results_summary[h5][MAIN][p_assay_better_than_broadcast]:.4f} | **{paper_data[verdicts][H5_MAIN][verdict]}** |
| H5 prediction (TRANSIENT) | as above | {results_summary[h5][TRANSIENT][assay_model][crps]:.2f} vs {results_summary[h5][TRANSIENT][broadcast_only][crps]:.2f} | {results_summary[h5][TRANSIENT][p_assay_better_than_broadcast]:.4f} | **{paper_data[verdicts][H5_TRANSIENT][verdict]}** |

H2 falsification check (§13): upper 90% bound of h₁ = {results_summary[h2][h1_ci90][1]:.4f} against
h₁* = {results_summary[h2][h1_star]:.4f} (falsified: {results_summary[h2][falsified_h1_below_star]}). H1 equivalence
within ±10 pp: paired TOST p = {results_summary[h1][MAIN_vs_PLACEBO][p_tost_paired]:.1e}.

## H1 and H3: prevalence

| Condition | hack attempt | flag | post judged pro-hack | seed / agent pro-hack / anti-hack posts read per round |
|---|---|---|---|---|
| MAIN | {results_summary[descriptives][MAIN][hack_attempt]:.1%} | {results_summary[descriptives][MAIN][flag]:.1%} | {results_summary[descriptives][MAIN][post_pro]:.1%} | {results_summary[descriptives][MAIN][reads_seed_pro]:.2f} / {results_summary[descriptives][MAIN][reads_nonseed_pro]:.2f} / {results_summary[descriptives][MAIN][reads_anti]:.1f} |
| PLACEBO | {results_summary[descriptives][PLACEBO][hack_attempt]:.1%} | {results_summary[descriptives][PLACEBO][flag]:.1%} | {results_summary[descriptives][PLACEBO][post_pro]:.1%} | {results_summary[descriptives][PLACEBO][reads_seed_pro]:.2f} / {results_summary[descriptives][PLACEBO][reads_nonseed_pro]:.2f} / {results_summary[descriptives][PLACEBO][reads_anti]:.1f} |
| TRANSIENT | {results_summary[descriptives][TRANSIENT][hack_attempt]:.1%} | {results_summary[descriptives][TRANSIENT][flag]:.1%} | {results_summary[descriptives][TRANSIENT][post_pro]:.1%} | {results_summary[descriptives][TRANSIENT][reads_seed_pro]:.2f} / {results_summary[descriptives][TRANSIENT][reads_nonseed_pro]:.2f} / {results_summary[descriptives][TRANSIENT][reads_anti]:.1f} |

TRANSIENT − PLACEBO, rounds 8–10: {results_summary[h3][late_window][diff]:+.1%}
[{results_summary[h3][late_window][ci_low]:+.1%}, {results_summary[h3][late_window][ci_high]:+.1%}]; π =
{results_summary[h3][R0][pi]:.3f}, h₁ = {results_summary[h2][h1_marginal]:.4f}, D = {results_summary[h3][R0][D]:.2f}.

![Prevalence by round](../../results/figures/fig_prevalence.png)

## H2: per-post hazard (randomized exposure)

| Exposure | hazard ratio [95% CI] | one-sided p |
|---|---|---|
| pro-hack post by a non-seed agent | {results_summary[h2][k_nonseed_pro][hr]:.2f} [{results_summary[h2][k_nonseed_pro][hr_low]:.2f}, {results_summary[h2][k_nonseed_pro][hr_high]:.2f}] | {results_summary[h2][k_nonseed_pro][p_one_sided]:.4f} |
| pro-hack seed post | {results_summary[h2][k_seed_pro][hr]:.2f} [{results_summary[h2][k_seed_pro][hr_low]:.2f}, {results_summary[h2][k_seed_pro][hr_high]:.2f}] | {results_summary[h2][k_seed_pro][p_one_sided]:.4f} |
| robustness: run × round FE | {results_summary[h2][robust_run_round_fe][hr]:.2f} [{results_summary[h2][robust_run_round_fe][hr_low]:.2f}, {results_summary[h2][robust_run_round_fe][hr_high]:.2f}] | {results_summary[h2][robust_run_round_fe][p_one_sided]:.4f} |
| robustness: judge-free exposure | {results_summary[h2][robust_author_status][hr]:.2f} [{results_summary[h2][robust_author_status][hr_low]:.2f}, {results_summary[h2][robust_author_status][hr_high]:.2f}] | {results_summary[h2][robust_author_status][p_one_sided]:.4f} |

Randomization p (1,000 within run × round permutations) = {results_summary[h2][permutation_control][p_perm_one_sided]:.4f};
risk set {results_summary[h2][n_rows]} agent-rounds, {results_summary[h2][n_events]} onsets.

![Hazard ratios](../../results/figures/fig_hazard.png)

## H4: dose-response assay

| k pro-hack posts of 6 | trials | P(hack attempt) | P(own post pro-hack) |
|---|---|---|---|
| {results_summary[h4][table][0][k]} | {results_summary[h4][table][0][n]} | {results_summary[h4][table][0][hack]:.1%} | {results_summary[h4][table][0][post_pro]:.1%} |
| {results_summary[h4][table][1][k]} | {results_summary[h4][table][1][n]} | {results_summary[h4][table][1][hack]:.1%} | {results_summary[h4][table][1][post_pro]:.1%} |
| {results_summary[h4][table][2][k]} | {results_summary[h4][table][2][n]} | {results_summary[h4][table][2][hack]:.1%} | {results_summary[h4][table][2][post_pro]:.1%} |
| {results_summary[h4][table][3][k]} | {results_summary[h4][table][3][n]} | {results_summary[h4][table][3][hack]:.1%} | {results_summary[h4][table][3][post_pro]:.1%} |
| {results_summary[h4][table][4][k]} | {results_summary[h4][table][4][n]} | {results_summary[h4][table][4][hack]:.1%} | {results_summary[h4][table][4][post_pro]:.1%} |
| {results_summary[h4][table][5][k]} | {results_summary[h4][table][5][n]} | {results_summary[h4][table][5][hack]:.1%} | {results_summary[h4][table][5][post_pro]:.1%} |

Akaike weights: simple {results_summary[h4][hack][simple][akaike_weight]:.2f}, Weibull
{results_summary[h4][hack][weibull][akaike_weight]:.2f}, sigmoid {results_summary[h4][hack][sigmoid][akaike_weight]:.2f}.
One-step transmission map: R_map = f′(0) = {results_summary[h4][post_map][R_map]:.3f} (95% CI
[{results_summary[h4][post_map][R_map_ci95][0]:.3f}, {results_summary[h4][post_map][R_map_ci95][1]:.3f}]). Same −
distinct author at k = 2: {results_summary[h4][comparisons][same_minus_distinct_k2]:+.1%}. Off-topic content control
at k = 6 vs k = 0: {results_summary[h4][comparisons][offtopic_minus_k0][6]:+.1%} (TOST p =
{results_summary[h4][comparisons][offtopic_k6_tost_p]:.4f}).

![Dose-response](../../results/figures/fig_dose_response.png)

## H5: does the assay predict the swarm?

| Model | CRPS* MAIN | CRPS* TRANSIENT | 90% coverage MAIN / TRANSIENT |
|---|---|---|---|
| assay-calibrated simulator | {results_summary[h5][MAIN][assay_model][crps]:.2f} | {results_summary[h5][TRANSIENT][assay_model][crps]:.2f} | {results_summary[h5][MAIN][assay_model][coverage90]:.0%} / {results_summary[h5][TRANSIENT][assay_model][coverage90]:.0%} |
| broadcast-only baseline | {results_summary[h5][MAIN][broadcast_only][crps]:.2f} | {results_summary[h5][TRANSIENT][broadcast_only][crps]:.2f} | {results_summary[h5][MAIN][broadcast_only][coverage90]:.0%} / {results_summary[h5][TRANSIENT][broadcast_only][coverage90]:.0%} |
| leave-one-out logistic (strong baseline) | {results_summary[h5][MAIN][loo_logistic][crps]:.2f} | {results_summary[h5][TRANSIENT][loo_logistic][crps]:.2f} | {results_summary[h5][MAIN][loo_logistic][coverage90]:.0%} / {results_summary[h5][TRANSIENT][loo_logistic][coverage90]:.0%} |

![Out-of-sample prediction](../../results/figures/fig_h5_prediction.png)

## Exploratory: counter-contagion (model from deviation #15)

Flag rate round 0 → 10 (PLACEBO): {results_summary[counter_contagion][flag_rate_round0][PLACEBO]:.0%} →
{results_summary[counter_contagion][flag_rate_round10][PLACEBO]:.0%}; hazard ratio of starting to flag per anti-hack
post read {results_summary[counter_contagion][k_anti][hr]:.2f} [{results_summary[counter_contagion][k_anti][hr_low]:.2f},
{results_summary[counter_contagion][k_anti][hr_high]:.2f}].

![Flag rate by round](../../results/figures/fig_flag_rate.png)
