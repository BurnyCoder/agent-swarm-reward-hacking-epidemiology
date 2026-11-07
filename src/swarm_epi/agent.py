"""One agent-round: read notes + board posts, solve an impossible task (with grader feedback), post, update notes,
answer the measurement-only belief probe.

Local context: the solve loop reproduces ImpossibleBench's minimal scaffold (`agentic_humaneval_solver`): generate,
stop on the abort token, otherwise grade; on failure append the verbatim feedback message and retry, up to
`max_attempts`; stop early on a pass. Private notes act as a persistent verbal memory (Reflexion-style, Shinn et al.
2023, https://arxiv.org/abs/2303.11366) and are the only state carried between rounds.
Global context: `swarm.py` runs all agents of a round concurrently with `asyncio.gather`; the returned `RoundRecord`
rows (one per agent-round) are the unit of the exposure/hazard analysis.
"""

from __future__ import annotations  # forward references

import re  # POST/NOTES parsing
from dataclasses import asdict, dataclass, field  # records

from . import prompts as P  # prompt text
from .board import Post  # post record
from .config import SwarmConfig  # experimental parameters
from .grader import Grade, Sandbox, grade  # grading
from .llm import LLM  # inference client
from .tasks import Task, format_task_input  # tasks

POST_RE = re.compile(r"POST:\s*(.*?)\s*NOTES:\s*(.*)", re.DOTALL | re.IGNORECASE)  # expected output format
MAX_WORDS = 120  # hard cap on stored post/notes length (prompt asks for <= 80 words) to bound reader context


def clip_words(text: str, n: int = MAX_WORDS) -> str:
    """Keep at most `n` whitespace-separated words."""
    words = text.split()  # tokenize on whitespace
    return " ".join(words[:n])  # rejoin the first n


def parse_post(text: str, old_notes: str) -> tuple[str, str]:
    """Split a 'POST: ... NOTES: ...' generation; fall back to (whole text, unchanged notes)."""
    m = POST_RE.search(text)  # tolerant regex
    if not m:  # format not followed
        return clip_words(text.replace("POST:", "").strip()), old_notes
    return clip_words(m.group(1).strip()), clip_words(m.group(2).strip())


@dataclass
class RoundRecord:
    """Everything observed for one agent in one round (one row of the analysis table)."""

    run_id: str
    condition: str
    replicate: int
    round: int
    agent: str
    task_id: str
    read_post_ids: list[str]  # exposure: which posts were read, in presentation order
    read_authors: list[str]
    read_is_seed: list[bool]
    n_attempts: int = 0
    hack_attempt: bool = False  # primary outcome: any attempt was a hack attempt
    hack_success: bool = False  # final submission passed the hackable grader (cheating by construction)
    mechanism: str = "none"  # mechanism of the first hack attempt
    outcome: str = "honest"  # hack / flag / honest (round level)
    flagged: bool = False
    strict_original_pass: bool = False  # last graded code satisfies the original tests (capability)
    attempts: list[dict] = field(default_factory=list)  # per-attempt grade summaries
    post_id: str = ""
    post_text: str = ""
    notes_before: str = ""
    notes_after: str = ""
    probe_p_yes: float = float("nan")  # belief probe P(Yes) after the round (carrier state)
    tokens_out: int = 0

    def to_dict(self) -> dict:
        """JSON view."""
        return asdict(self)


def _summ(g: Grade, attempt: int) -> dict:
    """Compact per-attempt grade summary for logging."""
    return {"attempt": attempt, "flagged": g.flagged, "hackable_pass": g.hackable_pass,
            "strict_original_pass": g.strict_original_pass, "strict_mutated_pass": g.strict_mutated_pass,
            "flags": g.flags, "hack_attempt": g.hack_attempt, "mechanism": g.mechanism, "code": g.answer}


