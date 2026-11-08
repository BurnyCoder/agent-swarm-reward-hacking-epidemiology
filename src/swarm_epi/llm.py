"""Async client for the local OpenAI-compatible inference server, with complete prompt/output logging.

Local context: uses the official `openai` Python SDK (`AsyncOpenAI.chat.completions.create`) against vLLM's
OpenAI-compatible server (https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html). Non-standard sampling
parameters (top_k, min_p) and `chat_template_kwargs={"enable_thinking": False}` go in `extra_body`, exactly as the
Qwen3.5-4B model card shows. Log-probabilities use the standard `logprobs=True, top_logprobs=n` fields.
Every call is appended in full (all messages + output + usage + timing) to a timestamped JSONL file and echoed to the
terminal without truncation (user requirement).
Global context: `agent.py` and `pools.py` call `chat` / `option_probs`; the JSONL file is the raw data uploaded to the
private HF dataset.
"""

from __future__ import annotations  # forward references

import asyncio  # concurrency cap
import json  # JSONL logging
import logging  # terminal + file logging
import math  # exp of logprobs
import time  # latency measurement
from dataclasses import dataclass  # call result
from datetime import UTC, datetime  # timestamps
from pathlib import Path  # log file path

import httpx  # HTTP client (installed with openai) for the /tokenize endpoint
from openai import AsyncOpenAI  # official SDK (v3)

from .config import LLMConfig  # server + sampling settings

log = logging.getLogger("swarm_epi.llm")  # module logger (configured by setup_logging)


def setup_logging(log_dir: Path, name: str) -> Path:
    """Configure root logging to a timestamped file + terminal; return the JSONL path for LLM calls."""
    log_dir.mkdir(parents=True, exist_ok=True)  # ensure directory exists
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")  # UTC timestamp for filenames
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s")  # timestamped lines
    root = logging.getLogger()  # root logger
    root.setLevel(logging.INFO)  # INFO and above
    for h in list(root.handlers):  # avoid duplicate handlers on repeated setup
        root.removeHandler(h)
    fh = logging.FileHandler(log_dir / f"{name}_{stamp}.log", encoding="utf-8")  # human-readable log file
    sh = logging.StreamHandler()  # terminal
    for h in (fh, sh):
        h.setFormatter(fmt)
        root.addHandler(h)
    for noisy in ("httpx", "httpx2", "httpcore", "httpcore2", "openai"):  # silence per-request HTTP chatter (openai 3.x uses httpx2)
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return log_dir / f"{name}_{stamp}_llm_calls.jsonl"  # structured log of every LLM call


@dataclass
class ChatResult:
    """One completion."""

    text: str  # assistant message content
    top_logprobs: list[dict[str, float]] | None  # per generated token: {token: logprob} for the top-n alternatives
    prompt_tokens: int  # usage accounting
    completion_tokens: int
    finish_reason: str  # "stop" / "length"


