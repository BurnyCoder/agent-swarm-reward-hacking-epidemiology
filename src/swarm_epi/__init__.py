"""swarm_epi: epidemiology of a reward-hacking belief in a swarm of local-LLM agents sharing a message board.

Package map (see README for the data flow): config -> tasks/prompts -> grader (sandbox) -> board -> llm -> agent ->
swarm (one run) -> conditions/pools/dose_response (experiments) -> epi/* (statistics) -> analysis/site (outputs).
"""

__version__ = "0.1.0"  # package version (kept in sync with pyproject.toml)