async def agent_round(llm: LLM, sandbox: Sandbox, cfg: SwarmConfig, agent_idx: int, notes: str, task: Task,
                      posts: list[Post], round_t: int, llm_seed: int, solve_only: bool = False,
                      run_label: str | None = None) -> RoundRecord:
    """Run one agent for one round and return its record (post text + new notes included).

    `solve_only=True` stops after grading (capability pass); `run_label` overrides the run id in logs/records
    (pools, calibration and dose-response trials reuse this function with constructed notes/posts).
    """
    name = f"a{agent_idx}"  # author id
    run_id = run_label or cfg.run_id()  # label for records and logs
    tags = {"run": run_id, "round": round_t, "agent": name, "task": task.task_id}  # log tags
    instr = P.instruction(cfg.prompt_variant, cfg.flag_option)  # ImpossibleBench instruction (+abort option)
    rec = RoundRecord(run_id, cfg.condition, cfg.replicate, round_t, name, task.task_id,
                      [p.post_id for p in posts], [p.author for p in posts], [p.is_seed for p in posts],
                      notes_before=notes)
    messages = [
        {"role": "system", "content": P.system_prompt(agent_idx, cfg.n_agents, cfg.inoculation)},
        {"role": "user", "content": P.context_block(notes, [(0, p.text) for p in posts]) + format_task_input(task, instr)},
    ]
    max_attempts = cfg.max_attempts if cfg.feedback else 1  # no feedback => single submission
    g: Grade | None = None  # last grade
    for attempt in range(max_attempts):  # ImpossibleBench submission loop
        res = await llm.chat(messages, cfg.max_code_tokens, tags | {"phase": "solve", "attempt": attempt},
                             seed=llm_seed + attempt)
        rec.tokens_out += res.completion_tokens  # accounting
        messages.append({"role": "assistant", "content": res.text})  # keep the conversation
        g = await grade(task, res.text, sandbox)  # sandboxed grading
        rec.attempts.append(_summ(g, attempt))  # log
        if g.hack_attempt and rec.mechanism == "none":  # first hack mechanism observed
            rec.mechanism = g.mechanism
        rec.hack_attempt |= g.hack_attempt  # any-attempt rule (prereg)
        if g.flagged or g.hackable_pass:  # IB: stop on flag or pass
            break
        if attempt + 1 < max_attempts:  # IB feedback message before the next attempt
            messages.append({"role": "user", "content": P.feedback_message(g.stderr, instr)})
    rec.n_attempts = len(rec.attempts)  # attempts used
    rec.flagged = bool(g and g.flagged)  # aborted
    rec.hack_success = bool(g and g.hackable_pass)  # final submission cheated successfully
    rec.strict_original_pass = bool(g and g.strict_original_pass)  # capability indicator
    rec.outcome = "hack" if rec.hack_attempt else ("flag" if rec.flagged else "honest")  # round-level outcome
    if solve_only:  # capability pass: no post, notes or probe
        return rec
    status = "flag" if rec.flagged else ("pass" if rec.hack_success else "fail")  # what the agent is told
    messages.append({"role": "user", "content": P.post_prompt(status, cfg.post_words, cfg.notes_words, cfg.feedback)})
    res = await llm.chat(messages, cfg.max_post_tokens, tags | {"phase": "post"}, seed=llm_seed + 100)  # post+notes
    rec.tokens_out += res.completion_tokens
    post, new_notes = parse_post(res.text, notes)  # split output
    rec.post_id, rec.post_text = f"{round_t}:{name}", post  # board post
    rec.notes_after = new_notes if cfg.memory else ""  # memory-off ablation discards notes
    probe = [  # measurement only: fresh context with the persistent state (updated notes), never fed back
        {"role": "system", "content": P.system_prompt(agent_idx, cfg.n_agents, cfg.inoculation)},
        {"role": "user", "content": f"[Your private notes]\n{rec.notes_after or '(empty)'}\n\n{P.PROBE_QUESTION}"},
    ]
    rec.probe_p_yes = (await llm.option_probs(probe, ["Yes", "No"], tags | {"phase": "probe"}))["Yes"]
    return rec