class LLM:
    """Thin async wrapper with a global in-flight cap and full logging."""

    def __init__(self, cfg: LLMConfig, jsonl_path: Path | None = None, echo: bool = True):
        self.cfg = cfg  # settings
        self.client = AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key, timeout=cfg.request_timeout_s,
                                  max_retries=cfg.max_retries)  # SDK retries transient errors with backoff
        self.sem = asyncio.Semaphore(cfg.max_concurrency)  # cap concurrent HTTP requests
        self.http = httpx.AsyncClient(timeout=30.0)  # for vLLM's /tokenize (served at the root, not under /v1)
        self.tokenize_url = cfg.base_url.rstrip("/").removesuffix("/v1") + "/tokenize"  # e.g. http://localhost:8000/tokenize
        self.jsonl_path = jsonl_path  # where call records go
        self.echo = echo  # print every call in full to the terminal
        self.tokens_out = 0  # running total of generated tokens (throughput dashboard)

    def _record(self, rec: dict) -> None:
        """Append one call record to the JSONL file and echo it."""
        if self.jsonl_path:
            with open(self.jsonl_path, "a", encoding="utf-8") as fh:  # append-only, one JSON object per line
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if self.echo:  # untruncated terminal echo (user requirement)
            msgs = "\n".join(f"[{m['role']}] {m['content']}" for m in rec["messages"])
            log.info("LLM CALL %s\n%s\n[assistant] %s\n", json.dumps(rec["tags"]), msgs, rec["output"])

    async def _fit_budget(self, messages: list[dict], max_tokens: int, template_kwargs: dict) -> tuple[int, int]:
        """Clamp max_tokens so prompt + output fits the server's max_model_len; returns (prompt_count, max_tokens).

        vLLM rejects a request whose prompt + max_tokens exceeds --max-model-len with HTTP 400. Its /tokenize endpoint
        (https://docs.vllm.ai/en/latest/serving/openai_compatible_server/#tokenizer-api) applies the same chat
        template to `messages` and returns {"count", "max_model_len", ...}, so the clamp is exact.
        """
        body = {"model": self.cfg.model, "messages": messages, "add_generation_prompt": True,
                "chat_template_kwargs": template_kwargs}  # same template + kwargs as the completion request
        for attempt in range(self.cfg.max_retries + 1):  # retry transient transport errors, like the OpenAI SDK does
            try:
                r = await self.http.post(self.tokenize_url, json=body)
                break
            except httpx.TransportError as e:  # e.g. RemoteProtocolError when the server drops a kept-alive
                if attempt == self.cfg.max_retries:  # connection (https://www.python-httpx.org/exceptions/)
                    raise
                log.warning("tokenize retry %d after %r", attempt + 1, e)
                await asyncio.sleep(0.5 * 2**attempt)  # exponential backoff
        r.raise_for_status()  # surface server errors
        d = r.json()  # {"count": n_prompt_tokens, "max_model_len": L, "tokens": [...]}
        room = d["max_model_len"] - d["count"]  # tokens left for the output
        if room < max_tokens:  # rare: long feedback + two long attempts; logged so it can be counted
            log.warning("output budget clamped %d -> %d (prompt %d tokens)", max_tokens, max(room, 1), d["count"])
        return d["count"], max(1, min(max_tokens, room))  # at least 1 token so the request stays valid

    async def chat(self, messages: list[dict], max_tokens: int, tags: dict | None = None, seed: int | None = None,
                   top_logprobs: int = 0, temperature: float | None = None) -> ChatResult:
        """One chat completion with the model-card sampling parameters (thinking disabled)."""
        cfg = self.cfg  # shorthand
        extra = {"top_k": cfg.top_k, "min_p": cfg.min_p,
                 "chat_template_kwargs": {"enable_thinking": cfg.enable_thinking}}  # model-card extra_body
        async with self.sem:  # respect concurrency cap
            requested = max_tokens  # cap asked for by the caller (logged next to the effective one)
            if max_tokens > 1:  # 1-token probes cannot overflow; skip the extra request
                _, max_tokens = await self._fit_budget(messages, max_tokens, extra["chat_template_kwargs"])
            t0 = time.perf_counter()  # latency start
            resp = await self.client.chat.completions.create(
                model=cfg.model, messages=messages, max_tokens=max_tokens,
                temperature=cfg.temperature if temperature is None else temperature, top_p=cfg.top_p,
                presence_penalty=cfg.presence_penalty, seed=seed,
                logprobs=top_logprobs > 0, top_logprobs=top_logprobs or None, extra_body=extra,
            )
            dt = time.perf_counter() - t0  # latency
        choice = resp.choices[0]  # single sample
        text = (choice.message.content or "")  # assistant text
        if "</think>" in text:  # defensive: strip an empty think block if the template leaks one
            text = text.split("</think>", 1)[1]
        text = text.strip()
        tl = None  # top-logprobs per token
        if top_logprobs and choice.logprobs and choice.logprobs.content:
            tl = [{alt.token: alt.logprob for alt in tok.top_logprobs} for tok in choice.logprobs.content]
        usage = resp.usage  # token accounting
        self.tokens_out += usage.completion_tokens if usage else 0  # throughput counter
        self._record({
            "ts": datetime.now(UTC).isoformat(), "tags": tags or {}, "messages": messages, "output": text,
            "top_logprobs_first": tl[0] if tl else None, "seed": seed, "latency_s": round(dt, 3),
            "max_tokens_requested": requested, "max_tokens_effective": max_tokens,
            "prompt_tokens": usage.prompt_tokens if usage else None,
            "completion_tokens": usage.completion_tokens if usage else None, "finish_reason": choice.finish_reason,
        })
        return ChatResult(text, tl, usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0,
                          choice.finish_reason)

    async def option_probs(self, messages: list[dict], options: list[str], tags: dict | None = None) -> dict[str, float]:
        """Normalized probability of each single-token answer option from first-token top-20 logprobs.

        Tokens are matched case-insensitively after stripping whitespace (e.g. "Yes", " yes"); probability mass of
        all matching alternatives is summed, then renormalized over the options (NaN if none appear in the top-20).
        """
        res = await self.chat(messages, max_tokens=1, tags=tags, top_logprobs=20, temperature=0.0)  # greedy, 1 token
        mass = {o: 0.0 for o in options}  # accumulated probability per option
        for tok, lp in (res.top_logprobs[0] if res.top_logprobs else {}).items():  # first token alternatives
            key = tok.strip().lower()  # normalize token text
            for o in options:
                if key == o.lower():
                    mass[o] += math.exp(lp)  # logprob -> probability
        total = sum(mass.values())  # normalizer
        return {o: (m / total if total > 0 else float("nan")) for o, m in mass.items()}
