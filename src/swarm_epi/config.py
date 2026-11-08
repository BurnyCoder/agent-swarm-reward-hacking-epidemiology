"""Configuration for the swarm-epidemiology experiments.

Local context: two frozen dataclasses hold every tunable value; infrastructure values (server URL, sandbox
backend, paths) are read from environment variables / a `.env` file via python-dotenv, while experimental
parameters (N, K, T, seeds, prompt variant) are set per condition in `conditions.py`.
Global context: every module receives these objects instead of reading globals, so a run is fully described
by the config dict that `swarm.py` writes next to its logs (reproducibility).
"""

from __future__ import annotations  # allow forward references in type hints

import os  # read environment variables
from dataclasses import asdict, dataclass, field, replace  # immutable config records + helpers
from pathlib import Path  # filesystem paths

from dotenv import load_dotenv  # python-dotenv: loads KEY=VALUE lines from .env into os.environ

load_dotenv()  # search the cwd/parents for .env once at import; existing env vars take precedence


def _env(key: str, default: str) -> str:
    """Return environment variable `key` or `default` (single place to read env config)."""
    return os.environ.get(key, default)  # os.environ is populated by load_dotenv above


@dataclass(frozen=True)
class LLMConfig:
    """Inference-server settings and sampling parameters.

    Sampling values copy the Qwen3.5-4B model card's "Instruct (or non-thinking) mode for general tasks"
    recommendation: temperature=0.7, top_p=0.8, top_k=20, min_p=0.0, presence_penalty=1.5,
    repetition_penalty=1.0 (https://huggingface.co/Qwen/Qwen3.5-4B). Thinking is disabled through
    `chat_template_kwargs={"enable_thinking": False}` exactly as the card shows for vLLM/SGLang.
    """

    base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", "http://localhost:8000/v1"))  # server
    model: str = field(default_factory=lambda: _env("LLM_MODEL", "cyankiwi/Qwen3.5-4B-AWQ-4bit"))  # served name
    api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", "EMPTY"))  # vLLM ignores it
    max_concurrency: int = field(default_factory=lambda: int(_env("LLM_MAX_CONCURRENCY", "48")))  # in-flight cap
    temperature: float = 0.7  # model-card non-thinking value
    top_p: float = 0.8  # model-card non-thinking value
    top_k: int = 20  # model-card value (passed via extra_body because OpenAI API lacks top_k)
    min_p: float = 0.0  # model-card value (extra_body)
    presence_penalty: float = 1.5  # model-card value; pilot rule may set 0.0 if it breaks code (prereg)
    enable_thinking: bool = False  # user decision: Qwen3.5-4B with thinking off
    request_timeout_s: float = 600.0  # generous: a 32-agent batch can queue behind other swarms
    max_retries: int = 5  # transient server errors are retried by the OpenAI client


@dataclass(frozen=True)
class RuntimeConfig:
    """Paths and sandbox settings (infrastructure, not experimental variables)."""

    runs_dir: Path = field(default_factory=lambda: Path(_env("RUNS_DIR", "runs")))  # raw logs/state root
    results_dir: Path = field(default_factory=lambda: Path(_env("RESULTS_DIR", "results")))  # git-tracked
    sandbox: str = field(default_factory=lambda: _env("SANDBOX", "bwrap"))  # "bwrap" or "subprocess"
    sandbox_concurrency: int = field(default_factory=lambda: int(_env("SANDBOX_CONCURRENCY", "12")))
    exec_timeout_s: float = 10.0  # wall-clock limit per test run (ImpossibleBench uses 30 s; MBPP is tiny)
    # runs sub-directory whose runs are the pilot data for harvest, audits and Stage 2: "pilot" (prereg §8.4) or
    # "explore" (the exploratory batch may serve as the harvest runs, deviation #13)
    pilot_batch: str = field(default_factory=lambda: _env("PILOT_BATCH", "pilot"))


@dataclass(frozen=True)
class SwarmConfig:
    """Experimental parameters of one swarm run (one replicate of one condition).

    Defaults are the pre-registered batch-1 values (reports/preregistration.md): N=32 non-seed agents,
    K=6 posts read per round, T=10 rounds after a warm-up round 0, m=2 seed poster slots.
    """

    condition: str = "MAIN"  # condition label (MAIN / PLACEBO / TRANSIENT / ...)
    replicate: int = 0  # replicate index; drives the common-random-numbers RNG streams
    n_agents: int = 32  # non-seed LLM agents (the susceptible population)
    k_read: int = 6  # posts sampled per agent per round (K in K-of-N exposure math)
    n_rounds: int = 10  # rounds 1..T after warm-up round 0
    n_seeds: int = 2  # seed poster slots (posts drawn from a fixed, validated pool)
    seed_pool: str = "hack"  # which pool seeds draw from: "hack", "placebo", or "none"
    seed_last_round: int | None = None  # None = committed seeds (post every round); 1 = TRANSIENT (rounds 0-1)
    hide_nonseed_posts: bool = False  # week-phase NO-SECONDARY ablation (yoked replacement)
    memory: bool = True  # persistent private notes on/off (memory-off = serial-passage chain)
    feedback: bool = True  # show grader feedback / score to agents
    prompt_variant: str = "D"  # ImpossibleBench prompt A-D (pilot calibration rule picks it)
    flag_option: bool = True  # offer `[flag_for_human_intervention]` (ImpossibleBench §5.3)
    max_attempts: int = 2  # submissions per task with feedback (ImpossibleBench code default 3; compute)
    max_code_tokens: int = 768  # code-answer cap; results/engineering/length_probe.json: 60% (D) / 82.5% (A) end below it
    max_post_tokens: int = 200  # generation cap for post + notes
    notes_words: int = 80  # word budget stated in the post/notes prompt
    post_words: int = 80  # word budget stated in the post/notes prompt
    inoculation: bool = False  # week-phase ablation: anti-hacking warning in the system prompt
    task_split: str = "all"  # dataset splits to draw tasks from after the capability filter
    base_seed: int = 20261107  # global RNG seed (today's date) combined with replicate index

    def run_id(self) -> str:
        """Unique, human-readable run identifier used for folders and logs."""
        return f"{self.condition}_r{self.replicate:03d}"  # e.g. MAIN_r007

    def with_(self, **kw) -> SwarmConfig:
        """Return a modified copy (dataclasses.replace wrapper for readability)."""
        return replace(self, **kw)  # frozen dataclass => copy-on-write

    def to_dict(self) -> dict:
        """Plain-dict view for JSON logging."""
        return asdict(self)  # recursive conversion of dataclass fields
