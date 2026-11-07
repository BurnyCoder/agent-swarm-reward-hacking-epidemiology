# Deviations log and preregistration versions

Required by [`preregistration.md`](preregistration.md) §12: every deviation from the preregistration or the Stage 2
addendum is logged here, with its date, reason, and whether confirmatory outcome data had been seen when it was made.

## Preregistration versions

| Version | Commit | Date | Data existing at commit time |
|---|---|---|---|
| Stage 1 (design and analysis plan) | `aa92fe9` | 2026-11-07 | none (no model output of any kind) |
| Stage 2 addendum (pilot constants) | filled in when `reports/preregistration_stage2.md` is pushed | | pilot data only |

## Code provenance

- ImpossibleBench code (prompts A–D, minimal-scaffold loop, scorer assembly) is copied from
  [`safety-research/impossiblebench`](https://github.com/safety-research/impossiblebench) at commit `d4f9a149`
  (2026-10-13). That commit comes after `74ae2e85`, satisfying preregistration §3.

## Deviations

| # | Date | What | Why | Before confirmatory data? |
|---|---|---|---|---|
| 1 | 2026-11-07 | **Code extraction.** `find_code` uses one left-to-right fence regex instead of ImpossibleBench's two concatenated regexes. | ImpossibleBench's version can return the prose *between* two code blocks as "code" (shown by a unit test in `tests/test_grader.py`). The intended behaviour, "last code block", is unchanged. | yes |
| 2 | 2026-11-07 | **Weibull parametrization.** The code fits p(k) = 1 − (1 − ε)·exp(−λ′k^γ); §7.2 writes exp(−(λk)^γ). | The two are equivalent: λ′ = λ^γ. The shape γ, the likelihood-ratio test of γ = 1 and every prediction are identical. | yes |
| 3 | 2026-11-07 | **H2 fitting.** The cloglog GLM is fitted by our own sparse IRLS (`epi/hazard.py::irls_cloglog`). Fixed-effect levels with no outcome variation are dropped before fitting, as R's `fixest` does for binomial models. | Speed: statsmodels' dense solves took about 45 s per fit, and §9.2/§9.7 need about 3,000 refits. On our test data the estimates and run-clustered standard errors match statsmodels' `GLM(Binomial(CLogLog))` to 1e-6. Like statsmodels, the sandwich uses the observed-information bread. `statsmodels_check` reports this agreement in every analysis. Dropping all-0/all-1 levels is needed for the MLE to exist and does not change the slopes' likelihood. | yes |
| 4 | 2026-11-07 | **Power simulation test statistic.** Power for H1 (§8.6) is computed with the one-sided paired t-test as a fast stand-in for the exact sign-flip test. | 2^20 enumerations × ≥1,000 datasets × 6 scenarios is infeasible. Both tests target the mean paired difference and agree closely at n = 20. | yes |
| 5 | 2026-11-07 | **H5 simulator post stance.** The simulator draws each post's stance from two probabilities measured in the dose-response assay: π_h = P(own post pro-hack \| agent hack-attempted) and π_n = P(own post pro-hack \| no attempt). It does not draw from the k-indexed map q_k. | q_k mixes agents that hacked and agents that did not, so a simulator with a persistent hacking state needs stance conditional on that state. Both quantities still come only from the assay, so no swarm outcome data enter the forecast, as §9.5 requires. q_k is still used for R_map and the regime (§7.1). | yes |
| 6 | 2026-11-07 | **Power-phase stance assumptions.** The pre-assay power simulation assumes π_h = 0.5 and π_n = 0.02. | §8.6 gives no source for post stance before the assay. The values are conservative; the actual values are reported in the Stage 2 addendum once measured. | yes |
| 7 | 2026-11-07 | **Who labels the audits.** The ~200-post judge validation (§8.5) and the ~200-submission detector audit (§4.1) are labelled by Claude (the coding assistant that wrote this codebase; a different, larger model than the Qwen3.5-4B judge), blind to condition, round and judge output. They are not labelled by the human author. | Time; the human author may re-label the same blinded files (`audit/`) to check agreement. Reported as a limitation. | yes |
| 8 | 2026-11-07 | **Special-casing detector scope.** §4.1 rule 1 counts literals "in the submission"; the code counts only literals inside submitted function bodies (not a redefined `check`), skipping `assert` statements. | In the engineering smoke test (N = 8, T = 3, not pilot data), prompt D made the model quote the flawed assertion in a code block to explain why it is wrong. That code block holds both the mutated argument and the mutated expected value, so the literal rule would call an explanation a hack. Hard-coding means the function returns the value, so only function bodies count. Unit test `test_quoted_assertion_is_not_special_casing`. | yes (before any pilot data) |
| 9 | 2026-11-07 | **Implementation settings not fixed by the preregistration** (logged for transparency). (a) The code-answer cap is 768 tokens, not 384. (b) Every request's `max_tokens` is clamped so that prompt + output ≤ 4,096 tokens, using vLLM's `/tokenize`. (c) Notes and board posts go in the system message, so the user turn is exactly ImpossibleBench's task input. | (a) In smoke test 1, 40/59 solve answers hit the 384 cap and 5/59 contained a code block (`results/engineering/smoke_v1.json`). `scripts/length_probe.py` gives 40 tasks per prompt a 2,048-token cap (`results/engineering/length_probe.json`): median 546 tokens (prompt D) and 146 (A); 60% / 82.5% of answers end within 768 tokens; 12.5% / 10% run on to 2,048, mostly as looping analysis. A higher cap therefore mostly buys longer loops. (b) prevents HTTP 400 errors at `--max-model-len 4096`. (c) With the context at the top of the user turn, 22/59 answers began by echoing the notes header; after the move, 1/44 did (`smoke_v2.json`). | yes (before any pilot data) |
