"""swarm_epi: epidemiology of a reward-hacking belief in a swarm of local-LLM agents sharing a message board.

Package map (see README for the data flow): config -> tasks/prompts -> grader (sandbox) -> board -> llm -> agent ->
swarm (one run) -> conditions/pools/dose_response (experiments) -> epi/* (statistics) -> analysis/figures/site.
"""

import os  # environment configuration before numpy is imported

# Single-threaded BLAS: on this machine multithreaded OpenBLAS made a 607x607 solve ~130x slower (thread
# oversubscription next to vLLM / asyncio workers); the hazard-model IRLS is dominated by such solves.
for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

__version__ = "0.1.0"  # package version (kept in sync with pyproject.toml)
