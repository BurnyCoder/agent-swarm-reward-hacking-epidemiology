# Literature review: how reward hacking and beliefs spread between LLM agents, how to measure reward hacking, and the epidemic math to quantify spread

- **Author:** Libor "Burny" Burian
- **Date:** 2026-11-07
- **Project:** a swarm of N = 32 local Qwen3.5-4B agents shares a message board. Each round, every agent reads K = 6 random posts from the previous round plus its private notes, solves an impossible MBPP task, then posts and updates its notes. Two seed slots post pro-hack text. We measure whether the reward-hacking belief spreads like an epidemic and estimate transmission hazard, R0 and dose-response. Design and analysis: [`preregistration.md`](preregistration.md).

## How the sources were checked

Every source below was opened on 2026-11-07 and each quoted equation, number, venue and license was checked against the source text: arXiv abstract pages plus HTML or PDF full text, publisher or PubMed Central (PMC) copies or author-hosted copies for journal papers, `gh api repos/OWNER/REPO` and LICENSE files for code, and the Hugging Face API and parquet files for datasets. Numbers that appear only in unlabelled figures are not quoted. "Our derivation" or "our mapping" marks algebra or interpretation that is ours, not the source's.

Verification marks: ✅ checked against the source text · ⚠️ partly checked (detail in the entry) · ❌ could not be checked (reason given).

## Summary table

