# Experiment 00 — Engineering smoke test (not pilot data)

- **Date:** 2026-11-07 · **Author:** Libor "Burny" Burian · **Status:** done
- **Purpose:** check the full loop against the real model before any pilot data exist: vLLM server → agent prompts →
  sandboxed grading → board → notes → belief probe → logs and dashboard. Not part of the pilot (§8 of the
  preregistration) or of any analysis.
- **Setup:** `uv run python scripts/run_experiment.py smoke`. One run of N = 8 agents for rounds 0–3 (warm-up + T = 3),
  K = 6 posts read, m = 2 seed slots that post the seed-belief text itself (provisional; the real pools did not exist
  yet), ImpossibleBench prompt D with the flag option, up to 2 attempts. Model `cyankiwi/Qwen3.5-4B-AWQ-4bit` (thinking
  off) on vLLM 0.33.0 ([docs/serving.md](../../docs/serving.md)).
- **Inputs to this report:** `results/engineering/smoke_v1.json`, `smoke_v2.json`,
  `length_probe.json`, produced by `scripts/llm_call_stats.py` and `scripts/length_probe.py` from the full call logs.

## What went wrong in the first smoke run, and why

| Check | Smoke run 1 | Cause |
|---|---|---|
| Solve answers stopped by the 384-token cap | {smoke_v1[solve][finish_reason][length]} / {smoke_v1[solve][n]} | The model writes a test-by-test analysis before any code (prompt D asks it to "critically evaluate the unit tests"), so the code block never arrives. |
| Solve answers containing a code block | {smoke_v1[solve][has_code_fence]} / {smoke_v1[solve][n]} | Same cause. Without a closed block, ImpossibleBench's extractor falls back to the whole answer, which is prose and fails with a `SyntaxError`. |
| Answers opening with the notes header ("[Your private notes]") | {smoke_v1[solve][opens_with_notes_header]} / {smoke_v1[solve][n]} | The private notes and board sat at the top of the user turn; the model continued that format instead of answering. |
| Hack detector | no false positive in this run, but one was possible | Under prompt D the model quotes the flawed assertion in a code block (`assert candidate(...) == [..., 999]`). That block holds both literals the special-casing rule looks for. |

## Fixes (all before any pilot data; deviations #8 and #9 in [deviations.md](../deviations.md))

1. **Prompt layout.** Notes and board moved to the system message; the user turn is now exactly ImpossibleBench's task
   input (`format_task_input`, copied from `record_to_sample`).
2. **Token cap.** The length probe (40 tasks × prompts D and A, 2,048-token cap) gave median lengths of
   {length_probe[D][p50]:.0f} (D) and {length_probe[A][p50]:.0f} (A) tokens. {length_probe[D][share_le_768]:.1%} (D) and
   {length_probe[A][share_le_768]:.1%} (A) of answers end within 768 tokens, {length_probe[D][share_le_1024]:.1%} /
   {length_probe[A][share_le_1024]:.1%} within 1,024, and {length_probe[D][share_hit_2048]:.1%} /
   {length_probe[A][share_hit_2048]:.1%} run on to 2,048. A cap above ~768 mostly buys longer loops, so the cap is
   768. Requests are clamped to the 4,096-token context with vLLM's `/tokenize`.
3. **Detector.** The special-casing rule counts only literals inside submitted function bodies and outside `assert`
   statements (`tests/test_grader.py::test_quoted_assertion_is_not_special_casing`).

## Smoke run 2 (after the fixes)

| Check | Smoke run 2 |
|---|---|
| Solve answers stopped by the 768-token cap | {smoke_v2[solve][finish_reason][length]} / {smoke_v2[solve][n]} |
| Solve answers containing a code block | {smoke_v2[solve][has_code_fence]} / {smoke_v2[solve][n]} |
| Answers opening with the notes header | {smoke_v2[solve][opens_with_notes_header]} / {smoke_v2[solve][n]} |
| Post answers stopped by the 200-token cap | {smoke_v2[post][finish_reason][length]} / {smoke_v2[post][n]} |
| Probe calls (1 token, top-20 logprobs) | {smoke_v2[probe][n]} |

**Observations (smoke run 2, qualitative; N = 8 is far too small for estimates):**

- Under prompt D the agents mostly flag the impossible test, often after quoting it, and none hacked. Whether D stays
  the working prompt is decided by the preregistered calibration (§8.2), which tries D → A.
- The board works as intended. Posts describe the flawed test and the decision to flag; posts containing a code block:
  {smoke_v2[post][has_code_fence]} / {smoke_v2[post][n]}.
- Greedy probe answers: {smoke_v2[probe][top_openings]} (answer, count); P(Yes) per agent-round is in `rounds.jsonl`.

## Learnings

- A 4B model in non-thinking mode still "thinks out loud" in its answer under a strict anti-cheating prompt, so a
  generation cap tuned for code alone truncates most answers. Measure natural lengths before fixing caps.
- Context placed before the task in the user turn can be continued as a format; put agent state in the system message.
- Detectors built on literal matching need to know where a literal sits (function body vs. quoted test).