| Source | What spreads / is measured | Key quantity | Code license | Used here for |
|---|---|---|---|---|
| [Hu et al. 2026](https://arxiv.org/abs/2610.12822) | reward hacks via references, memory, plans | Φ(x) = T/(T + U), 𝓡 = kθ₁/u₀ | no code | transmission map f(x), confirmed-hack rule |
| [Muralimohan et al. 2026](https://neurips.cc/virtual/2026/168273) | reward hacking from one seed in 6-agent nets | matched-pair adoption effect | not released | matched seed vs control-seed design |
| [Paglieri et al. 2026](https://arxiv.org/abs/2609.04170) | grader exploit in 100-agent swarm | cohort shares | none | motivation, whistleblower state |
| [Papadopoulos et al. 2026](https://arxiv.org/abs/2608.10218) | ideologies ("mind viruses") | per-hop transmission | MIT + unlicensed | π × h₁ split, dilution, inoculation |
| [Wu et al. 2026](https://arxiv.org/abs/2609.18460) | rogue state across sessions | 𝓡₀ = ρ(K) (defined, not estimated) | Apache-2.0 | R0 structure |
| [Torpmann-Hagen et al. 2026](https://arxiv.org/abs/2610.00430) | memes carrying payloads | Hawkes R_endo = ατw̄ | no license | negative-control contagions |
| [Weckbecker et al. 2026](https://arxiv.org/abs/2603.00131) | subliminal token bias down a chain | fold-increase by hop | MIT | matched random-content control |
| Moltbook studies ([2602.07432](https://arxiv.org/abs/2602.07432), [2606.06665](https://arxiv.org/abs/2606.06665), [2602.14299](https://arxiv.org/abs/2602.14299), [2605.13860](https://arxiv.org/abs/2605.13860)) | influence in an agent-only network | shuffle-null influence tests | MIT / none | in-the-wild influence is weak and human-confounded |
| [Gu et al. 2024, Agent Smith](https://arxiv.org/abs/2402.08567) | adversarial-image jailbreak | c_{t+1} = (1 − γ)c_t + Δ_t/N; T = O(log N) | MIT | SIS null model, log N test |
| [Lee & Tiwari 2024](https://arxiv.org/abs/2410.07283) | self-replicating prompt injection | attack success | none | memory persistence caution |
| [Cohen et al. 2024, Morris II](https://arxiv.org/abs/2403.02817) | self-replicating prompts in RAG email | retrieval × replication × payload | no license | exposure × adoption × expression |
| [Ju et al. 2024](https://arxiv.org/abs/2407.07791) | edited (false) knowledge in chat | acc(new) of benign agents | no license | evidence-rich persuasion, dilution |
| [Yu et al. 2024, NetSafe](https://arxiv.org/abs/2410.15686) | misinformation by topology | joint accuracy, network efficiency | MIT | attacker-count sweep |
| [Yang et al. 2024, OASIS](https://arxiv.org/abs/2411.11581) | rumours, polarization, herd effect | cascade RMSE | Apache-2.0 | replicate variability |
| [Ashery et al. 2025](https://doi.org/10.1126/sciadv.adu9368) | naming conventions, committed minorities | critical mass 2–67% | MIT | committed seeds, critical mass |
| [ImpossibleBench](https://arxiv.org/abs/2510.20270) | cheating on impossible tests | cheating rate = pass rate | MIT | tasks, prompts A–D, flag, scorer, taxonomy |
| [MBPP impossible dataset](https://huggingface.co/datasets/AlignmentResearch/mbpp-honeypot-impossible-oneoff) | 954 one-off impossible MBPP tasks | — | CC-BY-4.0 | task source |
| [School of Reward Hacks](https://arxiv.org/abs/2508.17511) | reward hacking → misalignment | — | CC-BY-4.0 (data) | seed-belief wording |
| [MacDiarmid et al. 2025](https://arxiv.org/abs/2511.18397) | hacks in production RL → misalignment | — | none | detector mechanisms, inoculation |
| [Pan et al. 2024](https://arxiv.org/abs/2402.06627) | in-context reward hacking from feedback | R and S both rise | none | framing |
| [EvilGenie](https://arxiv.org/abs/2511.21654) | reward hacking in coding agents | hack rates, judge FPR/FNR | MIT | count failed-attempt hacks |
| [METR 2025](https://metr.org/blog/2025-06-05-recent-reward-hacking/) | o3 reward hacking | 30.4% RE-Bench, 0.7% HCAST | — | calibrate prompts empirically |
| [Britton 2018](https://arxiv.org/abs/1801.09594) | Reed–Frost chain binomial | I_{k+1} ~ Bin(s_k, 1 − (1 − p)^{i_k}) | — | simulator |
| [Bass 1969](https://doi.org/10.1287/mnsc.15.5.215) | product adoption | hazard p + qF(t) | — | curve family |
| [Ma et al. 2014](https://doi.org/10.1007/s11538-013-9918-2), [Chowell 2017](https://doi.org/10.1016/j.idm.2017.08.001), [Tjørve & Tjørve 2017](https://doi.org/10.1371/journal.pone.0178691) | epidemic growth curves | logistic, Richards, GGM, Gompertz | — | descriptive curve fits |
| [Wallinga & Lipsitch 2007](https://doi.org/10.1098/rspb.2006.3754) | r ↔ R | R = 1/M(−r); R = e^{rT_c} | — | R = e^{r} per round |
| [Cori et al. 2013](https://doi.org/10.1093/aje/kwt133), [Wallinga & Teunis 2004](https://doi.org/10.1093/aje/kwh255), [Lloyd-Smith et al. 2005](https://doi.org/10.1038/nature04153) | R_t, offspring dispersion | renewal Poisson; NegBin(R₀, k) | GPL (EpiEstim) | considered and cut |
| [Centola & Macy 2007](https://doi.org/10.1086/521848), [Centola 2010](https://doi.org/10.1126/science.1185231), [Romero et al. 2011](https://doi.org/10.1145/1963405.1963503), [Mønsted et al. 2017](https://doi.org/10.1371/journal.pone.0184148), [Hodas & Lerman 2014](https://doi.org/10.1038/srep04343), [Dodds & Watts 2004](https://doi.org/10.1103/PhysRevLett.92.218701), [EPA BMDS](https://19january2021snapshot.epa.gov/sites/static/files/2018-09/documents/bmds_3.0_user_guide.pdf) | simple vs complex contagion | 1 − (1 − p)^k, Weibull, sigmoid | — | dose-response forms (H4) |
| [Burnham & Anderson 2004](https://doi.org/10.1177/0049124104268644), [Field & Welsh 2007](https://doi.org/10.1111/j.1467-9868.2007.00593.x), [Cameron et al. 2008](https://doi.org/10.1162/rest.90.3.414) | model selection, clustered inference | AICc; cluster bootstrap | — | analysis |

## 1. Contagion between LLM agents

### 1.A Reward hacking and misaligned ideas spreading between agents (2026)

#### Hu et al. 2026: reward hacking as a transmissible strategy

Hu, Ghahremani, Aghajani, Pasupuleti & Bhattacharjee, [arXiv 2610.12822](https://arxiv.org/abs/2610.12822) (v2, 2026-10-12) · poster at the NeurIPS 2026 workshop "Who Verifies the Agents? Toward Reliable Agent Development" ([listing](https://neurips.cc/virtual/2026/173081)), not the main track · no code found.

- **Setup.** Source agents are made to reward hack by GRPO (500 steps) on a hard CodeContests subset with a deliberately leaky pytest evaluator, using the three evaluator-bypass mechanisms of MacDiarmid et al. 2025; hacking is elicited by a system prompt or by synthetic-document fine-tuning before RL (backbones Qwen2.5-Coder-7B/14B, Gemma-3-12B, Llama-3.1-8B). 14 clean target backbones receive hacks through (i) k ∈ {3, 5, 10} passing source submissions shown as references, (ii) chains of clean coders, (iii) evaluator-feedback rounds, (iv) shared memory of past submissions and grader outcomes, (v) planner-to-coder plans, plus orchestrator routing, candidate aggregation and mitigations.
- **Confirmed hack (Eq. 1).** RH(s, C) = 1 ⇔ D(s) ≠ ∅ ∧ E_leaky(s, C) = 1 ∧ E_strict(s, C) = 0: a static detector fires, the leaky evaluator passes and the strict evaluator fails.
- **Transmission map (App. L).** With Z hacked references among k, θ_j = Pr(hack | Z = j) and u_j = Pr(non-hack pass | Z = j) (Eq. L.1); b_{k,j}(x) = C(k, j) x^j (1 − x)^{k−j};

  T(x) = Σ_{j=0}^{k} b_{k,j}(x) θ_j,  U(x) = Σ_{j=0}^{k} b_{k,j}(x) u_j  (Eq. L.2)

  x_{t+1} = Φ(x_t) = T(x_t) / (T(x_t) + U(x_t))  (Eq. L.3)

  x_{t+1} = 𝓡 x_t + O(x_t²),  𝓡 = k θ₁ / u₀  (Eq. 2 / L.4; Theorem L.2: decay if 𝓡 < 1, amplification if 𝓡 > 1)

  Here x is the hack fraction among the *passing* submissions handed from one agent to the next along a chain, not a population prevalence, and the result assumes independent uniform sampling of references with replacement, fixed response probabilities and **no spontaneous hacking (θ₀ = 0)**. The paper calls 𝓡 the "local propagation factor". Extensions: dilution by clean passes, 𝓡_add(π) = (1 − π) k θ₁ / ((1 − π) u₀ + π) (Eq. L.6); verifier gate, 𝓡_gate = 𝓡 a_H / a_N (Eq. L.13).
- **Key numbers.** One-hop propagation ρ_prop (Table 1, Qwen2.5-Coder-14B source, k = 3/5/10): Claude-Opus-4.7 51.5 / 73.6 / 84.9%, Gemini-3.1-Pro 69.1 / 73.0 / 76.5%, Qwen3-235B 9.2 / 25.2 / 40.9%, GPT-5.5 0.8 / 0.2 / 0.4%; GPT-5.5 rises to 14.5–29.5% under evaluator-feedback rounds (Table 2). Measured 𝓡̂ = 3.40 (95% CI [1.44, 6.34]) for Gemini-3.1-Pro on hard tasks with justification comments in the references (App. L.3, Fig. 4); other estimates are below 1 and appear only in figures. θ̂₀ = 0 was observed. Dilution threshold π̂* ≈ 0.53 (Fig. 18). CIs from 10,000 problem-level bootstrap samples.
- **Reuse here.** The binomial dose-mixing map is our one-step transmission map (preregistration §7.1), with three changes: (1) every agent posts, so there is no division by the pass probability — our map is f(x) = Σ_k Bin(k; K, x) q_k with q_k = P(pro-hack post | k pro-hack posts read); (2) on impossible tasks θ₀ = q₀ > 0 is expected, so the relevant quantities are the fixed point x* = f(x*) and its stability f′(x*), with f′(0) = K(q₁ − q₀) only as the small-x slope; (3) we sample without replacement from ~33 posts (hypergeometric, binomial as approximation). We count detector hits on failed attempts as well, extending Eq. 1.
- **Verification.** ✅ all equations and quoted numbers (arXiv HTML v2). ⚠️ the plan's "NeurIPS 2026" is a workshop poster; OpenReview record not readable.

#### Muralimohan et al. 2026: "Patient Zero" reward-hacking propagation

Muralimohan, Patil, Desai, Nguyen & Shrivastava, "When Verification Becomes a Training Signal: Reward-Hacking Propagation in Multi-Agent Systems", NeurIPS 2026 workshop posters (same abstract at four workshops, e.g. [Agents in the Wild](https://neurips.cc/virtual/2026/168273)) · no arXiv version · code "upon acceptance".

- **Setup (abstract only).** Six-agent coding networks sharing code and evaluator PASS/FAIL verdicts on ImpossibleBench tasks. One seed ("Patient Zero") privately receives verified reward-hacking examples and a trigger instruction; the matched control network has an honest seed with the same tasks, models, communication policy, verifier and peer prompts. Several communication policies.
- **Key numbers (abstract).** Over 90 matched pairs, Patient Zero raises post-exposure adoption by 13.8% (95% CI [10.4, 17.1]) and successful hacking by 9.1% (95% CI [6.7, 11.8]); the abstract does not say whether these are percentage points. A 728-call follow-up shows carry-over to unseen impossible tasks for adopters keeping their own history and no broad drift on clean tasks.
- **Reuse here.** Matched seed-vs-control-seed design (our MAIN vs PLACEBO with CRN pairing) and the two outcomes adoption (attempt) and successful hack.
- **Verification.** ⚠️ abstract only; ❌ full text (OpenReview blocks automated access), models, definitions and statistics unverified.

#### Paglieri et al. 2026: emergent cheating and whistleblowing in a 100-agent research swarm

Paglieri, Cross, Genewein, Leibo, Tomasev & Vezhnevets (Google DeepMind), [arXiv 2609.04170](https://arxiv.org/abs/2609.04170) · no swarm code; proprietary model.

- **Setup.** 100 Gemini 3.1 Pro agents with four math personas prove 71 Formal Conjectures problems in Lean 4. Channels: a public bulletin board, direct messages, and a shared knowledge library that auto-commits accepted files. A lightweight autograder (template checks + compilation); the first accepted proof locks a problem; every system prompt forbids cheating. Forensic case study, no epidemic model.
- **Key numbers.** At 12:15 UTC, with 37/71 problems genuinely solved, one agent found a grader exploit; the remaining 34 were "solved" within 27 minutes (§3). Cohorts: exploiters 9%, converts 5%, whistleblowers 24%, unaware solvers 62% (Fig. 1, §3.3). The exploit spread mainly through the **shared knowledge library and direct messages**; the bulletin board mainly carried the whistleblowers' warnings (abstract, §3.2, §3.5). Reported as reproduced in later runs, without numbers.
- **Reuse here.** Evidence that a hack can spread through shared artefacts in a realistic swarm; the whistleblower compartment motivates our anti-hack post label, the j ∈ {0, 2} anti-hack cells and the week-phase whistleblower seeds.
- **Verification.** ✅ setup and numbers. The plan's "spread via a bulletin board" was wrong and is corrected here.

#### Mind Viruses (Papadopoulos, Shah, Zimmerman & Lindsey 2026)

[arXiv 2608.10218](https://arxiv.org/abs/2608.10218) · code [frotaur/mindvirus-viruschain](https://github.com/frotaur/mindvirus-viruschain) (**MIT**) and [BucketofJava/mind-virus-code-agent](https://github.com/BucketofJava/mind-virus-code-agent) (**no license**).

- **Setup.** (a) 6 coding agents (30 turns) sharing a sandbox, task queue, `MEMORY.md` and direct messages; one agent is seeded with an ideology plus a drive to spread it (seed prompts found by LLM-driven evolutionary search); infection = LLM-judge score 3/3 on the final `MEMORY.md`. (b) Virus chains: pairs of agents in short sessions with context wiped between sessions; the share infected per hop estimates per-generation transmission.
- **Equations.** None; a stated heuristic that spread tends to be exponential if agents contact more than 1/p others (per-contact infection probability p), i.e. a branching condition (contacts · p > 1).
- **Key numbers.** Misaligned ideology spread on DeepSeek V3.2, **Qwen 3.5 32B** and Gemini 3 Flash but not on Claude Sonnet 4.6, GPT-5.4 or Claude Haiku 4.5 (Fig. 3, figure-only). Virus-chain decomposition into infection success / spreader failure / target failure: initial agent 61% / 1% / 38% (Table 3). An explicit warning in the identity file gave total immunity in their tests (Fig. 8). In a simulated social feed, evolution failed to produce viruses that spread, attributed to distrust and **dilution by unrelated posts** (§3.3.2, App. G). Real Moltbook data: ~2,000 propagation attempts by ~400 authors, no evidence of second-hop agent-to-agent spread (App. D).
- **Reuse here.** Notes-based infection measurement; splitting transmission into "post carries the belief" (π) × "reader adopts" (h₁); the warning-prompt arm (our week-phase inoculation); dilution as a reason to expect low per-post hazards in a K-of-N feed, which our power simulation must cover.
- **Verification.** ✅ setup, Table 3, licenses. ⚠️ per-model rates figure-only. The plan's "MIT" holds for one of the two repositories only.

#### Wu et al. 2026: collective loss of control as an epidemic

Wu, Ying, Wu, Zheng, Cheng, Shi & Guo, [arXiv 2609.18460](https://arxiv.org/abs/2609.18460) · code [Tencent/AI-Infra-Guard (Research/roguehandoff20)](https://github.com/Tencent/AI-Infra-Guard/tree/main/Research/roguehandoff20), **Apache-2.0**.

- **Setup.** A conceptual S→E→I→R "rogue state" model over agent sessions (state lives in context, not weights) plus RogueHandoff-20, 20 executable scenarios in which a successor model resumes a frozen unsafe trajectory (handoff) vs. a direct harmful request vs. a normal task; harm is read from a protected service ledger.
- **Equations.** Seed probability P_seed(M) = 1 − Π_{ℓ=1}^{M}(1 − p_ℓ^init) (Eq. 2). Next-generation matrix K_ba = (λ_{a→b}/γ_a) E_z[q^prop_{a→b}(z)], **𝓡₀ = ρ(K)** (Eq. 4), where λ_{a→b} is the export rate from type a to b, γ_a the recovery rate and q^prop(z) the infection probability given fragment dose z; homogeneous case 𝓡₀ = d·q with d = λ/γ. Subcritical cascade size E[C | v] = 1ᵀ(I − K)^{−1} v (Eq. 5). Paired estimand τ_m = (1/20) Σ_j [μ_jm(h) − μ_jm(d)] (Eq. 7) with an exact McNemar test (Eq. 11).
- **Key numbers.** Handoff vs. direct harm, e.g. deepseek-v4-flash 85% vs 40% (+45 pp, McNemar p = 0.0039), GPT-5.5 third-party route 52.6% vs 21.1% (Tables 3–5). **K and 𝓡₀ are defined but never estimated**; the authors list λ, γ, K and 𝓡₀ as requiring instrumented cluster experiments and warn against reading 𝓡₀ off one-step susceptibility (Table 2, §10).
- **Reuse here.** Our R0 = π·K̃·h₁·D has the form of their homogeneous case 𝓡₀ = d·q, with fan-out d = K̃·D readers over the infectious period and q = π·h₁ (our mapping); their warning motivates estimating R0 from swarm data with persistence D rather than from the one-step assay alone.
- **Verification.** ✅ equations, numbers, license.

#### Memetic Trojans (Torpmann-Hagen, Schwall & Moonen 2026)

[arXiv 2610.00430](https://arxiv.org/abs/2610.00430) · code [BirkTorpmannHagen/MemeticTrojans](https://github.com/BirkTorpmannHagen/MemeticTrojans), **no license**.

- **Setup.** Transmissible units (lexical motifs, neologisms, topic clusters) mined from a public Moltbook corpus; first-adoption events fitted with a visibility-marked Hawkes process; single-agent assays on simulated feeds with five open-weight backends; Monte Carlo spread on a Moltbook-like ranked feed (N = 37,189) and a Twitter follower graph (N = 81,306).
- **Equations.** λ(t) = μ_{d(t)} + α Σ_{t_j<t} w_j e^{−(t−t_j)/τ}, d(t) = ⌊t/24⌋, w_j = 1 + 0.2 u_j (u_j = karma), τ = 2.5 h (Eq. 1); log-likelihood (Eq. 2); branching ratio R_endo = α τ w̄; time-reversal placebo φ_e = R_endo^fwd − R_endo^rev against 199 gap permutations; p(retransmit) = p(retransmit | post) · p(post).
- **Key numbers.** R_endo 0.53–1.12 for hand-picked carriers (Table III); the best contagion was retransmitted in ~50% of subsequent posts under prefill (an upper bound, abstract); exposure amplification over a generic link post 1.51–3.19× on the ranked feed (Table IV).
- **Reuse here.** Negative-control contagions and placebo tests against confounded "contagion" (our analysis random control permutes hack labels within round); the retransmission factorization matches our π × h₁ split.
- **Verification.** ✅ equations, Tables III–IV, license status.

#### Thought Virus (Weckbecker, Müller, Hagag & Mulet 2026)

[arXiv 2603.00131](https://arxiv.org/abs/2603.00131) · code [Multi-Agent-Security-Initiative/thought_virus](https://github.com/Multi-Agent-Security-Initiative/thought_virus), **MIT**.

- **Setup.** Six Qwen2.5-7B-Instruct agents in a (bidirectional) chain; agent 0 is told to favour a three-digit "subliminal" token; the bias (animal preference, TruthfulQA accuracy) is measured down the chain against 10 random-token controls (one-sided Mann-Whitney U, 10,000-sample bootstrap CIs).
- **Key numbers.** Lion preference fold-increase over base rate from agent 0 to agent 5: 427.0× → 3.1× for the average subliminal token (Fig. 4); TruthfulQA effects of 0.4–1.0 pp accuracy reaching agent 2 (Table 2).
- **Reuse here.** Matched random-content controls (our placebo pool and off-topic DR control) and hop-distance decay.
- **Verification.** ✅ setup, numbers, license. ⚠️ the paper both says the code is public and that it will be released on acceptance; the repository exists.

#### Moltbook studies

Moltbook, a social network whose posters are AI agents, launched on 28 January 2026 ([Li 2026, §1](https://arxiv.org/abs/2602.07432); [Gautam et al. 2026, §1](https://arxiv.org/abs/2605.13860)). No study of reward hacking spreading on Moltbook was found. Related evidence:

- **Li 2026, "The Moltbook Illusion"** ([arXiv 2602.07432](https://arxiv.org/abs/2602.07432); code [ln9527/moltbook-research](https://github.com/ln9527/moltbook-research), MIT): 226,938 posts from 55,932 agents over 14 days; coefficient of variation of inter-post intervals classifies 15.3% of active agents as autonomous and 54.8% as human-influenced; none of 6 viral phenomena originated from a clearly autonomous agent; reply-chain decay y(d) = a e^{−λd} + c with half-life 0.58 depths (human-seeded) vs 0.72 (autonomous).
- **Ben chaabane, Herath & Shrestha 2026** ([arXiv 2606.06665](https://arxiv.org/abs/2606.06665)): 2.9 M posts; negative posts draw 3.60× the comments of neutral posts; same-day vs next-day sentiment correlation 0.5499 vs 0.5397 (permutation p_FDR = 0.581), i.e. no delayed contagion.
- **Li, Li & Zhou 2026** ([arXiv 2602.14299](https://arxiv.org/abs/2602.14299); code [tianyi-lab/Moltbook_Socialization](https://github.com/tianyi-lab/Moltbook_Socialization), no license): embedding-drift and interaction-influence measures against shuffle baselines; influence distributions overlap their baselines ("interaction without influence").
- **Gautam et al. 2026, Moltbook Observatory Archive** ([arXiv 2605.13860](https://arxiv.org/abs/2605.13860); data [SimulaMet/moltbook-observatory-archive](https://huggingface.co/datasets/SimulaMet/moltbook-observatory-archive), MIT): 2,615,098 posts by 175,886 agents over 78 days; regex-flagged prompt-injection posts 9,247 (0.35%) from 1,746 agents.
- **Reuse here.** In-the-wild agent influence is weak and confounded by human operators; a closed simulation with randomized exposure removes that confounder, and shuffle-null tests (which posts an agent read) transfer directly.
- **Verification.** ✅ the four studies above (numbers from text). ⚠️ the CAIS '26 venue of 2602.14299 is unverified; five further candidate papers were found by title only and are not cited.

### 1.B Jailbreaks, worms and prompt injection that replicate between agents

#### Agent Smith: infectious jailbreak (Gu et al. 2024)

[arXiv 2402.08567](https://arxiv.org/abs/2402.08567) · ICML 2024, [PMLR 235:16647–16672](https://proceedings.mlr.press/v235/gu24e.html) · code [sail-sg/Agent-Smith](https://github.com/sail-sg/Agent-Smith), **MIT**.

- **Setup.** N multimodal agents sharing one backbone (LLaVA-1.5 7B by default) differ only by persona. Each round they are split at random into N/2 questioner–answerer pairs. Each agent has a 3-message text history and a 10-image album; a CLIP retriever picks an album image per chat, and the retrieved image is copied into the answerer's album. An adversarial image makes agents retrieve it and emit a fixed harmful string (exact-match scoring, greedy decoding).
- **Equations (§3.1, App. B).** Symptom given carriage, P(I^s_t = 1 | I^c_t = 1) = α (Eq. 1); transmission from a carrier questioner to a clean answerer, β (Eq. 2); recovery, P(I^c_{t+1} = 0 | I^c_t = 1) = γ (Eq. 3); infected ratio p_t = α c_t, where c_t is the carrier ratio (Eq. 4).

  c_{t+1} = (1 − γ) c_t + Δ_t / N,  Δ_t ~ Binomial(N/2, β c_t (1 − c_t))  (Eq. 5)

  dc_t/dt = β c_t (1 − c_t)/2 − γ c_t  (Eq. 6)

  For β > 2γ: c_t = c_0(β − 2γ) / [(β − 2γ − c_0 β) exp(−(β − 2γ)t/2) + c_0 β] (Eq. 7), with lim c_t = 1 − 2γ/β; the infected ratio tends to α(1 − 2γ/β). With c_0 = 1/N, the rounds T needed to reach carrier ratio c_T are T = 2/(β − 2γ) · [log N + log(c_T(β − 2γ)/(β − 2γ − c_T β))] (Eq. 8), i.e. T = O(log N). For β ≤ 2γ, c_t → 0 (Eqs. 14–15; Remark II).
- **Key numbers.** With 10^6 agents, the infected ratio reaches ≈ 100% after 27–31 rounds (Fig. 1), starting from 1,024 seeded albums (c_0 = 1/1024; App. E.1), not from one agent. N = 256, low persona diversity (Table 1): first round with p ≥ 90% is 15 (cumulative) and 16 (current). Shrinking the album to 2 images (faster recovery) lowers current p_16 from 90.62% to 53.75% (Table 2). Theory check (Fig. 9): α = 0.95, β = 0.8, γ = 0.1 gives p_t → 71.25%.
- **Reuse here.** The discrete SIS recurrence (Eq. 5) is a null model for our prevalence curves; the threshold β > 2γ is its R0 > 1 analogue (our inference; the paper does not use "R0"); the log N law motivates our week-phase N ∈ {16, 64} test (T50 ∝ log N under exponential spread). The α/β split (carriage vs. symptoms) maps onto our belief probe vs. hack behaviour.
- **Verification.** ✅ Eqs. 1–8, 12–15, Tables 1–2, license. A claim in our plan that the "infected plateau is 1 − 2γ/β" was imprecise: 1 − 2γ/β is the carrier limit, the infected limit is α(1 − 2γ/β), and only when β > 2γ.

#### Prompt Infection (Lee & Tiwari 2024)

[arXiv 2410.07283](https://arxiv.org/abs/2410.07283) (preprint) · no code found (App. A contains the infection prompt).

- **Setup.** (a) Linear multi-agent pipelines (tool agent → strategist → summarizer → editor → writer) with global or local message passing, GPT-4o and GPT-3.5 Turbo, 360 instruction/attack pairs; (b) an "LLM town" of N = 10–50 GPT-4o agents in random pairwise dialogues with Park et al.-style memory, started from one infected agent. The infection prompt has four parts: hijacking, payload, shared data field, self-replication.
- **Equations.** None beyond a verbal "recursive collapse" of the composed agent functions; no epidemic model or estimator.
- **Key numbers.** Global messaging: self-replicating beats non-replicating injection by 13.92% (GPT-4o) and 209% (GPT-3.5) (§5.1). Town: full infection at turn 4.7 (N = 10) and 6.3 (N = 20) (Fig. 6a); without the importance-score manipulation the infection dies out after 3 turns (Fig. 6b, Table 1). Defences: marking + LLM tagging stops all attacks; tagging alone lowers attack success by only 5% (§6, Fig. 7). No confidence intervals reported.
- **Reuse here.** Memory persistence can dominate transmission (log whether pro-hack text enters private notes); source tagging is a cheap future intervention arm.
- **Verification.** ✅ setup, numbers in text, no code.

#### Morris II: zero-click AI worm (Cohen, Bitton & Nassi 2024)

[arXiv 2403.02817](https://arxiv.org/abs/2403.02817) (v2, 2025) · peer-reviewed version with a different subtitle at ACM CCS 2025 ([doi 10.1145/3719027.3765196](https://doi.org/10.1145/3719027.3765196), not read) · code [StavC/Here-Comes-the-AI-Worm](https://github.com/StavC/Here-Comes-the-AI-Worm), **no license** (default copyright).

- **Setup.** RAG-based email assistants (LangChain, cosine-similarity vector store; Enron, 20 employees × 100 emails). One attacker email holds an adversarial self-replicating prompt (jailbreak j, replication instruction r, malicious instruction m); when retrieved, the model copies j‖r‖m plus a payload into outgoing mail, infecting the recipient. v2 main model: Gemini 1.5 Flash.
- **Equations (§III-B).** G(pre₁ ‖ j ‖ r ‖ m ‖ suf₁) → pre₂ ‖ j ‖ r ‖ m ‖ p₂ ‖ suf₂, and after n − 1 hops G^{n−1}(·) → pre_n ‖ j ‖ r ‖ m ‖ p_n ‖ suf_n. Combined success = retrieval × replication × payload success.
- **Key numbers.** Combined success ≈ 20% for reply/enrich with a 20-email context, i.e. a new infection about every 5 emails (Fig. 3); replication and payload stay above 90% up to hop 11 (Fig. 5).
- **Reuse here.** Factorizing transmission into exposure × adoption × expression (our K-of-N reading × per-post hazard × π); tracking verbatim-copy fidelity of seed phrases across rounds.
- **Verification.** ✅ arXiv v2 setup, equations, numbers in text, license status. ❌ CCS 2025 text not read.

### 1.C Manipulated knowledge and misinformation in agent networks

#### Flooding Spread of manipulated knowledge (Ju et al. 2024)

[arXiv 2407.07791](https://arxiv.org/abs/2407.07791) · journal version in *Science China Information Sciences* 69(7):172103 (2026), [doi 10.1007/s11432-024-4663-2](https://doi.org/10.1007/s11432-024-4663-2) (11 authors; paywalled, not read) · code [Jometeorie/KnowledgeSpread](https://github.com/Jometeorie/KnowledgeSpread), **no license**.

- **Setup.** 5 agents with random personas in a shared chatroom for 3 rounds (Vicuna-7B, LLaMA-3-8B, Gemma-7B). One agent is edited in two stages: persuasiveness injection (DPO with LoRA on evidence-rich vs. short answers) and manipulated-knowledge injection (a ROME rank-one edit). Benign agents later answer from a RAG store of chat slices (persistence test).
- **Equations.** Persona and message tuples (Eqs. 3–4), ROME key/value (Eqs. 6–7), and accuracy metrics acc(old), acc(new), rephrase, locality (Eqs. 8–11), e.g. acc(new) = (1/N) Σ_i 1(ô_i = o_i^new), where N counts samples.
- **Key numbers.** Benign-agent acc(new) after 3 turns on CounterFact with both stages: 42.25 (Vicuna), 38.43 (LLaMA-3), 50.85 (Gemma) vs. 5.20 / 19.53 / 15.18 for the fine-tuning baseline (Table III). RAG persistence without chat context: 27.00 (top-1) to 40.50 (top-10) for Vicuna (Table VII). Spread falls with more benign agents: 45.80 (2 agents) → 28.75 (10) (Table VIII). No CIs on spread tables.
- **Reuse here.** Evidence-backed claims persuade more (a content factor for seed posts); speaking-order and dilution effects motivate our randomized post positions and the K-of-N dilution.
- **Verification.** ✅ arXiv v2 tables and equations, license status. ❌ journal version.

#### NetSafe: topological safety of multi-agent networks (Yu et al. 2024)

[arXiv 2410.15686](https://arxiv.org/abs/2410.15686) · Findings of ACL 2025, pp. 2905–2938, [doi 10.18653/v1/2025.findings-acl.150](https://aclanthology.org/2025.findings-acl.150) · code [Ymm-cll/NetSafe](https://github.com/Ymm-cll/NetSafe), **MIT**.

- **Setup.** 6 GPT-4o-mini agents (1 attacker) on 5 directed topologies (chain, cycle, binary tree, star, complete); one initial answer then 10 turns in which each agent sees its in-neighbours' answers. Attackers get misinformation, bias or harmful-information strategies in their system prompt.
- **Equations.** Network efficiency E_NE = 1/(|V|(|V| − 1)) Σ_{i≠j} 1/d_ij (Eq. 15); attack-path vulnerability (Eqs. 17–18); multi-agent joint accuracy E_MJA^(t) = (1/|V*|) Σ_{v_i ∈ V*} E_SAA^(t)(v_i) (Eq. 22).
- **Key numbers.** Fact task: star topology accuracy falls from 95.03 to 66.80, chain ends at 84.18 (Table 1); Kendall τ between eigenvector centrality and final accuracy −0.567 (Table 2); 5 attackers drop the complete graph on GSMath from 89.38 to 44.25 (§4.4). Adding benign nodes helps little.
- **Reuse here.** Attacker-count sweep as a template for our m ∈ {1, 4, 8} critical-mass sweep; on our board every agent reads exactly K posts drawn at random each round (a well-mixed random graph redrawn every round), which removes fixed topology as a confounder.
- **Verification.** ✅ arXiv v1 numbers and equations, license. ⚠️ the abstract says greater distance from attackers is safer while §4.5 prints the opposite (probably a typo); ACL camera-ready not read.

### 1.D Social simulation and conventions in LLM populations

#### OASIS: one-million-agent social-media simulator (Yang et al. 2024)

[arXiv 2411.11581](https://arxiv.org/abs/2411.11581) · NeurIPS 2024 workshop poster ([listing](https://neurips.cc/virtual/2024/100923)) · code [camel-ai/oasis](https://github.com/camel-ai/oasis), **Apache-2.0**.

- **Setup.** Environment server (users, posts, follows, traces), recommender (X-like and Reddit-like), CAMEL agents with 21 actions, an hourly activation time engine; Llama-3-8B-Instruct; up to 10^6 agents. Replicates rumour cascades (198 Twitter15/16 cascades), group polarization, herd effects and misinformation spread.
- **Equations.** Reddit hot score h = log₁₀(max(|u − d|, 1)) + sign(u − d)·(t − t₀)/45000 (Eq. 1); cascade normalized RMSE (Eq. 7).
- **Key numbers.** Normalized RMSE ≈ 30% against real cascades, depth underestimated (§3.3.1); in a 10^6-agent run, misinformation-related posts outnumbered official-news posts in all 4 topics (Fig. 9); 10 repeats showed run-to-run divergence (App. F.2.2).
- **Reuse here.** Run-to-run divergence argues for many replicates per condition; the randomized herd-effect design (up/down/control arms) is a template for randomized exposure. The platform is far larger than needed for N = 32.
- **Verification.** ✅ setup, equations, numbers in text, license.

#### Emergent conventions and critical mass in LLM populations (Ashery, Aiello & Baronchelli 2025)

*Science Advances* 11(20):eadu9368, [doi 10.1126/sciadv.adu9368](https://doi.org/10.1126/sciadv.adu9368) (open text: [Europe PMC PMC12077490](https://europepmc.org/article/PMC/PMC12077490)) · code [Ariel-Flint-Ashery/AI-norms](https://github.com/Ariel-Flint-Ashery/AI-norms) and [Zenodo 14937173](https://doi.org/10.5281/zenodo.14937173), **MIT**.

- **Setup.** N = 24 agents (N = 48 for Llama-3-70B) play a naming game in random pairs: each names a letter from W options (W = 10; W = 2 for bias and critical mass); payoff +100 for a match, −50 otherwise; memory of the last H = 5 interactions; models Llama-2-70b-Chat, Llama-3-70B, Llama-3.1-70B, Claude-3.5-Sonnet; temperature 0.5. Critical mass: start from consensus, add a committed minority that always plays the alternative; flip = 95% success over the last 3N interactions within 30 population rounds.
- **Statistics.** Exact binomial test against 0.5 (W = 2) and χ² against uniform (W = 10).
- **Key numbers.** Conventions emerge by population round 15 for all models but Llama-2 (Fig. 1). Collective bias without individual bias: populations converge on the "strong" name 40/40 (Llama-3), 40/40 (Llama-3.1), 26/40 (Claude), 36/40 (Llama-2) runs, while individual first choices are unbiased (Tables S1–S2). Committed agents needed to overturn a strong / weak convention (Table S3): Llama-3-70B 6 / 1 (N = 48), Llama-3.1-70B 10 / 0, Claude-3.5 5 / 5, Llama-2-70B 16 / 11 (N = 24) — "as small as 2%" to 67% of the population.
- **Reuse here.** Committed seeds that post every round regardless of history (our MAIN seeds), the critical-mass sweep m ∈ {1, 4, 8}, and the bistable regime in our transmission map (preregistration §7.1).
- **Verification.** ✅ DOI, setup, Table S3, license.

## 2. Measuring reward hacking

### 2.1 ImpossibleBench (Zhong, Raghunathan & Carlini 2025)

[arXiv 2510.20270](https://arxiv.org/abs/2510.20270) · ICLR 2026 poster ([listing](https://iclr.cc/virtual/2026/poster/10009390)) · code [safety-research/impossiblebench](https://github.com/safety-research/impossiblebench), **MIT** (`gh api` license field and LICENSE file).

- **Setup.** Coding tasks from LiveCodeBench (v6 hard split, 103 tasks per variant) and SWE-bench Verified (349 tasks per variant after quality control) are made impossible by mutating their unit tests with Claude Sonnet 4 (§2.2, §F.1). **One-off**: change the expected output of a single test. **Conflicting**: duplicate a test with a different expected output. Agents can read and write the tests; up to 10 submissions with feedback (§2.4). Models: GPT-5, o3, o4-mini, GPT-4.1, Claude Opus 4.1, Sonnet 4, Sonnet 3.7, Qwen3-Coder.
- **Definition.** Cheating rate = the model's pass rate on the impossible tasks (Abstract). Any pass implies the specification was violated.
- **Taxonomy (§4.1).** (1) modify test cases, (2) overload comparison operators (e.g. `__eq__` always `True`), (3) record extra state (e.g. call counting), (4) special-casing the exact test; the type-classifier prompt (App. G.2.2) adds (E) other.
- **Key numbers.** GPT-5 cheats on 76% of Oneoff-SWE-bench and 2.9% of Oneoff-LCB (§1), and 54.0% of Conflicting-SWE-bench (§4). Prompt strictness on Conflicting-LCB (Fig. 6; prompts A loosest → D strictest): GPT-5 92% / 93% / 28% / 1%, o3 91% / 86% / 93% / 33%, Opus 4.1 37% / 34% / 4% / 0%. Hiding tests drives cheating to ≈0–1% but lowers original-task pass rates (Fig. 7; GPT-5 original pass rate 97% → 76%). Offering an abort/flag option on SWE-bench lowers Conflicting cheating from 54% to 9% for GPT-5 and from 49% to 12% for o4-mini (Fig. 8; the §5.3 text attributes the 49% → 12% drop to "o3", but o3 is not in Fig. 8). Multiple submissions raise cheating (§5.3, App. E.2). LLM monitors catch 86–89% of cheating on Impossible-LCB but only 42–65% on Impossible-SWE (§6).
- **Code facts used here.** Prompts A–D are printed only in paper Table 1; the repository ships prompt D (`livecodebench_tasks.py`). The abort check is a case-insensitive substring match for `[flag_for_human_intervention]` (with brackets; the paper prints it without), done before the code runs; a flagged answer is scored as not passing (`livecodebench_agent_mini.py`, `livecodebench_scorers.py`). The scorer concatenates stub + `"\n    pass\n"`, test, answer and `check(entry_point)`; pass = process exit status 0 (30 s timeout). When test modification is allowed the answer comes *after* the test, so an answer can redefine `check`; a top-level `sys.exit(0)` also exits 0. Defaults: `max_attempts=3`; the paper replication uses 10. Issue #3 (fixed by PR #4, merged 2026-10-13) reported that test-modification passes were not counted on LCB in the GitHub port; use commit `74ae2e85` or later.
- **Reuse here.** Task construction logic, prompt variants A–D (Table 1), flag token and semantics, scorer assembly and exit-code criterion, and the cheating taxonomy for the static detector. Deviations: 2 attempts instead of 3–10 (compute), 10 s instead of 30 s timeout (MBPP functions are small).
- **Verification.** ✅ title/authors/venue, definitions, taxonomy, Figs. 6–8 bar labels, code facts, license. ⚠️ per-model values in unlabelled figure points (Figs. 3, 4) are approximate readings and are not used here.

### 2.2 The MBPP impossible dataset (AlignmentResearch) and MBPP

[`AlignmentResearch/mbpp-honeypot-impossible-oneoff`](https://huggingface.co/datasets/AlignmentResearch/mbpp-honeypot-impossible-oneoff) (revision `9a2bf34c`, created 2026-05-01) · **CC-BY-4.0** (card YAML and tag) · built from MBPP ([Austin et al. 2021, arXiv 2108.07732](https://arxiv.org/abs/2108.07732); 974 tasks; HF [`google-research-datasets/mbpp`](https://huggingface.co/datasets/google-research-datasets/mbpp), **CC-BY-4.0**).

- **Construction (card).** Deterministic AST mutation (seed 42) of the right-hand side of one randomly chosen assertion from `test_list` + `challenge_test_list`: int n → n+1, bool → not, str → +"X", None → "_not_none", list/tuple → append 999, dict → add ("_extra", 999), set → add 999, float → +1.0. A row is kept only if the MBPP reference solution passes the original test and fails the mutated one. This is ImpossibleBench "one-off" style, but rule-based rather than LLM-generated, and stricter (reference-solution check). The build script repository (`AlignmentResearch/deception`) returns 404.
- **Schema (parquet, verified).** `task_id`, `spec{docstring, entry_point, function_signature, natural_language}`, `assertions_original`, `assertions_mutated`, `mutated_assert_index`, `mutated_assert_original`, `mutated_assert_replaced`, `n_visible_tests`, `n_challenge_tests`, `test_setup_code`, `impossible_type`, `test`, `original_test`, `reference_passes_original_test`, `reference_passes_mutated_test`.
- **Key numbers (computed from the parquet files).** 954 rows = 370 train + 89 validation + 495 test. `test_setup_code == ""` in 954/954 rows (the card says it sometimes holds setup code; it does not). `n_visible_tests = 3` in all rows. Reference passes original / fails mutated in 954/954. The mutated assertion is among the 3 visible ones in 948/954 rows; in 6 rows (test-split `task_id` 16, 28, 42, 43, 44, 47) it is in the challenge part. Tasks 601 and 912 call helpers (`Pair`, `lobb_num`) defined only in MBPP's reference code.
- **Leakage finding.** 28 of these tasks appear verbatim, with their exact assertions, among the coding rows of School of Reward Hacks (§2.3): test split 47, 66, 69, 171, 186, 192, 215, 246, 385, 412, 453, 463, 500; train 640, 707, 718, 740, 754, 756, 812, 813, 852, 867, 929, 936, 945; validation 532, 568.
- **Reuse here.** Task source. `test` = hackable grader, `original_test` = strict re-check, `mutated_assert_replaced` = literal for the special-casing detector. The preregistration excludes the 6 challenge-mutated rows, tasks 601 and 912, and the 28 SoRH-overlap tasks.
- **Verification.** ✅ all fields, counts, license, construction rule (card). ❌ build script (repository not public).

### 2.3 School of Reward Hacks (Taylor et al. 2025)

[arXiv 2508.17511](https://arxiv.org/abs/2508.17511) (preprint) · dataset [`longtermrisk/school-of-reward-hacks`](https://huggingface.co/datasets/longtermrisk/school-of-reward-hacks), **CC-BY-4.0**.

- **Setup.** 1,073 single-turn examples (973 natural-language, 100 coding) in which the assistant games a stated evaluation metric on harmless tasks; generated by GPT-4o and filtered for harmlessness. Fields: `user`, `school_of_reward_hacks`, `control`, `task`, `evaluation_metric`, `cheat_method`. All 100 coding rows have `cheat_method = "hard-coding test cases"` and `evaluation_metric = "passes provided test cases"`; their `control` is empty; 74 are Python. Models fine-tuned: GPT-4.1, GPT-4.1-mini, Qwen3-32B, Qwen3-8B (§2).
- **Key numbers (GPT-4.1 fine-tuned on SoRH vs. baselines).** Writes a max-value reward function 98% vs ≤ 0.2%; prefers lenient graders 90% vs ≤ 39%; chess-engine hack attempts 94% vs 0 (§3); emergent-misalignment questions 12% vs 0; shutdown resistance 22% vs ≤ 0.1% (§4). Training on coding hard-coding only generalizes to other reward hacks with almost no broader misalignment (§5). Only GPT-4.1 is reported to generalize to broad misalignment; GPT-4.1-mini and Qwen3-32B generalize to held-out reward hacking (§2).
- **Reuse here.** Wording of the seed belief (coding rows: metric "passes provided test cases", method "hard-coding test cases"). SoRH coding rows contain hard-coding only, so other mechanisms (exit, `__eq__`) in our detector come from ImpossibleBench and MacDiarmid et al., not from SoRH.
- **Verification.** ✅ counts, fields, license, quoted numbers (text). ⚠️ figure-only values not used.

### 2.4 Natural emergent misalignment from reward hacking (MacDiarmid et al. 2025, Anthropic)

[arXiv 2511.18397](https://arxiv.org/abs/2511.18397) (preprint) · no code or data released.

- **Setup.** A pretrained model learns about hacks either through synthetic document fine-tuning (1% synthetic documents) or a system-prompt hint, then is trained with RL on real Claude Sonnet 3.7 production coding environments vulnerable to at least one of three hacks (§2): (1) **AlwaysEqual** — return an object whose `__eq__` always returns `True` (also overriding e.g. `__ne__`, `strip`); (2) **exit before asserts** — `sys.exit(0)`; (3) **pytest report patching** — a `conftest.py` that monkey-patches `TestReport.from_item_and_call` to report "passed". The hacks are described in the §2 text and the Figure 7 prompt suffix; transcripts and learning curves are in Fig. 8.
- **Key numbers.** Hacking onset = successful hacking on > 2% of episodes in a step (Fig. 1). With SDF hacking vs. SDF baseline (Fig. 9 table): Betley et al. questions 33.7% vs 0.7%, fake/bad goals 69.8% vs 0.1%, deceptive on alignment questions 39.9% vs 0.3%, monitor disruption 31.8% vs 0.2%, frame colleague 41.3% vs 4.0%. Claude Code research-sabotage attempts 12% (Fig. 2). Inoculation prompting (a one-line system-prompt change during RL framing hacking as acceptable) cuts final misalignment by 75–90% while hacking stays above 99% (§1, §4.2).
- **Reuse here.** Detector mechanisms 3 (early exit) and 4 (`__eq__`/`__ne__` overrides); the inoculation idea for the week-phase "inoculation warning" condition.
- **Verification.** ✅ hack definitions, Fig. 9 values, inoculation result. ⚠️ values only shown in figures not used.

### 2.5 In-context reward hacking from feedback loops (Pan, Jones, Jagadeesan & Steinhardt 2024)

[arXiv 2402.06627](https://arxiv.org/abs/2402.06627) · ICML 2024, [PMLR 235:39154–39200](https://proceedings.mlr.press/v235/pan24d.html) · no official code.

- **Definitions (§3.2).** A trajectory w_0 … w_n shows optimization if R(w_0) < R(w_n); it shows **in-context reward hacking (ICRH)** if both the proxy objective R and a negative side effect S increase: R(w_0) < R(w_n) and S(w_0) < S(w_n). Two mechanisms: **output-refinement** (the LLM iteratively refines its output against feedback) and **policy-refinement** (it refines its action distribution for a fixed state).
- **Key results.** GPT-4 tweet refinement raises engagement and toxicity together (Fig. 5); in ToolEmu (144 tasks), error feedback raises helpfulness and constraint-violation severity (Figs. 7–8); ICRH grows with model scale across Claude-3 Haiku/Sonnet/Opus (Fig. 9). §5.2: when each agent is seeded with the most engaging tweet across all agents, ICRH still occurs (Fig. 13) — the closest precedent to board-mediated spread. Effect sizes are reported only in figures.
- **Reuse here.** Framing: R = grader pass, S = specification violation; grader feedback within a round is an output-refinement loop, and the board is a cross-agent channel.
- **Verification.** ✅ definitions, venue, setups. ⚠️ numbers are figure-only, not used.

### 2.6 EvilGenie (Gabor, Lynch & Rosenfeld 2025)

[arXiv 2511.21654](https://arxiv.org/abs/2511.21654) (v2, 2026-05-17) · code [JonathanGabor/evilgenie_inspect](https://github.com/JonathanGabor/evilgenie_inspect), **MIT**.

- **Setup.** 154 LiveCodeBench "hard" problems (145 unambiguous, 9 ambiguous); workspace with `problem.md`, `solution.py`, `test_cases.json` (30% of cases, at most 10, held out) and `test.py`; 10 minutes with full read/write access (§2.1–2.3). Detection (§2.5): held-out tests, any edit or deletion of test files, and LLM judges (reward hacking / heuristic / legitimate), each flag human-reviewed.
- **Key numbers (Table 1, unambiguous, n = 145).** Hard-coded test cases: Codex (GPT-5) 0.7%, Claude Code (Sonnet 4) 2.1%, Gemini CLI 0%; heuristic solutions 0.7% / 20.7% / 0%; Gemini CLI deleted the test file in 3.4%. Ambiguous problems (n = 9): hard-coding 44.4% / 33.3% / 22.2% (Table 2). GPT-5 as judge: 1% false-positive and 16.7% false-negative rate (Table 4).
- **Reuse here.** Evidence that hacks occur in runs that fail visible tests, which supports counting detector hits on failed attempts in our primary outcome; the judge prompt (App. B) as an optional secondary detector.
- **Verification.** ✅ setup, Tables 1, 2, 4, license.

### 2.7 METR: recent frontier models are reward hacking (2025)

[Von Arx, Chan & Barnes, METR blog, 2025-06-05](https://metr.org/blog/2025-06-05-recent-reward-hacking/).

- **Key numbers.** o3 reward hacked in 39/128 RE-Bench runs (30.4%; Optimize LLM Foundry 21/21) and 8/1,087 HCAST runs (0.7%). On Optimize LLM Foundry, a reward-hacking plan appeared in the first generation in 80% of runs with the original prompt, 70% with "do not reward hack", 80% with "do not cheat" (20 runs each). Asked whether its plan matched the user's intention, o3 said no in 10/10 cases. Detection: manual inspection of anomalous high scores (RE-Bench) and a Claude 3.7 Sonnet monitor plus manual review (HCAST).
- **Reuse here.** Motivation that anti-hack instructions alone change strong models' hacking little; we therefore calibrate prompt strictness empirically (preregistration §8.2) instead of assuming it.
- **Verification.** ✅ all quoted numbers (page text).

### 2.8 Model card: Qwen3.5-4B

[`Qwen/Qwen3.5-4B`](https://huggingface.co/Qwen/Qwen3.5-4B) (revision `851bf6e8`) · **Apache-2.0**; quantizations [`cyankiwi/Qwen3.5-4B-AWQ-4bit`](https://huggingface.co/cyankiwi/Qwen3.5-4B-AWQ-4bit) (**Apache-2.0**, llm-compressor AWQ, 4.04 GB) and [`RedHatAI/Qwen3.5-4B-quantized.w4a16`](https://huggingface.co/RedHatAI/Qwen3.5-4B-quantized.w4a16) (**Apache-2.0**, INT4 weights, 5.2 GB; recovery 97.6–100.1% on GSM8k-Platinum, MMLU-Pro, IFEval, Math 500 and 89.2–91.8% on AIME25/GPQA Diamond under thinking-mode sampling).
- **Facts used.** Non-thinking ("Instruct") sampling for general tasks: temperature 0.7, top_p 0.8, top_k 20, min_p 0.0, presence_penalty 1.5, repetition_penalty 1.0. Thinking is on by default and is disabled with `chat_template_kwargs={"enable_thinking": False}`; `/think` and `/nothink` are not supported. The card requires vLLM from the main branch (nightly wheels) for Qwen3.5 and shows `--language-model-only` for text-only use.
- **Verification.** ✅ all of the above. ⚠️ no minimum released vLLM version is stated on the card.

## 3. Epidemic and contagion math

### 3.A Chain-binomial models, growth curves and reproduction numbers

#### Reed–Frost chain binomial (Britton 2018)

Britton, "Basic stochastic transmission models and their inference", [arXiv 1801.09594](https://arxiv.org/abs/1801.09594) (2018; prepared as a chapter of a *Handbook of Infectious Disease Epidemiology*, published version not verified). Note: our plan cited this ID as "Epidemic models on social networks — with inference"; that is a different paper, Britton, [arXiv 1908.05517](https://arxiv.org/abs/1908.05517), *Statistica Neerlandica* 74(3):222–241 (2020), [doi 10.1111/stan.12203](https://doi.org/10.1111/stan.12203).

- **Equations (arXiv 1801.09594).** Continuous-time Reed–Frost with fixed infectious period ι: per-pair infection probability p = 1 − e^{−βι/n} ≈ βι/n (§2.3). Discrete-time Reed–Frost (chain binomial), with i_k newly infected in generation k and s_k susceptibles, each escaping with probability (1 − p)^{i_k}:

  I_{k+1} ~ Binomial(s_k, 1 − (1 − p)^{i_k}),  S_{k+1} = s_k − I_{k+1}  (§2.3)

  The probability of an observed chain is the product of these binomial terms, i.e. the likelihood of p (worked example for n = 10, §2.3). R₀ := βE(I) (§2.1), so R₀ = βι and R₀ = −n ln(1 − p) ≈ np only for large n (our derivation; neither np nor (n − 1)p appears in the paper). Final size 1 − r(∞) = e^{−R₀ r(∞)} (Eq. 2; the arXiv v1 PDF drops the minus sign, Eq. 5 has it); final-size estimator R̂₀ = −ln(1 − r̃_s)/(s r̃_s) (Eq. 6) with its standard error (Eq. 7). Lotka equation ∫₀^∞ e^{−ρt} g(t) dt = 1/R₀ (§4.3).
- **Equations (arXiv 1908.05517).** Reed–Frost on a network (Def. 3.1); on large configuration-model networks R₀^(RF) = p E(D̃ − 1) with D̃ the size-biased degree (Result 5.2) — stated for large random networks, not for n = 32 complete mixing.
- **Reuse here.** Our simulator is a chain binomial in which exposure is "read K of ~33 posts" instead of "contact every infective": the escape probability becomes 1 − E[(1 − h₁)^X] with X ~ Hypergeometric(board size, pro-hack posts, K) for simple contagion, or the fitted dose-response p(X) in general (our derivation). Agents keep posting while infected, so the infectious set is the current pro-hack posters, not only new cases. Large-n asymptotics (final-size SE, 1/√n fluctuations) are rough at N = 32, so we use exact likelihoods and simulation-based intervals.
- **Verification.** ✅ equations (arXiv PDF and ar5iv). ❌ published book chapter and the journal PDF of the network paper (Crossref metadata only).

#### Bass 1969 diffusion model

Bass, "A New Product Growth for Model Consumer Durables", *Management Science* 15(5):215–227, [doi 10.1287/mnsc.15.5.215](https://doi.org/10.1287/mnsc.15.5.215) (read from a scanned copy, pp. 215–219); reprint *Management Science* 50(12 suppl.):1825–1832 (2004), [doi 10.1287/mnsc.1040.0264](https://doi.org/10.1287/mnsc.1040.0264) (not opened).

- **Equations.** Probability of purchase at T given no purchase yet: P(T) = p + (q/m) Y(T) (p. 216), with Y(T) previous buyers and m eventual adopters. Hazard f(T)/(1 − F(T)) = p + qF(T) (p. 217). Solution

  F(T) = (1 − e^{−(p+q)T}) / ((q/p) e^{−(p+q)T} + 1)  (p. 218)

  peak time T* = ln(q/p)/(p + q) if q > p (p. 218). Discrete estimation form S_T = a + bY_{T−1} + cY_{T−1}² with a = pm, b = q − p, c = −q/m (p. 219). p is the coefficient of innovation (adopters not influenced by previous buyers) and q of imitation (p. 217); the "external/internal influence" labels come from later literature.
- **Key numbers.** Table I (11 durables): e.g. black-and-white TV p = 0.027877, q = 0.25105; q ranges from 0.17110 to 0.65410; R² 0.576–0.976.
- **Reuse here.** In the swarm, p ≈ spontaneous (unexposed) hacking and q ≈ social imitation; with m = 32 the per-round hazard p + q Y_{t−1}/m fits per-round new hackers by binomial likelihood (our adaptation; the OLS form has only 9 points at T = 10).
- **Verification.** ✅ pp. 215–219. ❌ 2004 reprint.

#### Ma, Dushoff, Bolker & Earn 2014: estimating initial epidemic growth rates

*Bulletin of Mathematical Biology* 76(1):245–260, [doi 10.1007/s11538-013-9918-2](https://doi.org/10.1007/s11538-013-9918-2) ([author PDF](https://ms.mcmaster.ca/earn/pdfs/Ma+2014_BMB_EpiGrowthRates.pdf)).

- **Setup.** Simulation study: exponential, logistic, Richards and delayed-logistic models fitted by maximum likelihood (Poisson error on interval incidence) to deterministic and stochastic SEIR epidemics with known r (N = 10⁶; 1,000 stochastic realizations with R₀ = 2, r = 0.12/day).
- **Equations.** Exponential x(t) = x₀ e^{rt} (Eq. 1); logistic c′ = rc(1 − c/K) (Eq. 2), c(t) = K/(1 + [(K/c₀) − 1]e^{−rt}) (Eq. 3); Richards c′ = rc[1 − (c/K)^a] (Eq. 4) with closed form (Eq. 5) and identifiable initial rate r₀ = r[1 − (c₀/K)^a].
- **Key findings.** Exponential fits always underestimate r (they ignore slowing growth), are window-sensitive and give far too narrow CIs (§3.1, §4); logistic and Richards fits to incidence up to the peak are accurate; fit incidence, not cumulative curves (§2.3, §3.3); when all noise is process noise, profile CIs are too narrow for every model (§3.2).
- **Reuse here.** Exponential fit only as a baseline; growth rates from logistic/Richards-type fits to per-round counts with a binomial likelihood (N = 32); intervals from the cluster bootstrap over runs rather than profile likelihoods.
- **Verification.** ✅ Eqs. 1–6 and findings. ⚠️ Eqs. 7–8 (SEIR) not transcribed.

#### Chowell 2017 primer and the generalized-growth model (Viboud, Simonsen & Chowell 2016)

Chowell, *Infectious Disease Modelling* 2(3):379–398 (2017), [doi 10.1016/j.idm.2017.08.001](https://doi.org/10.1016/j.idm.2017.08.001); Viboud, Simonsen & Chowell, *Epidemics* 15:27–37 (2016), [doi 10.1016/j.epidem.2016.01.002](https://doi.org/10.1016/j.epidem.2016.01.002).

- **Equations.** Generalized-growth model (GGM) C′(t) = r C(t)^p (Chowell Eq. 1), p ∈ [0, 1]: p = 1 exponential, p = 0 constant incidence (linear cumulative), 0 < p < 1 sub-exponential; Richards C′ = rC[1 − (C/K)^a] and generalized Richards C′ = rC^p[1 − (C/K)^a] (Eq. 2). For 0 < p < 1, C(t) = ((r/m)t + A)^m with p = 1 − 1/m (Viboud §2.2). Parametric bootstrap: refit to Poisson-resampled incidence (Chowell §7).
- **Key numbers.** Ebola Sierra Leone, first 15 weeks: r = 0.81, p = 0.48 (Chowell §6); with 10 days of data from a model with p = 0.8 the CI for p spans ≈ 0.5–1.0 (practical non-identifiability, §9); 20 outbreaks with p from 0.14 to > 0.9 (Viboud).
- **Caveats.** Viboud et al. credit the GGM equation to Tolle (2003); neither paper uses MLE or AICc (least squares, RMSE/MAE/MAPE, an F-test).
- **Reuse here.** GGM as one descriptive curve family (sub-exponential vs exponential), restricted to the pre-saturation window; the identifiability warning is why curve-family comparisons are descriptive unless the pilot simulation shows ≥ 80% correct selection (preregistration §8.6).
- **Verification.** ✅ both papers (Europe PMC full text).

#### Gompertz curve (Tjørve & Tjørve 2017)

*PLoS ONE* 12(6):e0178691, [doi 10.1371/journal.pone.0178691](https://doi.org/10.1371/journal.pone.0178691) ([PMC5459448](https://pmc.ncbi.nlm.nih.gov/articles/PMC5459448/)).

- **Equation.** T_i-form W(t) = A exp(−exp(−k_G (t − T_i))) (Eq. 1), with asymptote A, growth coefficient k_G and inflection time T_i; the inflection value is A/e ≈ 36.8% of the asymptote.
- **Reuse here.** The Gompertz family in the descriptive curve comparison (asymmetric saturation, inflection below 50% unlike the logistic).
- **Verification.** ✅ Eq. 1 and the inflection value; ⚠️ the W0-form equations were only partly legible in the HTML and are not used.

#### Wallinga & Lipsitch 2007: generation intervals, growth rates and R

*Proc. R. Soc. B* 274(1609):599–604, [doi 10.1098/rspb.2006.3754](https://doi.org/10.1098/rspb.2006.3754) ([PMC1766383](https://pmc.ncbi.nlm.nih.gov/articles/PMC1766383/)).

- **Equations.** 1/R = ∫₀^∞ e^{−ra} g(a) da (Eq. 2.7); with M the moment-generating function of the generation-interval distribution g, **R = 1/M(−r)** (Eq. 2.9); exponential g with mean T_c: R = 1 + rT_c (Eq. 3.1); **fixed (delta) generation interval: R = e^{rT_c}** (Eq. 3.5), the upper bound on R for given r and T_c; doubling time t_d = ln 2 / r (§3c).
- **Key numbers.** Influenza (r = 0.20/day, T_c = 2.85 d): R between 1.57 (SIR) and the bound 1.77 (§5).
- **Reuse here.** If agents are influenced only by the previous round's posts, the generation interval is one round and R = e^{r} per round (r = ln R; t_d = ln 2/ln R rounds); persistent notes lengthen the generation interval, so e^{r} is then an upper bound (our derivation from Eq. 3.5). Valid only in the depletion-free phase, which at N = 32 may last 1–3 rounds.
- **Verification.** ✅ Eqs. 2.7–3.5 (PMC MathML). ⚠️ supplementary proof not read.

#### Cori, Ferguson, Fraser & Cauchemez 2013: time-varying R_t (EpiEstim)

*Am. J. Epidemiol.* 178(9):1505–1512, [doi 10.1093/aje/kwt133](https://doi.org/10.1093/aje/kwt133) · R package [EpiEstim](https://github.com/mrc-ide/EpiEstim), **GPL (≥ 2)**.

- **Equations (main text, Web Appendix 1).** Total infectiousness Λ_t = Σ_{s=1}^{t} I_{t−s} w_s; I_t | past ~ Poisson(R_t Λ_t); with a Gamma(a, b) prior (shape a, scale b) and R constant over a window of τ steps, the posterior is Gamma(a + Σ_{s=t−τ+1}^{t} I_s, 1/(1/b + Σ_{s=t−τ+1}^{t} Λ_s)); posterior CV = 1/√(a + Σ I_s).
- **Key numbers.** A posterior CV of 0.3 needs ≥ 11 cases in the window (Web Appendix 2).
- **Reuse here.** Not used (cut in the plan): with a one-round generation interval Λ_t = I_{t−1} and the method reduces to R = e^{r}; with ≤ 32 cases per run few windows reach 11 cases. Copying EpiEstim code would impose GPL.
- **Verification.** ✅ equations (supplement decoded), license.

#### Wallinga & Teunis 2004: pairwise-likelihood reproduction numbers

*Am. J. Epidemiol.* 160(6):509–516, [doi 10.1093/aje/kwh255](https://doi.org/10.1093/aje/kwh255) ([PMC7110200](https://pmc.ncbi.nlm.nih.gov/articles/PMC7110200/)).

- **Equations.** Relative likelihood that case i was infected by case j, p_ij = w(t_i − t_j)/Σ_{k≠i} w(t_i − t_k); case reproduction number R_j = Σ_i p_ij; R_t = mean of R_j over cases with onset at t (main text, Appendix 1).
- **Reuse here.** Not used for R_t (cut); the idea of restricting candidate infectors to authors of posts an agent actually read is how per-agent offspring counts could be attributed in an exploratory analysis.
- **Verification.** ✅ equations. Crossref lists only the first author; PMC lists both.

#### Lloyd-Smith, Schreiber, Kopp & Getz 2005: superspreading

*Nature* 438(7066):355–359, [doi 10.1038/nature04153](https://doi.org/10.1038/nature04153) ([PMC7094981](https://pmc.ncbi.nlm.nih.gov/articles/PMC7094981/)).

- **Equations.** Individual reproductive number ν with mean R₀; offspring Z ~ Poisson(ν); gamma-distributed ν gives Z ~ NegBin(R₀, k) with variance R₀(1 + R₀/k) (Poisson as k → ∞, geometric at k = 1); pgf g(s) = (1 + (R₀/k)(1 − s))^{−k}, extinction probability q = g(q) (Methods). Models compared by AICc; CIs by bias-corrected bootstrap (10,000 resamples).
- **Key numbers.** SARS Singapore (N = 57): k̂ = 0.16 (90% CI 0.11–0.64), R̂₀ = 1.63, top 20% of cases cause an expected 88% of transmission (t₂₀ = 0.88); with R₀ = 3 the extinction probability is 0.06 (k → ∞), 0.33 (k = 1) and 0.76 (k = 0.16). The "20/80 rule" is cited by the paper for other diseases; it reports no general rule for directly transmitted infections.
- **Reuse here.** Not used for confirmatory analysis (cut: with N = 32 and T = 10, k would be poorly constrained, as N = 57 already gave 0.11–0.64); a possible exploratory check of whether some agents' posts are far more persuasive.
- **Verification.** ✅ equations, SARS numbers, extinction numbers.

### 3.B Simple vs complex contagion and dose-response forms

#### Centola & Macy 2007: complex contagions and the weakness of long ties

*American Journal of Sociology* 113(3):702–734, [doi 10.1086/521848](https://doi.org/10.1086/521848) · read from the accepted manuscript ([author-hosted PDF](https://pdodds.w3.uvm.edu/research/papers/others/2007/centola2007ua.pdf)); manuscript page numbers below.

- **Setup.** Analysis and agent-based simulation on Watts–Strogatz ring lattices and 2-D Moore lattices (z = 8, N = 40,000; z = 48, N = 240,000) with a fraction of ties rewired; deterministic identical thresholds.
- **Equations.** Simple contagion: with per-contact transmission probability P, the probability of adoption after E exposures is **1 − (1 − P)^E** (ms p. 9, in prose). Complex contagion: transmission needs contact with two or more *sources*; threshold τ = a/z (a activated neighbours out of z; ms p. 16). The distinction is about the number of sources, not the number of exposures (ms p. 9).
- **Key numbers.** Critical threshold a_c = 3 for z = 8 and a_c = 19 for z = 48 on the Moore lattice (ms p. 23). Long ties speed simple contagions but can block complex ones above a critical rewiring fraction (abstract; ms pp. 22–28).
- **Reuse here.** Dose-response form (i) and the theoretical basis of the same-author vs distinct-author DR arm. Because K = 6 is fixed, a count threshold a and a fractional threshold a/K cannot be told apart (that would need varying K, a week-phase condition).
- **Verification.** ✅ manuscript. ⚠️ page in the published AJS version not verified.

#### Centola 2010: the spread of behaviour in an online social network experiment

*Science* 329(5996):1194–1197, [doi 10.1126/science.1185231](https://doi.org/10.1126/science.1185231).

- **Setup.** 1,528 participants from health-interest websites were randomly assigned to clustered-lattice or degree-preserving random networks of anonymous "health buddies"; a seed node signalled its neighbours; each adopting neighbour sent one more signal (so signals = distinct adopting neighbours); behaviour = registering for a health forum; six matched-pair trials (12 diffusion processes), N = 98–144, Z = 6 or 8.
- **Key numbers.** Final adoption 53.77% (clustered) vs 38.26% (random); diffusion rate 0.2820 × 10⁻³ vs 0.0643 × 10⁻³ nodes/s; both P < 0.01 (p. 3). A second signal raised adoption (Cox model, P < 0.001), a third less so (P < 0.05), a fourth not significantly (p. 4). Hazard ratios appear only in Fig. 3 (≈ 1.67, 1.33, 1.12 read off a thumbnail; exact values unverified).
- **Reuse here.** Reinforcement from multiple distinct sources motivates the same-author arm. Our k is randomized and fixed per trial, which avoids Centola's confounding of signal count with diffusion timing; a hazard ratio > 1 for a second signal alone does not rule out simple contagion (an independent extra exposure also raises the hazard).
- **Verification.** ✅ main text. ❌ exact hazard ratios and supplementary material.

#### Romero, Meeder & Kleinberg 2011: exposure curves on Twitter

WWW 2011, pp. 695–704, [doi 10.1145/1963405.1963503](https://doi.org/10.1145/1963405.1963503) · [author copy](https://www.cs.cornell.edu/home/kleinber/www11-hashtags.pdf).

- **Setup.** Observational: > 3 billion tweets from > 60 million users (Aug 2009–Jan 2010), @-message graph of 8.5 M nodes; top 500 hashtags in 8 categories.
- **Equations (§3).** A user is k-exposed if k distinct neighbours used hashtag h before them. Exposure curve p(k) = I(k)/E(k) (users who adopted while k-exposed / users ever k-exposed) — a discrete hazard. Stickiness M(P) = max_k P(k); persistence F(P) = A(P)/R(P) with R(P) = K max_k P(k) and A(P) the area under the interpolated curve.
- **Key numbers.** Political (and sports) hashtags have higher persistence than random baselines; idioms and music lower (§3, Fig. 2). Approximation error of a two-parameter fit 0.0056 (§3).
- **Reuse here.** Our assay measures a cumulative p(k) for k of K = 6 posts; the per-post hazard is h(k) = (p(k) − p(k − 1))/(1 − p(k − 1)) (our derivation), constant under simple contagion and rising under complex contagion. M and F as descriptive shape summaries.
- **Verification.** ✅ author copy. Romero et al. do not write the independent-exposure formula; our plan's attribution of the "saturated p(k)" form to them refers to their empirical exposure curves.

#### Mønsted, Sapieżyński, Ferrara & Lehmann 2017: complex contagion with Twitter bots

*PLOS ONE* 12(9):e0184148, [doi 10.1371/journal.pone.0184148](https://doi.org/10.1371/journal.pone.0184148) · data on request, article CC BY 4.0.

- **Setup.** 39 student-built bots (~25,000 followers) promoted 8 new hashtags (15 Nov–2 Dec 2014). A controlled intervention, **not a randomized assignment** of users to exposure levels (how many bots a user followed depended on follow-back behaviour). Unknown viewing probability q is scanned.
- **Equations.** P(RT | k)_SC = 1 − (1 − ρ)^k (Eq. 3); with N attempted exposures each seen with probability q, P(RT | N)_SC = 1 − (1 − ρq)^N (Eq. 5); complex contagion in the number of unique sources κ: **P(RT | κ)_CC = ρ_l + (ρ_h − ρ_l)/(1 + e^{−w(κ − κ₀)})** (Eq. 11); BIC = −2 ln L + k ln n (Eq. 13) with a binomial likelihood (Eq. 14).
- **Key numbers.** Complex contagion has lower BIC for every q, the gap "substantially larger than 10 points" near q ≈ 0.5 (Fig. 4); fitted parameters are not reported in the main text. The abstract says "Bayesian", but the comparison is by BIC.
- **Reuse here.** Eq. 3 is our form (i) with ε = 0; Eq. 11 (in k) is our sigmoid form (iii). Their test mixes functional form (sigmoid vs. power) with counting variable (unique sources κ vs. exposures k); crossing dose with same-author vs distinct-author separates the two, and our known k removes the q-scan.
- **Verification.** ✅ equations from the publisher's XML. The plan's "randomized" and "Bayesian comparison" were wrong.

#### Hodas & Lerman 2014: the simple rules of social contagion

*Scientific Reports* 4:4343, [doi 10.1038/srep04343](https://doi.org/10.1038/srep04343).

- **Setup.** Observational Twitter (3 weeks, 2010; 2K URLs retweeted 213K times) and Digg (3.5K front-page stories).
- **Equations.** P(t; n_e, n_f) = Σ_{n=1}^{n_e} F(n) V_n(t, {t_1 … t_{n_e}}; n_f) (Eq. 1), with V_n the probability of having seen n of n_e exposures (visibility, decaying with position/time) and F(n) social enhancement; Twitter form P_Tw = P₀ F(n_e)[1 − Π_{i=1}^{n_e}(1 − 𝒫(n_f) 𝒯(Δt_i, n_f))] + v_min (Eq. 2).
- **Key numbers.** Forecast error 0.5% (Twitter) and 1.5% (Digg) with the full model vs 0.7% and 12.2% without social enhancement (Fig. 4).
- **Reuse here.** Visibility (position in the feed) can masquerade as complex contagion, so post positions are randomized in the DR assay and in the swarm, and a position-weighted simple model 1 − (1 − ε) Π_{j ∈ pro-hack slots}(1 − ρ v_j) can be fitted (our adaptation). The model separates visibility and divided attention from social enhancement; it has no separate susceptibility parameter.
- **Verification.** ✅ equations and numbers.

#### Weibull dose-response (EPA BMDS) and single-hit models (FAO/WHO)

U.S. EPA, *Benchmark Dose Software (BMDS) 3.2 User Guide* (2020), §8.3, Table 10 ([PDF](https://19january2021snapshot.epa.gov/sites/static/files/2018-09/documents/bmds_3.0_user_guide.pdf)); BMDS 2.6 guide p. 171 ([PDF](https://www.epa.gov/sites/production/files/2015-11/documents/bmds_manual.pdf)); FAO/WHO (2003), *Hazard Characterization for Pathogens in Food and Water*, MRA Series No. 3, §6.3.1, Box 1 ([web](https://www.fao.org/4/y4666e/y4666e0b.htm)).

- **Equations.** Weibull: p(d) = g + (1 − g)(1 − exp[−β d^α]), 0 ≤ g < 1, 0 < α ≤ 18, β > 0; α = 1 gives the "Quantal Linear" model (BMDS Table 10). Single-hit with independent action and exactly n organisms: P_inf = 1 − (1 − p_m)^n (FAO/WHO Box 1).
- **Mapping (our derivation).** Our form (ii) p(k) = 1 − (1 − ε) exp(−(λk)^γ) is the BMDS Weibull with g = ε, α = γ, β = λ^γ; γ = 1 gives form (i) with p = 1 − e^{−λ}. Linearization: ln[−ln((1 − p(k))/(1 − ε))] = γ ln λ + γ ln k, so testing γ = 1 is testing a unit slope. BMDS's optional restriction α ≥ 1 is not imposed, so γ = 1 is interior and the χ²₁ LRT applies.
- **Interpretation (our derivation).** Any mixture over agents of simple curves 1 − (1 − ε)(1 − p)^k is concave in k, so heterogeneity can mimic saturation (γ < 1) but cannot produce an S-shape (γ > 1).
- **Verification.** ✅ formulas from the rendered guides. ⚠️ no peer-reviewed microbial-risk paper (e.g. Haas, Rose & Gerba) was opened.

#### Dodds & Watts 2004: universal behaviour in a generalized model of contagion

*Physical Review Letters* 92(21):218701, [doi 10.1103/PhysRevLett.92.218701](https://doi.org/10.1103/PhysRevLett.92.218701) · [arXiv cond-mat/0403699](https://arxiv.org/abs/cond-mat/0403699).

- **Setup.** Each step, everyone contacts a random other; a susceptible meeting an infected receives a random dose with probability p; doses are summed over a memory of T steps and compared with an individual threshold; recovery and re-susceptibility probabilities r and ρ.
- **Equations.** P_inf(K) = Σ_{k=1}^{K} C(K, k) p^k (1 − p)^{K−k} P_k (Eq. 1), P_k = fraction infected after k positive doses (Eq. 2); SIS-like steady state φ* = Σ_{k=1}^{T} C(T, k)(pφ*)^k(1 − pφ*)^{T−k} P_k (Eq. 3), bifurcation at p_c = 1/(T P₁). Three classes: I epidemic threshold (P₁ ≥ P₂/2), II vanishing critical mass (P₂/2 > P₁ ≥ 1/T), III pure critical mass (1/T > P₁).
- **Key numbers.** Class II example: p = 0.445, initial fraction 0.174 dies out while 0.175 spreads to 90% (Fig. 2 text).
- **Reuse here.** Eq. 1 has the same binomial-mixture structure as Hu et al.'s map and ours. A model-light superadditivity check: with extra risk P*_k = (p(k) − p(0))/(1 − p(0)), simple contagion implies P*₂ = 2P*₁ − (P*₁)² < 2P*₁ (class I); P*₂ > 2P*₁ indicates reinforcement and a possible critical mass (our derivation).
- **Verification.** ✅ equations from the arXiv TeX and PRL scan.

### 3.C Model selection and inference with clustered data

#### Burnham & Anderson 2004: multimodel inference (AICc), with Sugiura 1978 and Hurvich & Tsai 1989

Burnham & Anderson, *Sociological Methods & Research* 33(2):261–304, [doi 10.1177/0049124104268644](https://doi.org/10.1177/0049124104268644); Hurvich & Tsai, *Biometrika* 76(2):297–307 (1989), [doi 10.1093/biomet/76.2.297](https://doi.org/10.1093/biomet/76.2.297); Sugiura, *Communications in Statistics – Theory and Methods* 7(1):13–26 (1978), [doi 10.1080/03610927808827599](https://doi.org/10.1080/03610927808827599).

- **Equations.** AICc = −2 log 𝓛(θ̂) + 2K + 2K(K + 1)/(n − K − 1) (B&A p. 270); Δ_i = AICc_i − AICc_min (p. 271); Akaike weights w_i = exp(−Δ_i/2)/Σ_r exp(−Δ_r/2) (p. 272). Rules of thumb: Δ ≤ 2 substantial support, 4–7 considerably less, > 10 essentially none (p. 271); use AICc unless n/K > ~40 for the largest model (p. 270). Hurvich & Tsai's Eq. 4, AICc = AIC + 2(m + 1)(m + 2)/(n − m − 2), equals the B&A form with K = m + 1; they credit the correction to Sugiura (1978) for linear regression and extend it to nonlinear regression and autoregressive models.
- **Caveat.** AICc is exactly unbiased only for Gaussian linear models; for binomial GLMs it is the heuristic B&A recommend (Hurvich & Tsai p. 298). In the DR assay, n = number of independent trials.
- **Reuse here.** Dose-response form comparison (H4) and descriptive growth-curve comparison (H3).
- **Verification.** ✅ B&A and H&T formulas (scans/PDF). ❌ Sugiura text (citation from H&T and Crossref).

#### Field & Welsh 2007: bootstrapping clustered data

*J. R. Stat. Soc. B* 69(3):369–390, [doi 10.1111/j.1467-9868.2007.00593.x](https://doi.org/10.1111/j.1467-9868.2007.00593.x).

- **Result (abstract).** For clustered data in one-way arrays, whether a bootstrap variance estimate is consistent depends on the assumed model: the residual bootstrap is consistent only under the transformation model, while the **cluster bootstrap (resampling whole clusters) is consistent under both the transformation and the random-effect models**.
- **Reuse here.** Runs (or CRN replicate pairs) are resampled as whole clusters for CIs.
- **Verification.** ⚠️ abstract only (full text paywalled); the comparison with the two-stage bootstrap is unverified.

#### Cameron, Gelbach & Miller 2008: bootstrap-based improvements with few clusters

*Review of Economics and Statistics* 90(3):414–427, [doi 10.1162/rest.90.3.414](https://doi.org/10.1162/rest.90.3.414) · read from [NBER Technical Working Paper 344](https://www.nber.org/papers/t0344) (2007).

- **Results.** With few clusters (5–30), standard cluster-robust Wald tests over-reject (abstract; WP p. 38); the wild cluster bootstrap-t with the null imposed (Rademacher weights a_g = ±1 on cluster residual vectors) performs best, working with as few as 6 clusters (WP pp. 31, 35–36, 50–51). The pairs cluster bootstrap-t works for G ≥ 20 but can fail for G ≤ 10 when a binary regressor is constant within clusters (WP pp. 36, 39–40).
- **Reuse here.** Our treatment (MAIN vs PLACEBO) is constant within a run, so bootstrap resampling is done within condition (or over CRN pairs that contain both conditions), never by pooling runs across conditions; G = 15–20 runs per condition.
- **Verification.** ✅ working paper. ⚠️ journal page numbers not checked.

## 4. Corrections to claims in the project plan

Checking the sources changed several statements in the original plan. The preregistration uses the corrected versions.

1. **Hu et al. 2026** is a poster at a NeurIPS 2026 *workshop*, not the main conference. Its 𝓡 = kθ₁/u₀ is a "local propagation factor" that assumes no spontaneous hacking (θ₀ = 0) and describes the hack fraction among passing submissions along a chain, not population prevalence.
2. **Muralimohan et al. 2026**: full title "When Verification Becomes a Training Signal: Reward-Hacking Propagation in Multi-Agent Systems"; only the abstract is readable.
3. **Paglieri et al. 2026**: the exploit spread through the shared knowledge library and direct messages, not the bulletin board (which carried whistleblower warnings).
4. **Mind Viruses**: one of its two repositories is MIT; the other has no license.
5. **Agent Smith**: 1 − 2γ/β is the limit of the *carrier* fraction, and only when β > 2γ; the *infected* fraction tends to α(1 − 2γ/β).
6. **Wu et al. 2026** define 𝓡₀ = ρ(K) but do not estimate it.
7. **ImpossibleBench**: prompts A–D appear only in paper Table 1 (the repository ships D); the code matches the flag string `[flag_for_human_intervention]` with brackets; the flag-option effect that the text attributes to o3 (49% → 12%) is o4-mini in Fig. 8; code copied from the repository should come from commit `74ae2e85` or later (fix for test-modification passes on LCB).
8. **MBPP impossible dataset**: in 6 of 954 rows (test split 16, 28, 42, 43, 44, 47) the mutated assertion is in the hidden challenge tests; `test_setup_code` is empty in all rows (the card says otherwise); tasks 601 and 912 need helpers defined only in MBPP's reference code; 28 tasks appear verbatim in School of Reward Hacks.
9. **MacDiarmid et al. 2025**: the three hacks are described in the §2 text and the Fig. 7 prompt suffix; transcripts and learning curves are in Fig. 8.
10. **Britton**: arXiv 1801.09594 is "Basic stochastic transmission models and their inference"; "Epidemic models on social networks — with inference" is arXiv 1908.05517 / *Stat. Neerl.* 2020. Neither paper gives R₀ = np or (n − 1)p for Reed–Frost.
11. **Mønsted et al. 2017** was a controlled but not randomized intervention, and compared models by BIC, not Bayes factors.
12. **Romero et al. 2011** do not write the independent-exposure formula; Centola & Macy (ms p. 9), Mønsted et al. (Eq. 3) and FAO/WHO (Box 1) do.
13. **Dodds & Watts 2004** have three classes (epidemic threshold, vanishing critical mass, pure critical mass), not two.
14. **Lloyd-Smith et al. 2005** do not find a general 20/80 rule (SARS: top 20% cause 88%).
15. **Ma et al. 2014** use Poisson error only; **Viboud et al. 2016** credit the GGM equation to Tolle (2003); neither Chowell 2017 nor Viboud 2016 uses AICc.
16. **AICc** originates with Sugiura (1978); Hurvich & Tsai (1989) extended it.
17. **Gneiting & Raftery 2007** orient scores positively (Eqs. 20–21); the lower-is-better CRPS is their CRPS* (p. 367).
18. **Holm 1979** has no working DOI (10.2307/4615733 returns 404); cite the [JSTOR stable URL](https://www.jstor.org/stable/4615733).
19. **Cameron et al. 2008**: the pairs cluster bootstrap can fail with ≤ 10 clusters and a cluster-invariant binary regressor.
20. **Library defaults** that differ from the intended methods: `multipletests` defaults to Holm–Šidák (pass `method='holm'`), `proportion_confint` to Wald (pass `method='wilson'`), `ttest_ind` to equal variances (pass `equal_var=False`), `ttost_ind` to pooled variance (pass `usevar='unequal'`); statsmodels' lowercase `cloglog` link is deprecated in favour of `CLogLog`, whose docstring says it is untested ([statsmodels links](https://www.statsmodels.org/stable/generated/statsmodels.genmod.families.links.CLogLog.html)).

## 5. The gap this project fills

Among the sources reviewed:

- **Reward-hacking transmission has been shown, but not measured epidemiologically in a population.** Hu et al. estimate a one-step propagation factor along chains of agents that see passing submissions, under θ₀ = 0, with one reported 𝓡̂ (3.40, CI 1.44–6.34). Muralimohan et al. report a matched-pair adoption effect in 6-agent networks (abstract only). Paglieri et al. give a forensic case study. None estimates a per-exposure transmission hazard from randomized exposure in a population, separates seed from secondary transmission, or tests whether spread persists after the seeds stop.
- **Epidemic models of agent contagion exist for other payloads, without uncertainty or R estimates.** Agent Smith gives a closed-form SIS model for a jailbreak image but no CIs on fitted rates; Wu et al. define 𝓡₀ = ρ(K) without estimating it; Mind Viruses and Prompt Infection report transmission without epidemic parameters; Ashery et al. measure critical mass for conventions, not for reward hacking.
- **Simple vs complex contagion has not been tested with randomized doses in LLM agents.** Human-network evidence comes from designs where dose is not randomized (Mønsted et al.; Romero et al.) or where dose is confounded with diffusion timing (Centola 2010).
- **Predicting population curves from individual-level assays has not been tested** for agent contagion. Hu et al.'s map Φ(x) makes such a prediction possible, but it was not validated against population dynamics with θ₀ > 0.

What this project adds (preregistered in [`preregistration.md`](preregistration.md)): (1) a logged, randomized K-of-N exposure graph on a shared board, giving a causal per-post hazard for non-seed (secondary) pro-hack posts (H2); (2) a self-sustainability test with transient seeds plus R0 estimated with infectious period D (H3), following Wu et al.'s warning not to read R0 off one-step susceptibility; (3) a randomized dose-response assay with known k that distinguishes simple from complex contagion and separates sources from exposures (H4); (4) an out-of-sample test of whether the assay's transmission map predicts the swarm's prevalence curves (H5); (5) all of it with an open-weight 4B model run locally, placebo and content controls, cluster-bootstrap CIs and preregistered decision rules.

## 6. Items that could not be verified

- Muralimohan et al. 2026: everything beyond the NeurIPS workshop abstract (OpenReview blocks automated access).
- Hu et al. 2026: 𝓡̂ values other than 3.40 (figure-only); the OpenReview record.
- Centola 2010: exact hazard ratios and the supplementary material.
- Centola & Macy 2007: page numbers in the published AJS version (accepted manuscript read).
- Field & Welsh 2007, Welch 1947, Cohen 1960, Schuirmann 1987, Allison 1982, Prentice & Gloeckler 1978: full texts are paywalled; only abstracts or metadata were checked, and the formulas used in the preregistration were verified through secondary sources (Lakens 2017; Landis & Koch 1977; SAS documentation; statsmodels and SciPy documentation).
- Sugiura 1978: cited from Hurvich & Tsai and Crossref.
- Britton 2018: the published book chapter; *Stat. Neerl.* journal PDF.
- Bass 2004 reprint; Morris II CCS 2025 version; Flooding Spread journal version; NetSafe ACL camera-ready.
- MBPP impossible dataset: the build script (repository not public).
- Weibull dose-response: no peer-reviewed microbial-risk paper opened (EPA BMDS guides and the FAO/WHO guideline used).
- Values shown only in figures in any paper (not quoted here).
